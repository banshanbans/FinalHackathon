import asyncio
import hashlib
import json
import re
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import TypeVar

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from policyscope_api.dependencies import build_adapter, get_adapter
from policyscope_api.idempotency import (
    IdempotencyConflictError,
    PersistentIdempotencyRepository,
)
from policyscope_api.schemas import (
    ApproveDirectiveRequest,
    ApproveEventScenarioRequest,
    ApproveInterventionRequest,
    ConfirmBaselineRequest,
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
from simulation.models.m34 import (
    ExperimentDesignV2,
    InteractionWave,
    MacroTick,
)
from simulation.models.v32 import PolicyInterpretation
from simulation.presentation_catalog import presentation_event_catalog
from simulation.services.m34_orchestrator import M34Orchestrator

ResponseT = TypeVar("ResponseT")


def _http_error(error: Exception) -> HTTPException:
    message = str(error)
    if isinstance(error, KeyError) and "presentation frame not found" in message:
        return HTTPException(
            status_code=404,
            detail={
                "error_code": "PRESENTATION_FRAME_NOT_FOUND",
                "message": message.strip("'\""),
            },
        )
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
        application.state.m34 = M34Orchestrator(
            application.state.adapter,
            runtime_dir=app_settings.runtime_dir / "m34",
            cache_dir=app_settings.runtime_dir / "cache" / "v3_2_m34_luna",
            cache_enabled=app_settings.run_mode.value == "cache",
        )
        application.state.idempotency = PersistentIdempotencyRepository(
            app_settings.runtime_dir / "idempotency"
        )
        yield
        await application.state.adapter.close()

    application = FastAPI(
        title="13110 API",
        version="0.9.0",
        description="PolicyScope V3.2 upfront A/B multi-agent simulation API",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.middleware("http")
    async def reject_legacy_m32_runtime(request: Request, call_next):
        if re.search(r"/api/experiments/exp_m32_[^/]+", request.url.path):
            return JSONResponse(
                status_code=410,
                content={
                    "detail": {
                        "error_code": "LEGACY_V32_RUNTIME_UNSUPPORTED",
                        "message": (
                            "该固定七轮历史实验已停止加载；磁盘文件仍保留。请创建 M34 季度实验。"
                        ),
                    }
                },
            )
        return await call_next(request)

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
        try:
            return await application.state.idempotency.execute(
                scope=scope,
                key=key,
                payload_hash=digest,
                operation=operation,
            )
        except IdempotencyConflictError as error:
            raise HTTPException(
                status_code=409,
                detail={
                    "error_code": "IDEMPOTENCY_CONFLICT",
                    "message": str(error),
                },
            ) from error

    @application.get("/api/health")
    async def health() -> dict[str, str]:
        return {
            "status": "ok",
            "runtime": "asyncio",
            "run_mode": app_settings.run_mode.value,
            "version": "0.6.0",
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

    @application.get("/api/meta/presentation-event-catalog")
    async def presentation_events() -> dict[str, object]:
        return presentation_event_catalog().model_dump(mode="json")

    @application.get("/api/meta/v32/baseline")
    async def v32_baseline_metadata() -> dict[str, object]:
        snapshot = application.state.m34.m29
        return {
            **snapshot.manifest.model_dump(mode="json"),
            "relation_network_version": snapshot.relation_network.schema_version,
            "profile_versions": {
                "province": "province-profile-v6",
                "automaker": "automaker-profile-v2",
            },
        }

    @application.get("/api/meta/v32/provinces")
    async def v32_provinces() -> list[dict[str, object]]:
        return [
            profile.model_dump(mode="json")
            for _, profile in sorted(application.state.m34.m29.province_profiles.items())
        ]

    @application.get("/api/meta/v32/automakers")
    async def v32_automakers() -> list[dict[str, object]]:
        return [
            profile.model_dump(mode="json")
            for _, profile in sorted(application.state.m34.m29.automaker_profiles.items())
        ]

    @application.post("/api/experiments", status_code=status.HTTP_201_CREATED)
    async def create_experiment(
        body: CreateExperimentRequest,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
        simulation: AsyncioSimulationAdapter = Depends(get_adapter),
    ) -> dict[str, object]:
        async def operation() -> dict[str, object]:
            stable_experiment_id = (
                f"exp_m34_{hashlib.sha256(f'm34-create:{idempotency_key}'.encode()).hexdigest()[:12]}"
                if idempotency_key
                else None
            )
            state = await application.state.m34.create_experiment(
                body.policy_text or "西部 95%，中部 90%，东部 85%，促进新能源汽车消费与产业布局。",
                seed=body.seed,
                experiment_id=stable_experiment_id,
            )
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
            if application.state.m34.has_experiment(experiment_id):
                return (await application.state.m34.get_state(experiment_id)).model_dump(
                    mode="json"
                )
            return (await simulation.get_record(experiment_id)).model_dump(mode="json")
        except Exception as error:
            raise _http_error(error) from error

    @application.put("/api/experiments/{experiment_id}/interpretation")
    async def confirm_interpretation(
        experiment_id: str,
        body: PolicyInterpretation,
    ) -> dict[str, object]:
        try:
            result = await application.state.m34.confirm_interpretation(experiment_id, body)
            return result.model_dump(mode="json")
        except Exception as error:
            raise _http_error(error) from error

    @application.put("/api/experiments/{experiment_id}/design")
    async def confirm_design(
        experiment_id: str,
        body: ExperimentDesignV2,
    ) -> dict[str, object]:
        try:
            result = await application.state.m34.confirm_design(experiment_id, body)
            return result.model_dump(mode="json")
        except Exception as error:
            raise _http_error(error) from error

    @application.post("/api/experiments/{experiment_id}/baseline/confirm")
    async def confirm_baseline(
        experiment_id: str,
        body: ConfirmBaselineRequest,
    ) -> dict[str, object]:
        try:
            confirmed = body.confirm_data_snapshot or body.confirm_proxy_data is True
            if not confirmed:
                raise ValueError("必须确认当前 M29 事实与派生快照后才能冻结。")
            result = await application.state.m34.confirm_baseline(
                experiment_id, expected_data_version=body.expected_data_version
            )
            return result.model_dump(mode="json")
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
            if application.state.m34.has_experiment(experiment_id):
                state = await application.state.m34.run(experiment_id, until_tick=body.until_tick)
                return state.model_dump(mode="json")
            raise KeyError(f"experiment not found: {experiment_id}")

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
            if application.state.m34.has_experiment(experiment_id):
                return (await application.state.m34.get_state(experiment_id)).model_dump(
                    mode="json"
                )
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
            if application.state.m34.has_experiment(experiment_id):
                return await application.state.m34.get_province_detail(experiment_id, province_code)
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
            if application.state.m34.has_experiment(experiment_id):
                return await application.state.m34.get_automaker_detail(experiment_id, automaker_id)
            return (await simulation.get_automaker_detail(experiment_id, automaker_id)).model_dump(
                mode="json"
            )
        except Exception as error:
            raise _http_error(error) from error

    @application.get("/api/experiments/{experiment_id}/decision-traces")
    async def decision_traces(
        experiment_id: str,
        branch_id: str | None = Query(default=None),
        agent_id: str | None = Query(default=None),
        tick: MacroTick | None = Query(default=None),
        wave: InteractionWave | None = Query(default=None),
    ) -> list[dict[str, object]]:
        try:
            if not application.state.m34.has_experiment(experiment_id):
                raise ValueError("decisions are only available for M34 experiments")
            traces = await application.state.m34.get_decisions(
                experiment_id,
                branch_id=branch_id,
                tick=tick,
                wave=wave,
                agent_id=agent_id,
            )
            return [item.model_dump(mode="json") for item in traces]
        except Exception as error:
            raise _http_error(error) from error

    @application.get("/api/experiments/{experiment_id}/interactions")
    async def interactions(
        experiment_id: str,
        branch_id: str | None = Query(default=None),
        tick: MacroTick | None = Query(default=None),
    ) -> dict[str, object]:
        try:
            if not application.state.m34.has_experiment(experiment_id):
                raise ValueError("interactions are only available for M34 experiments")
            return (
                await application.state.m34.get_interactions(
                    experiment_id, branch_id=branch_id, tick=tick
                )
            ).model_dump(mode="json")
        except Exception as error:
            raise _http_error(error) from error

    @application.get("/api/experiments/{experiment_id}/strategy-market")
    async def strategy_market(experiment_id: str) -> dict[str, object]:
        try:
            if not application.state.m34.has_experiment(experiment_id):
                raise ValueError("strategy market is only available for M34 experiments")
            return (await application.state.m34.get_interactions(experiment_id)).model_dump(
                mode="json"
            )
        except Exception as error:
            raise _http_error(error) from error

    @application.get("/api/experiments/{experiment_id}/presentation-summary")
    async def presentation_summary(experiment_id: str) -> dict[str, object]:
        try:
            if not application.state.m34.has_experiment(experiment_id):
                raise ValueError("presentation summary is only available for M34 experiments")
            timeline = await application.state.m34.get_presentation_timeline(experiment_id)
            return {
                "schema_version": "presentation-summary-v2",
                "experiment_id": experiment_id,
                "scenes": [
                    {
                        "scene": item.kind,
                        "title": item.title,
                        "summary": "季度聚合节点",
                        "evidence_refs": item.source_event_ids,
                    }
                    for item in timeline.nodes
                ],
            }
        except Exception as error:
            raise _http_error(error) from error

    @application.get("/api/experiments/{experiment_id}/presentation/timeline")
    async def presentation_timeline(experiment_id: str) -> dict[str, object]:
        try:
            if not application.state.m34.has_experiment(experiment_id):
                raise ValueError("presentation timeline is only available for M34 experiments")
            return (
                await application.state.m34.get_presentation_timeline(experiment_id)
            ).model_dump(mode="json")
        except Exception as error:
            raise _http_error(error) from error

    @application.get("/api/experiments/{experiment_id}/presentation/frames/{frame_id}")
    async def presentation_frame(experiment_id: str, frame_id: str) -> dict[str, object]:
        try:
            if not application.state.m34.has_experiment(experiment_id):
                raise ValueError("presentation frames are only available for M34 experiments")
            return (
                await application.state.m34.get_presentation_frame(experiment_id, frame_id)
            ).model_dump(mode="json")
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
                    if application.state.m34.has_experiment(experiment_id):
                        events = await application.state.m34.wait_for_events(
                            experiment_id, cursor, timeout_seconds=10
                        )
                    else:
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
        if application.state.m34.has_experiment(experiment_id):
            raise HTTPException(
                status_code=409,
                detail={
                    "error_code": "V32_INCOMPATIBLE_OPERATION",
                    "message": "V3.2 已在实验设计阶段冻结双分支，不支持年末干预审批。",
                },
            )

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
        if application.state.m34.has_experiment(experiment_id):
            raise HTTPException(
                status_code=409,
                detail={
                    "error_code": "V32_INCOMPATIBLE_OPERATION",
                    "message": "V3.2 不支持运行期年末干预审批。",
                },
            )

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
            if application.state.m34.has_experiment(experiment_id):
                world = await application.state.m34.get_state(experiment_id)
                return [branch.model_dump(mode="json") for branch in world.branches.values()]
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
        if application.state.m34.has_experiment(experiment_id):
            raise HTTPException(
                status_code=409,
                detail={
                    "error_code": "V32_INCOMPATIBLE_OPERATION",
                    "message": "V3.2 在基线确认时已同源创建双分支。",
                },
            )

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
            if application.state.m34.has_experiment(experiment_id):
                world = await application.state.m34.get_state(experiment_id)
                events = world.design.event_plans if world.design else []
                return {"event_plans": [item.model_dump(mode="json") for item in events]}
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
        if application.state.m34.has_experiment(experiment_id):
            raise HTTPException(
                status_code=409,
                detail={
                    "error_code": "V32_INCOMPATIBLE_OPERATION",
                    "message": "V3.2 事件在实验设计阶段冻结，运行期不再审批。",
                },
            )

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
            if application.state.m34.has_experiment(experiment_id):
                return (await application.state.m34.get_comparison(experiment_id)).model_dump(
                    mode="json"
                )
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
            if application.state.m34.has_experiment(experiment_id):
                return await application.state.m34.get_evidence(experiment_id, evidence_id)
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
            if application.state.m34.has_experiment(experiment_id):
                return await application.state.m34.get_audit(experiment_id, limit=limit)
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
            if application.state.m34.has_experiment(experiment_id):
                audit = await application.state.m34.get_audit(experiment_id, limit=500)
                record = next(
                    (item for item in audit["records"] if item["record_id"] == record_id),
                    None,
                )
                if record is None:
                    raise KeyError(f"audit record not found: {record_id}")
                return record
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
            if application.state.m34.has_experiment(experiment_id):
                return await application.state.m34.get_replay(experiment_id)
            return await simulation.get_replay(experiment_id)
        except Exception as error:
            raise _http_error(error) from error

    return application


app = create_app()
