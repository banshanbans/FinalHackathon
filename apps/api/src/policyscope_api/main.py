import asyncio
import hashlib
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import TypeVar

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from policyscope_api.dependencies import build_adapter, get_adapter
from policyscope_api.schemas import (
    ApproveDirectiveRequest,
    ApproveEventScenarioRequest,
    ApproveInterventionRequest,
    CreateBranchRequest,
    CreateExperimentRequest,
    RejectInterventionRequest,
    RunBranchRequest,
    RunExperimentRequest,
)
from policyscope_api.settings import Settings, get_settings
from simulation.adapters.asyncio_adapter import AsyncioSimulationAdapter
from simulation.catalog import automaker_catalog, event_scenario_catalog, policy_region_catalog
from simulation.models.audit import AuditRecordType
from simulation.models.common import Phase, PolicyRegion, ProvincePersonaType
from simulation.models.experiment import ExperimentConfig

ResponseT = TypeVar("ResponseT")


def _http_error(error: Exception) -> HTTPException:
    message = str(error)
    if isinstance(error, KeyError) and "province not found" in message:
        return HTTPException(
            status_code=404,
            detail={"error_code": "PROVINCE_NOT_FOUND", "message": message.strip("'\"")},
        )
    if message == "directive is not awaiting approval":
        return HTTPException(
            status_code=409,
            detail={
                "error_code": "DIRECTIVE_NOT_AWAITING_APPROVAL",
                "message": "该中央政策已完成审批，不能重复提交。请直接进入实时推演。",
            },
        )
    if message == "EVENT_APPROVAL_REQUIRED":
        return HTTPException(
            status_code=403,
            detail={
                "error_code": "EVENT_APPROVAL_REQUIRED",
                "message": "两个分支完成 Y2_Q2 后必须先由用户批准一次事件情景。",
            },
        )
    if message == "event scenario already approved":
        return HTTPException(
            status_code=409,
            detail={
                "error_code": "EVENT_ALREADY_APPROVED",
                "message": "本实验的事件情景已批准，不能重复审批或修改。",
            },
        )
    if "COMPARISON_NOT_AVAILABLE" in message:
        return HTTPException(
            status_code=409,
            detail={
                "error_code": "COMPARISON_NOT_AVAILABLE",
                "message": "用户未创建干预分支，当前实验只有原始方案单线复盘。",
            },
        )
    if isinstance(error, KeyError):
        return HTTPException(
            status_code=404,
            detail={"error_code": "NOT_FOUND", "message": message},
        )
    if isinstance(error, PermissionError):
        return HTTPException(
            status_code=403,
            detail={"error_code": "APPROVAL_REQUIRED", "message": message},
        )
    if isinstance(error, ValueError):
        return HTTPException(
            status_code=409,
            detail={"error_code": "INVALID_STATE", "message": message},
        )
    return HTTPException(
        status_code=500,
        detail={"error_code": "INTERNAL_ERROR", "message": "Internal simulation error"},
    )


def _request_hash(payload: object) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def create_app(
    adapter: AsyncioSimulationAdapter | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    app_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        application.state.adapter = adapter or build_adapter(app_settings)
        application.state.idempotency = {}
        yield
        await application.state.adapter.close()

    application = FastAPI(
        title="PolicyScope API",
        version="0.5.0",
        description="PolicyScope V3.1 event-driven interprovincial simulation API",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    async def idempotent(
        *,
        scope: str,
        key: str | None,
        payload: object,
        operation: Callable[[], Awaitable[ResponseT]],
    ) -> ResponseT:
        if not key:
            return await operation()
        digest = _request_hash(payload)
        cache_key = (scope, key)
        existing = application.state.idempotency.get(cache_key)
        if existing:
            old_digest, response = existing
            if old_digest != digest:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error_code": "IDEMPOTENCY_CONFLICT",
                        "message": "同一 Idempotency-Key 不能用于不同请求。",
                    },
                )
            return response
        response = await operation()
        application.state.idempotency[cache_key] = (digest, response)
        return response

    @application.get("/api/health")
    async def health() -> dict[str, str]:
        return {
            "status": "ok",
            "runtime": "asyncio",
            "run_mode": app_settings.run_mode.value,
            "version": "0.5.0",
        }

    @application.get("/api/meta/provinces")
    async def provinces(
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> list[dict[str, object]]:
        return [
            profile.model_dump(mode="json") for _, profile in sorted(simulation.profiles.items())
        ]

    @application.get("/api/meta/automakers")
    async def automakers(
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> list[dict[str, object]]:
        catalog = automaker_catalog()
        return [
            {
                "automaker_id": automaker_id,
                "display_name": catalog[automaker_id].display_name,
                "schema_version": profile.schema_version,
                "baseline_year": profile.baseline_year,
                "data_quality": profile.data_quality.value,
                "representative_set_disclaimer": catalog[
                    automaker_id
                ].representative_set_disclaimer,
            }
            for automaker_id, profile in simulation.automaker_profiles.items()
        ]

    @application.get("/api/meta/policy-regions")
    async def policy_regions(
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> list[dict[str, object]]:
        catalog = policy_region_catalog()
        return [
            {
                "policy_region": region.value,
                "central_share": simulation.default_policy.central_share_for_region(region),
                "province_codes": [
                    code for code, item in catalog.items() if item.policy_region is region
                ],
                "province_names": [
                    item.name for item in catalog.values() if item.policy_region is region
                ],
            }
            for region in (PolicyRegion.WEST, PolicyRegion.CENTRAL, PolicyRegion.EAST)
        ]

    @application.get("/api/meta/province-persona-types")
    async def province_persona_types() -> list[dict[str, object]]:
        return [
            {
                "type": persona_type.value,
                "display_name": persona_type.value,
                "visible_label": "本次实验决策画像",
            }
            for persona_type in ProvincePersonaType
        ]

    @application.get("/api/meta/default-policy")
    async def default_policy(
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> dict[str, object]:
        return simulation.default_policy.model_dump(mode="json")

    @application.get("/api/meta/event-scenarios")
    async def event_scenarios() -> list[dict[str, object]]:
        return [
            template.model_dump(mode="json")
            for _, template in sorted(
                event_scenario_catalog().items(), key=lambda item: item[0].value
            )
        ]

    @application.post("/api/experiments", status_code=status.HTTP_201_CREATED)
    async def create_experiment(
        body: CreateExperimentRequest,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> dict[str, object]:
        async def operation() -> dict[str, object]:
            selected_mode = body.run_mode or app_settings.run_mode
            if selected_mode != app_settings.run_mode:
                raise ValueError("experiment run_mode must match the configured server run mode")
            config = ExperimentConfig(
                objective=body.objective,
                scenario_id=body.scenario_id,
                seed=body.seed,
                run_mode=selected_mode,
                comparison_mode=body.comparison_mode,
                model_version=(
                    app_settings.central_model
                    if selected_mode.value == "live"
                    else f"{selected_mode.value}-v3"
                ),
            )
            state = await simulation.initialize(config)
            return state.model_dump(mode="json")

        try:
            return await idempotent(
                scope="create-experiment",
                key=idempotency_key,
                payload=body.model_dump(mode="json"),
                operation=operation,
            )
        except HTTPException:
            raise
        except Exception as error:
            raise _http_error(error) from error

    @application.get("/api/experiments/{experiment_id}")
    async def get_experiment(
        experiment_id: str,
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> dict[str, object]:
        try:
            return (await simulation.get_record(experiment_id)).model_dump(mode="json")
        except Exception as error:
            raise _http_error(error) from error

    @application.post("/api/experiments/{experiment_id}/directive/approve")
    async def approve_directive(
        experiment_id: str,
        body: ApproveDirectiveRequest,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> dict[str, object]:
        async def operation() -> dict[str, object]:
            state = await simulation.approve_directive(experiment_id, body.policy)
            return state.model_dump(mode="json")

        try:
            return await idempotent(
                scope=f"approve-directive:{experiment_id}",
                key=idempotency_key,
                payload=body.model_dump(mode="json"),
                operation=operation,
            )
        except HTTPException:
            raise
        except Exception as error:
            raise _http_error(error) from error

    @application.post("/api/experiments/{experiment_id}/run")
    async def run_experiment(
        experiment_id: str,
        body: RunExperimentRequest,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> dict[str, object]:
        async def operation() -> dict[str, object]:
            state = await simulation.run_to_phase(experiment_id, body.until_phase, body.branch_id)
            return state.model_dump(mode="json")

        try:
            return await idempotent(
                scope=f"run:{experiment_id}",
                key=idempotency_key,
                payload=body.model_dump(mode="json"),
                operation=operation,
            )
        except HTTPException:
            raise
        except Exception as error:
            raise _http_error(error) from error

    @application.get("/api/experiments/{experiment_id}/state")
    async def get_state(
        experiment_id: str,
        branch_id: str = Query(default="control"),
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> dict[str, object]:
        try:
            return (await simulation.get_state(experiment_id, branch_id)).model_dump(mode="json")
        except Exception as error:
            raise _http_error(error) from error

    @application.get("/api/experiments/{experiment_id}/provinces/{province_code}")
    async def province_detail(
        experiment_id: str,
        province_code: str,
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> dict[str, object]:
        try:
            return (await simulation.get_province_detail(experiment_id, province_code)).model_dump(
                mode="json"
            )
        except Exception as error:
            raise _http_error(error) from error

    @application.get("/api/experiments/{experiment_id}/automakers/{automaker_id}")
    async def automaker_detail(
        experiment_id: str,
        automaker_id: str,
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> dict[str, object]:
        try:
            return (await simulation.get_automaker_detail(experiment_id, automaker_id)).model_dump(
                mode="json"
            )
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
                        experiment_id, cursor, timeout_seconds=10
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
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> dict[str, object]:
        async def operation() -> dict[str, object]:
            result = await simulation.approve_intervention(experiment_id, proposal_id, body.policy)
            return result.model_dump(mode="json")

        try:
            return await idempotent(
                scope=f"approve-intervention:{experiment_id}:{proposal_id}",
                key=idempotency_key,
                payload=body.model_dump(mode="json"),
                operation=operation,
            )
        except HTTPException:
            raise
        except Exception as error:
            raise _http_error(error) from error

    @application.post("/api/experiments/{experiment_id}/interventions/{proposal_id}/reject")
    async def reject_intervention(
        experiment_id: str,
        proposal_id: str,
        body: RejectInterventionRequest,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> dict[str, object]:
        async def operation() -> dict[str, object]:
            state = await simulation.reject_intervention(experiment_id, proposal_id)
            result = state.model_dump(mode="json")
            result["user_reason"] = body.reason
            return result

        try:
            return await idempotent(
                scope=f"reject-intervention:{experiment_id}:{proposal_id}",
                key=idempotency_key,
                payload=body.model_dump(mode="json"),
                operation=operation,
            )
        except HTTPException:
            raise
        except Exception as error:
            raise _http_error(error) from error

    @application.get("/api/experiments/{experiment_id}/branches")
    async def list_branches(
        experiment_id: str,
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> list[dict[str, object]]:
        try:
            return [
                branch.model_dump(mode="json")
                for branch in await simulation.list_branches(experiment_id)
            ]
        except Exception as error:
            raise _http_error(error) from error

    @application.post("/api/experiments/{experiment_id}/branches", status_code=201)
    async def create_branch(
        experiment_id: str,
        body: CreateBranchRequest,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> dict[str, object]:
        async def operation() -> dict[str, object]:
            if body.kind == "policy_intervention":
                branch = await simulation.create_approved_branch(
                    experiment_id, body.intervention_id
                )
            else:
                branch = await simulation.create_event_counterfactual_branches(experiment_id)
            return branch.model_dump(mode="json")

        try:
            return await idempotent(
                scope=f"create-branch:{experiment_id}",
                key=idempotency_key,
                payload=body.model_dump(mode="json"),
                operation=operation,
            )
        except HTTPException:
            raise
        except Exception as error:
            raise _http_error(error) from error

    @application.get("/api/experiments/{experiment_id}/event-scenario")
    async def get_event_scenario(
        experiment_id: str,
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> dict[str, object] | None:
        try:
            scenario = await simulation.get_event_scenario(experiment_id)
            return scenario.model_dump(mode="json") if scenario else None
        except Exception as error:
            raise _http_error(error) from error

    @application.post("/api/experiments/{experiment_id}/event-scenario/approve")
    async def approve_event_scenario(
        experiment_id: str,
        body: ApproveEventScenarioRequest,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> dict[str, object]:
        async def operation() -> dict[str, object]:
            scenario = await simulation.approve_event_scenario(experiment_id, body)
            return scenario.model_dump(mode="json")

        try:
            return await idempotent(
                scope=f"approve-event-scenario:{experiment_id}",
                key=idempotency_key,
                payload=body.model_dump(mode="json"),
                operation=operation,
            )
        except HTTPException:
            raise
        except Exception as error:
            raise _http_error(error) from error

    @application.post("/api/branches/{branch_id}/run")
    async def run_branch(
        branch_id: str,
        body: RunBranchRequest,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> dict[str, object]:
        async def operation() -> dict[str, object]:
            experiment_id, _ = await simulation.find_branch(branch_id)
            state = await simulation.run_to_phase(experiment_id, body.until_phase, branch_id)
            return state.model_dump(mode="json")

        try:
            return await idempotent(
                scope=f"run-branch:{branch_id}",
                key=idempotency_key,
                payload=body.model_dump(mode="json"),
                operation=operation,
            )
        except HTTPException:
            raise
        except Exception as error:
            raise _http_error(error) from error

    @application.get("/api/experiments/{experiment_id}/compare")
    async def compare(
        experiment_id: str,
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> dict[str, object]:
        try:
            return (await simulation.get_comparison(experiment_id)).model_dump(mode="json")
        except Exception as error:
            raise _http_error(error) from error

    @application.get("/api/experiments/{experiment_id}/evidence/{evidence_id}")
    async def evidence(
        experiment_id: str,
        evidence_id: str,
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> dict[str, object]:
        try:
            return await simulation.get_evidence(experiment_id, evidence_id)
        except Exception as error:
            raise _http_error(error) from error

    @application.get("/api/experiments/{experiment_id}/audit")
    async def audit_records(
        experiment_id: str,
        branch_id: str | None = Query(default=None),
        phase: Phase | None = Query(default=None),
        actor_kind: str | None = Query(default=None),
        actor_id: str | None = Query(default=None),
        record_type: AuditRecordType | None = Query(default=None),
        status: str | None = Query(default=None),
        outcome: str | None = Query(default=None),
        after_sequence: int = Query(default=0, ge=0),
        limit: int = Query(default=100, ge=1, le=500),
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> dict[str, object]:
        try:
            result = await simulation.get_audit(
                experiment_id,
                branch_id=branch_id,
                phase=phase,
                actor_kind=actor_kind,
                actor_id=actor_id,
                record_type=record_type,
                outcome=status or outcome,
                after_sequence=after_sequence,
                limit=limit,
            )
            return result.model_dump(mode="json")
        except Exception as error:
            raise _http_error(error) from error

    @application.get("/api/experiments/{experiment_id}/audit/{record_id}")
    async def audit_record(
        experiment_id: str,
        record_id: str,
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> dict[str, object]:
        try:
            result = await simulation.get_audit_record(experiment_id, record_id)
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
