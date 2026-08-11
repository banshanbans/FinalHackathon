import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from policyscope_api.dependencies import build_adapter, get_adapter
from policyscope_api.schemas import (
    ApproveDirectiveRequest,
    ApproveInterventionRequest,
    CreateBranchRequest,
    CreateExperimentRequest,
    RunBranchRequest,
    RunExperimentRequest,
)
from policyscope_api.settings import Settings, get_settings
from simulation.adapters.asyncio_adapter import AsyncioSimulationAdapter
from simulation.models.experiment import ExperimentConfig


def _http_error(error: Exception) -> HTTPException:
    if isinstance(error, KeyError):
        return HTTPException(
            status_code=404,
            detail={"error_code": "NOT_FOUND", "message": str(error)},
        )
    if isinstance(error, PermissionError):
        return HTTPException(
            status_code=403,
            detail={"error_code": "APPROVAL_REQUIRED", "message": str(error)},
        )
    if isinstance(error, ValueError):
        return HTTPException(
            status_code=409,
            detail={"error_code": "INVALID_STATE", "message": str(error)},
        )
    return HTTPException(
        status_code=500,
        detail={"error_code": "INTERNAL_ERROR", "message": "Internal simulation error"},
    )


def create_app(
    adapter: AsyncioSimulationAdapter | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    app_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        application.state.adapter = adapter or build_adapter(app_settings)
        yield
        await application.state.adapter.close()

    application = FastAPI(
        title="PolicyScope API",
        version="0.1.0",
        description="Auditable hybrid multi-agent policy simulation API",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/api/health")
    async def health() -> dict[str, str]:
        return {
            "status": "ok",
            "runtime": "asyncio",
            "run_mode": app_settings.run_mode.value,
            "version": "0.1.0",
        }

    @application.get("/api/meta/provinces")
    async def provinces(
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> list[dict[str, object]]:
        return [
            profile.model_dump(mode="json") for _, profile in sorted(simulation.profiles.items())
        ]

    @application.get("/api/meta/default-policy")
    async def default_policy(
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> dict[str, object]:
        return simulation.default_policy.model_dump(mode="json")

    @application.post("/api/experiments", status_code=status.HTTP_201_CREATED)
    async def create_experiment(
        body: CreateExperimentRequest,
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> dict[str, object]:
        try:
            selected_mode = body.run_mode or app_settings.run_mode
            if selected_mode != app_settings.run_mode:
                raise ValueError("experiment run_mode must match the configured server run mode")
            config = ExperimentConfig(
                objective=body.objective,
                scenario_id=body.scenario_id,
                seed=body.seed,
                run_mode=selected_mode,
                model_version=(
                    app_settings.central_model
                    if selected_mode.value == "live"
                    else f"{selected_mode.value}-v1"
                ),
            )
            state = await simulation.initialize(config)
            return state.model_dump(mode="json")
        except Exception as error:
            raise _http_error(error) from error

    @application.get("/api/experiments/{experiment_id}")
    async def get_experiment(
        experiment_id: str,
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> dict[str, object]:
        try:
            record = await simulation.get_record(experiment_id)
            return record.model_dump(mode="json")
        except Exception as error:
            raise _http_error(error) from error

    @application.post("/api/experiments/{experiment_id}/directive/approve")
    async def approve_directive(
        experiment_id: str,
        body: ApproveDirectiveRequest,
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> dict[str, object]:
        try:
            state = await simulation.approve_directive(experiment_id, body.policy)
            return state.model_dump(mode="json")
        except Exception as error:
            raise _http_error(error) from error

    @application.post("/api/experiments/{experiment_id}/run")
    async def run_experiment(
        experiment_id: str,
        body: RunExperimentRequest,
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> dict[str, object]:
        try:
            state = await simulation.run_to_phase(experiment_id, body.until_phase, body.branch_id)
            return state.model_dump(mode="json")
        except Exception as error:
            raise _http_error(error) from error

    @application.get("/api/experiments/{experiment_id}/state")
    async def get_state(
        experiment_id: str,
        branch_id: str = Query(default="control"),
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> dict[str, object]:
        try:
            state = await simulation.get_state(experiment_id, branch_id)
            return state.model_dump(mode="json")
        except Exception as error:
            raise _http_error(error) from error

    @application.get("/api/experiments/{experiment_id}/stream")
    async def stream_events(
        request: Request,
        experiment_id: str,
        last_event_id_header: str | None = Header(default=None, alias="Last-Event-ID"),
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> EventSourceResponse:
        async def generator() -> AsyncIterator[dict[str, str]]:
            cursor = last_event_id_header
            while not await request.is_disconnected():
                try:
                    events = await simulation.wait_for_events(
                        experiment_id,
                        cursor,
                        timeout_seconds=10,
                    )
                except Exception as error:
                    yield {"event": "error", "data": _http_error(error).detail["message"]}
                    return
                if not events:
                    yield {"event": "heartbeat", "data": "{}"}
                    continue
                for event in events:
                    cursor = event.event_id
                    yield {
                        "id": event.event_id,
                        "event": event.type,
                        "data": event.model_dump_json(),
                    }
                await asyncio.sleep(0)

        return EventSourceResponse(generator())

    @application.post("/api/experiments/{experiment_id}/interventions/{proposal_id}/approve")
    async def approve_intervention(
        experiment_id: str,
        proposal_id: str,
        body: ApproveInterventionRequest,
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> dict[str, object]:
        try:
            intervention = await simulation.approve_intervention(
                experiment_id, proposal_id, body.overrides
            )
            return intervention.model_dump(mode="json")
        except Exception as error:
            raise _http_error(error) from error

    @application.post("/api/experiments/{experiment_id}/branches", status_code=201)
    async def create_branch(
        experiment_id: str,
        body: CreateBranchRequest,
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> dict[str, object]:
        try:
            branch = await simulation.create_approved_branch(experiment_id, body.intervention_id)
            return branch.model_dump(mode="json")
        except Exception as error:
            raise _http_error(error) from error

    @application.post("/api/branches/{branch_id}/run")
    async def run_branch(
        branch_id: str,
        body: RunBranchRequest,
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> dict[str, object]:
        try:
            experiment_id, _ = await simulation.find_branch(branch_id)
            state = await simulation.run_to_phase(experiment_id, body.until_phase, branch_id)
            return state.model_dump(mode="json")
        except Exception as error:
            raise _http_error(error) from error

    @application.get("/api/experiments/{experiment_id}/compare")
    async def compare(
        experiment_id: str,
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> dict[str, object]:
        try:
            result = await simulation.get_comparison(experiment_id)
            return result.model_dump(mode="json")
        except Exception as error:
            raise _http_error(error) from error

    @application.get("/api/experiments/{experiment_id}/replay")
    async def replay(
        experiment_id: str,
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> list[dict[str, object]]:
        try:
            return await simulation.get_replay(experiment_id)
        except Exception as error:
            raise _http_error(error) from error

    return application


app = create_app()
