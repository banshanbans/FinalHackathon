from __future__ import annotations

import asyncio
import json
import os
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from statistics import fmean
from typing import TypeVar
from uuid import uuid4

from pydantic import BaseModel

from simulation.adapters.asyncio_adapter import AsyncioSimulationAdapter
from simulation.catalog import automaker_catalog, event_scenario_catalog, policy_region_catalog
from simulation.domain_constants import AUTOMAKER_IDS, MAINLAND_PROVINCE_CODES
from simulation.envs.china_policy_env import ChinaPolicyEnv
from simulation.llm.v32_provider import V32AgentProvider, build_v32_agent_provider
from simulation.m29_data import M29Snapshot, load_m29_personas, load_m29_snapshot
from simulation.models.automaker import AutomakerAction, FacilityAction, ProvinceMarketAction
from simulation.models.common import (
    AutomakerReasonCode,
    BranchKind,
    ChannelStrategy,
    CoordinationStatus,
    EventIntensity,
    EventPolicyFocus,
    EventTemplateId,
    FacilityActionKind,
    PeerResponseMode,
    Phase,
    PolicyStatus,
    ProvinceReasonCode,
    RunMode,
    SimulatedRoiBand,
)
from simulation.models.policy import PolicySchema
from simulation.models.presentation import PresentationFrame, PresentationTimeline
from simulation.models.province import ProvinceAction, SubsidyMix
from simulation.models.scenario import (
    CoordinationMatch,
    EventScenario,
    ProvinceEventResponse,
    SubsidyMixDelta,
)
from simulation.models.v32 import (
    ActionDelta,
    AgentInvocationRecord,
    AutomakerActionV2,
    AutomakerCounterOffer,
    AutomakerDecisionTrace,
    AutomakerOutcomeDelta,
    AutomakerProvinceSignal,
    AutomakerResourceEnvelope,
    AutomakerSimulationPersona,
    BaselineSnapshot,
    BranchRuntimeState,
    ChangeCondition,
    ComparisonResultV6,
    CompetitionOutcome,
    ConsumerResponseRecord,
    CoordinationRecord,
    DecisionObservation,
    DecisionReason,
    DecisionTrace,
    EventPlan,
    EventTriggerPoint,
    EventV6,
    ExperimentDesign,
    ExperimentType,
    JourneyStep,
    MechanismChain,
    MechanismNode,
    MetricComparison,
    OpportunityCost,
    PolicyInterpretation,
    PolicyV4,
    PresentationScene,
    PresentationSummary,
    ProvinceActionV5,
    ProvinceCoordinationProposal,
    ProvinceCoordinationResponse,
    ProvinceCounterOfferResponse,
    ProvinceCounterOfferResponseBatch,
    ProvinceDecisionTrace,
    ProvinceEnterpriseMatch,
    ProvinceEnterpriseOffer,
    ProvinceEnterpriseOfferResponse,
    ProvinceOutcomeDelta,
    ProvinceProposalBatch,
    ProvinceRelation,
    ProvinceRelationNetwork,
    ProvinceResourceEnvelope,
    ProvinceResponseBatch,
    ProvinceUtility,
    QualityCount,
    RejectedAlternative,
    SensitivityFinding,
    SimulationRound,
    StrategyMarketSnapshot,
    TopKReallocation,
    TraceConfidence,
    V32DataQuality,
    V32ExperimentStatus,
    WorldStateV6,
)
from simulation.services.presentation_projection import PresentationProjectionService
from simulation.services.replay import canonical_hash

ROUND_SEQUENCE = tuple(SimulationRound)
ModelT = TypeVar("ModelT", bound=BaseModel)
EXPERIMENT_ID_PATTERN = re.compile(r"exp_m32_[0-9a-f]{12}\Z")
RUNTIME_SNAPSHOT_SCHEMA = "v32-runtime-snapshot-v1"
EVENT_ID_PATTERN = re.compile(r"evt_v32_(\d{8})\Z")

MECHANISM_LABELS = {
    "consumer_wtp": "消费意愿代理",
    "consumer_subsidy": "消费端支持",
    "automaker_sales": "车企销售投入",
    "charging_access": "充电基础条件",
    "event_policy_response": "事件政策响应",
    "peer_event_diffusion": "Peer 事件扩散",
    "industry_base": "新能源汽车产业基础",
    "fixed_cost_support": "固定成本支持",
    "variable_cost_support": "可变成本支持",
    "battery_proximity": "电池供应可达性",
    "facility_activity": "模拟产能活动",
    "province_coordination_effect": "省际协作效应",
    "province_enterprise_channel_effect": "省企渠道协同",
    "province_enterprise_industry_effect": "省企产业协同",
    "competition_channel_displacement": "竞争渠道挤出",
    "competition_facility_displacement": "竞争产能挤出",
    "intelligent_driving_acceptance": "智驾消费接受",
    "technology_market_adaptation": "技术市场适配",
    "intelligent_driving_industry_activity": "智驾产业活动",
    "oil_relative_cost_advantage": "相对使用成本",
    "battery_distance_relief": "电池距离改善",
    "battery_logistics_relief": "电池物流改善",
    "l3_liability_clarity_acceptance": "L3 责任清晰效应",
    "l3_liability_acceptance_drag": "L3 责任接受阻力",
    "l3_enterprise_liability_cost": "L3 企业责任成本",
}

PERSONA_TYPE_LABELS = {
    "consumption_activator": "消费激活",
    "industry_attractor": "产业承接",
    "operating_cost_competitor": "运营成本竞争",
    "supply_chain_coordinator": "供应链协同",
    "fiscally_prudent": "财政审慎",
    "peer_responder": "同类省份响应",
}

CONSTRAINT_LABELS = {
    "fiscal_rigidity": "财政刚性",
    "weak_consumer_wtp": "消费意愿代理偏弱",
    "weak_industry_base": "产业基础代理偏弱",
    "battery_distance": "电池供应距离",
    "talent_cost": "人才成本",
    "energy_cost": "能源成本",
    "logistics_cost": "物流成本",
}


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return round(max(minimum, min(maximum, value)), 4)


def _conserve_market_budget(
    actions: list[ProvinceMarketAction], budget: float
) -> list[ProvinceMarketAction]:
    """Remove per-province quantization overflow without changing rank order.

    Each province intensity is frozen at four decimals. Rounding 31 scaled values can
    otherwise add several ten-thousandths above the national envelope even though the
    unrounded vector is exactly budget-conserving.
    """

    overflow = round(sum(item.sales_investment_intensity for item in actions) - budget, 4)
    if overflow <= 0:
        return actions
    values = [item.sales_investment_intensity for item in actions]
    for index in sorted(range(len(actions)), key=lambda item: (values[item], -item), reverse=True):
        reduction = min(values[index], overflow)
        values[index] = round(values[index] - reduction, 4)
        overflow = round(overflow - reduction, 4)
        if overflow <= 0:
            break
    return [
        item.model_copy(update={"sales_investment_intensity": values[index]})
        for index, item in enumerate(actions)
    ]


def _stable_id(prefix: str, *parts: object) -> str:
    return f"{prefix}_{canonical_hash(parts)[:16]}"


def _normalize_mix(consumer: float, fixed: float, variable: float) -> SubsidyMix:
    values = [max(0.001, consumer), max(0.001, fixed), max(0.001, variable)]
    total = sum(values)
    normalized = [round(value / total, 6) for value in values]
    normalized[-1] = round(1 - normalized[0] - normalized[1], 6)
    return SubsidyMix(consumer=normalized[0], fixed_cost=normalized[1], variable_cost=normalized[2])


def _primary_policy_focus(mix: SubsidyMix) -> str:
    values = {
        "consumer": mix.consumer,
        "fixed_cost": mix.fixed_cost,
        "variable_cost": mix.variable_cost,
    }
    focus, value = max(values.items(), key=lambda item: item[1])
    return focus if value - min(values.values()) >= 0.035 else "balanced"


def _policy_values(policy: PolicyV4) -> tuple[float, float, float]:
    return (
        policy.west_central_share,
        policy.central_central_share,
        policy.east_central_share,
    )


@dataclass
class V32Runtime:
    world: WorldStateV6
    events: list[EventV6] = field(default_factory=list)
    comparison: ComparisonResultV6 | None = None
    event_counter: int = 0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    condition: asyncio.Condition = field(default_factory=asyncio.Condition)


class V32Orchestrator:
    """M32/v9 upfront A/B runtime with deterministic, inspectable fake agents."""

    def __init__(
        self,
        legacy: AsyncioSimulationAdapter,
        *,
        runtime_dir: Path | str = Path("runtime/m32"),
        cache_dir: Path | str = Path("runtime/cache/v3_2_m32_luna"),
        cache_enabled: bool = False,
        agent_provider: V32AgentProvider | None = None,
    ) -> None:
        self.m29: M29Snapshot = load_m29_snapshot()
        self.profiles = self.m29.mechanism_province_profiles
        self.observation_network = self.m29.observation_network
        self.personas = load_m29_personas(self.m29)
        self.automaker_profiles = self.m29.mechanism_automaker_profiles
        self.default_policy = legacy.default_policy
        self.runtime_dir = Path(runtime_dir)
        self.cache_dir = Path(cache_dir)
        self.cache_enabled = cache_enabled
        self.agent_provider = agent_provider or build_v32_agent_provider(
            legacy.provider, self.cache_dir
        )
        self.runtimes: dict[str, V32Runtime] = {}
        self.relation_network = self._build_relation_network()
        self.automaker_personas = self._build_automaker_personas()

    async def _resolve_agent(
        self,
        branch: BranchRuntimeState,
        *,
        agent_id: str,
        kind: str,
        instruction: str,
        payload: object,
        response_type: type[ModelT],
        fallback: Callable[[], ModelT],
    ) -> ModelT:
        value = await self.agent_provider.resolve(
            kind=kind,
            instruction=instruction,
            payload=payload,
            response_type=response_type,
            fallback=fallback,
        )
        nested_action = getattr(value, "proposed_action", None) or getattr(
            value, "base_final_action", None
        )
        fallback_used = bool(
            getattr(value, "fallback_used", False)
            or (nested_action is not None and getattr(nested_action, "fallback_used", False))
        )
        provider_mode = self.agent_provider.run_mode
        branch.agent_invocations.append(
            AgentInvocationRecord(
                invocation_id=_stable_id(
                    "agent_invocation",
                    branch.branch_id,
                    kind,
                    agent_id,
                    len(branch.agent_invocations),
                ),
                branch_id=branch.branch_id,
                agent_id=agent_id,
                kind=kind,
                model=self.agent_provider.model_name_for(kind),
                run_mode="fallback" if fallback_used else provider_mode,
                input_hash=canonical_hash(payload),
                output_hash=canonical_hash(value),
                output_schema=str(value.schema_version),
                fallback_used=fallback_used,
            )
        )
        return value

    @staticmethod
    def _mark_orchestrator_fallback(
        branch: BranchRuntimeState,
        *,
        agent_id: str,
        kind: str,
        value: BaseModel,
    ) -> None:
        """Keep provider provenance honest when a system constraint rejects output."""
        invocation = next(
            (
                item
                for item in reversed(branch.agent_invocations)
                if item.agent_id == agent_id and item.kind == kind
            ),
            None,
        )
        if invocation is None:
            raise RuntimeError("agent invocation missing before fallback accounting")
        invocation.run_mode = "fallback"
        invocation.fallback_used = True
        invocation.output_hash = canonical_hash(value)
        invocation.output_schema = str(value.schema_version)

    def has_experiment(self, experiment_id: str) -> bool:
        if experiment_id in self.runtimes:
            return True
        if not EXPERIMENT_ID_PATTERN.fullmatch(experiment_id):
            return False
        experiment_dir = self.runtime_dir / experiment_id
        if (
            not (experiment_dir / "runtime-snapshot.json").is_file()
            and not (experiment_dir / "state.json").is_file()
        ):
            return False
        self.runtimes[experiment_id] = self._restore_runtime(experiment_id)
        return True

    def _runtime(self, experiment_id: str) -> V32Runtime:
        if self.has_experiment(experiment_id):
            return self.runtimes[experiment_id]
        raise KeyError(f"experiment not found: {experiment_id}")

    def _restore_runtime(self, experiment_id: str) -> V32Runtime:
        experiment_dir = self.runtime_dir / experiment_id
        snapshot_path = experiment_dir / "runtime-snapshot.json"
        if snapshot_path.is_file():
            try:
                payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise ValueError("RUNTIME_SNAPSHOT_JSON_INVALID") from exc
            if payload.get("schema_version") != RUNTIME_SNAPSHOT_SCHEMA:
                raise ValueError("RUNTIME_SNAPSHOT_SCHEMA_INVALID")
            world_payload = payload.get("world")
            event_payloads = payload.get("events")
            comparison_payload = payload.get("comparison")
            if not isinstance(world_payload, dict) or not isinstance(event_payloads, list):
                raise ValueError("RUNTIME_SNAPSHOT_PAYLOAD_INVALID")
            world = WorldStateV6.model_validate(world_payload)
            events = [EventV6.model_validate(item) for item in event_payloads]
            comparison = (
                ComparisonResultV6.model_validate(comparison_payload)
                if comparison_payload is not None
                else None
            )
            if payload.get("world_hash") != canonical_hash(world):
                raise ValueError("RUNTIME_SNAPSHOT_WORLD_HASH_INVALID")
            if payload.get("replay_hash") != canonical_hash(events):
                raise ValueError("RUNTIME_SNAPSHOT_REPLAY_HASH_INVALID")
            expected_comparison_hash = canonical_hash(comparison) if comparison else None
            if payload.get("comparison_hash") != expected_comparison_hash:
                raise ValueError("RUNTIME_SNAPSHOT_COMPARISON_HASH_INVALID")
            event_counter = payload.get("event_counter")
            if not isinstance(event_counter, int) or event_counter < 0:
                raise ValueError("RUNTIME_SNAPSHOT_EVENT_COUNTER_INVALID")
        else:
            state_path = experiment_dir / "state.json"
            if not state_path.is_file():
                raise KeyError(f"experiment not found: {experiment_id}")
            world = WorldStateV6.model_validate_json(state_path.read_text(encoding="utf-8"))
            replay_path = experiment_dir / "replay.jsonl"
            events = []
            if replay_path.is_file():
                events = [
                    EventV6.model_validate_json(line)
                    for line in replay_path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
            comparison_path = experiment_dir / "comparison.json"
            comparison = (
                ComparisonResultV6.model_validate_json(comparison_path.read_text(encoding="utf-8"))
                if comparison_path.is_file()
                else None
            )
            event_counter = len(events)

        if world.experiment_id != experiment_id:
            raise ValueError("RUNTIME_EXPERIMENT_ID_MISMATCH")
        previous_counter = 0
        for event in events:
            match = EVENT_ID_PATTERN.fullmatch(event.event_id)
            if event.experiment_id != experiment_id or match is None:
                raise ValueError("RUNTIME_REPLAY_EVENT_INVALID")
            current_counter = int(match.group(1))
            if current_counter != previous_counter + 1:
                raise ValueError("RUNTIME_REPLAY_SEQUENCE_INVALID")
            if event.branch_id is not None and event.branch_id not in world.branches:
                raise ValueError("RUNTIME_REPLAY_BRANCH_INVALID")
            previous_counter = current_counter
        if event_counter != previous_counter:
            raise ValueError("RUNTIME_EVENT_COUNTER_MISMATCH")
        if comparison is not None:
            if comparison.experiment_id != experiment_id:
                raise ValueError("RUNTIME_COMPARISON_EXPERIMENT_MISMATCH")
            if world.status is not V32ExperimentStatus.COMPLETED:
                raise ValueError("RUNTIME_COMPARISON_STATUS_MISMATCH")
        elif world.status is V32ExperimentStatus.COMPLETED:
            raise ValueError("RUNTIME_COMPLETED_COMPARISON_MISSING")
        for branch in world.branches.values():
            self._assert_round_prefix(branch)
        return V32Runtime(
            world=world,
            events=events,
            comparison=comparison,
            event_counter=event_counter,
        )

    def _build_relation_network(self) -> ProvinceRelationNetwork:
        return ProvinceRelationNetwork(
            relations=[
                ProvinceRelation(
                    source_code=edge.source_code,
                    target_code=edge.target_code,
                    relation_type=edge.relation_type,
                    weight=edge.weight,
                    data_quality=V32DataQuality(edge.data_quality),
                    evidence_refs=[
                        ref
                        if ref.startswith(("relation:", "feature:"))
                        else f"{('relation' if ref.startswith('relation_') else 'feature')}:{ref}"
                        for ref in edge.evidence_refs
                    ],
                )
                for edge in self.m29.relation_network.edges
            ]
        )

    @staticmethod
    def _persona_specs() -> dict[str, tuple[object, ...]]:
        return {
            "byd": (
                "mass_market",
                "全价格带与垂直整合",
                0.92,
                0.20,
                0.72,
                0.88,
                0.76,
                0.82,
                0.78,
                0.80,
                0.92,
                0.88,
                0.58,
            ),
            "geely": (
                "mainstream",
                "多品牌平台与混动",
                0.82,
                0.34,
                0.65,
                0.78,
                0.80,
                0.74,
                0.72,
                0.74,
                0.82,
                0.78,
                0.62,
            ),
            "changan": (
                "mainstream",
                "自主平台与智能化",
                0.76,
                0.38,
                0.74,
                0.70,
                0.74,
                0.72,
                0.62,
                0.72,
                0.76,
                0.72,
                0.68,
            ),
            "sgmw": (
                "mass_market",
                "小型车与下沉渠道",
                0.68,
                0.48,
                0.62,
                0.84,
                0.48,
                0.45,
                0.50,
                0.90,
                0.86,
                0.58,
                0.46,
            ),
            "nio": (
                "premium",
                "高端纯电与补能服务",
                0.60,
                0.76,
                0.52,
                0.58,
                0.90,
                0.88,
                0.30,
                0.62,
                0.72,
                0.64,
                0.78,
            ),
            "chery": (
                "mainstream",
                "多动力路线与外向扩张",
                0.84,
                0.42,
                0.70,
                0.72,
                0.70,
                0.62,
                0.74,
                0.70,
                0.80,
                0.82,
                0.54,
            ),
            "leapmotor": (
                "mainstream",
                "成本效率与自研平台",
                0.86,
                0.62,
                0.78,
                0.76,
                0.72,
                0.76,
                0.56,
                0.82,
                0.80,
                0.74,
                0.60,
            ),
            "seres": (
                "premium",
                "增程与智能座舱协同",
                0.78,
                0.64,
                0.82,
                0.68,
                0.84,
                0.86,
                0.42,
                0.70,
                0.76,
                0.64,
                0.82,
            ),
            "xiaomi_auto": (
                "premium",
                "智能生态与高研发投入",
                0.94,
                0.56,
                0.86,
                0.90,
                0.96,
                0.94,
                0.60,
                0.64,
                0.88,
                0.70,
                0.90,
            ),
            "li_auto": (
                "premium",
                "家庭用户与增程平台",
                0.70,
                0.36,
                0.80,
                0.66,
                0.82,
                0.84,
                0.34,
                0.66,
                0.86,
                0.60,
                0.72,
            ),
        }

    def _build_automaker_personas(self) -> dict[str, AutomakerSimulationPersona]:
        result: dict[str, AutomakerSimulationPersona] = {}
        for automaker_id, values in self._persona_specs().items():
            (
                price_band,
                technology,
                growth,
                cashflow,
                capacity,
                channel,
                rd,
                driving,
                new_capacity,
                subsidy,
                market,
                supply,
                regulation,
            ) = values
            display_name = automaker_catalog()[automaker_id].display_name
            result[automaker_id] = AutomakerSimulationPersona(
                automaker_id=automaker_id,
                primary_price_band=price_band,
                technology_focus=str(technology),
                growth_goal=float(growth),
                cashflow_constraint=float(cashflow),
                capacity_pressure=float(capacity),
                channel_expansion_tendency=float(channel),
                rd_investment_tendency=float(rd),
                intelligent_driving_stage=float(driving),
                new_capacity_willingness=float(new_capacity),
                subsidy_sensitivity=float(subsidy),
                market_sensitivity=float(market),
                supply_chain_sensitivity=float(supply),
                regulation_sensitivity=float(regulation),
                summary=f"{display_name}模拟主体侧重{technology}，扩张与约束指标均为冻结代理值。",
            )
        return result

    @staticmethod
    def _parse_share(text: str, region: str, default: float) -> float:
        names = {"west": "西部", "central": "中部", "east": "东部"}
        match = re.search(rf"{names[region]}[^0-9]{{0,12}}(100|\d{{1,2}}(?:\.\d+)?)\s*%", text)
        return _clamp(float(match.group(1)) / 100) if match else default

    def interpret_policy(self, source_text: str) -> PolicyInterpretation:
        normalized = source_text.strip()
        shares = {
            region: self._parse_share(normalized, region, default)
            for region, default in (("west", 0.95), ("central", 0.90), ("east", 0.85))
        }
        goals = ["缩小区域新能源汽车发展差距"]
        if any(term in normalized for term in ("需求", "消费", "以旧换新")):
            goals.append("激活新能源汽车需求")
        if any(term in normalized for term in ("产业", "布局", "供应链")):
            goals.append("改善产业布局与供应链协同")
        tools = ["西部中央承担比例", "中部中央承担比例", "东部中央承担比例"]
        if "消费" in normalized:
            tools.append("省级消费端支持（内生决策）")
        if any(term in normalized for term in ("建厂", "固定成本", "运营成本")):
            tools.append("省级固定/可变成本支持（内生决策）")
        event_hints: list[str] = []
        for term, hint in (
            ("智能网联", "可配置智驾能力升级事件"),
            ("L3", "可配置 L3 责任边界事件"),
            ("油价", "可配置油价冲击事件"),
            ("供应链", "可配置电池节点或供应链事件"),
        ):
            if term.lower() in normalized.lower():
                event_hints.append(hint)
        unmodeled = [
            f"“{term}”尚未进入可执行机制"
            for term in ("税收减免", "信贷利率", "城市限行", "出口配额")
            if term in normalized
        ]
        policy = PolicyV4(
            policy_id=_stable_id("policy", normalized, shares),
            west_central_share=shares["west"],
            central_central_share=shares["central"],
            east_central_share=shares["east"],
        )
        summary = (
            f"可执行中央参数为西部 {shares['west']:.0%}、中部 {shares['central']:.0%}、"
            f"东部 {shares['east']:.0%}；其他条款已分类为省级内生决策、事件提示或暂未建模。"
        )
        return PolicyInterpretation(
            interpretation_id=_stable_id("interpretation", normalized),
            source_text=normalized,
            policy_goals=goals[:8],
            target_subjects=["中央政策操作者", "31 个省级模拟 Agent", "10 家车企模拟 Agent"],
            policy_tools=tools[:10],
            executable_policy=policy,
            execution_period="一个冻结模拟周期（双分支同轮次）",
            core_constraints=["三档比例独立取值 0–100%", "环境计算结果，Agent 仅选择行动"],
            ambiguities=[]
            if "%" in normalized
            else ["原文未给出明确三档比例，已使用 2025 年政策参考基线。"],
            unmodeled_clauses=unmodeled,
            event_design_hints=event_hints,
            recommended_metrics=[
                "区域发展差距",
                "中央财政负担",
                "地方财政压力",
                "新能源汽车需求",
                "新增投资集中度",
                "产业集聚度",
            ],
            public_summary=summary,
        )

    async def create_experiment(
        self,
        policy_text: str,
        *,
        seed: int = 20260812,
        experiment_id: str | None = None,
    ) -> WorldStateV6:
        interpretation = self.interpret_policy(policy_text)
        experiment_id = experiment_id or f"exp_m32_{uuid4().hex[:12]}"
        if not EXPERIMENT_ID_PATTERN.fullmatch(experiment_id):
            raise ValueError("EXPERIMENT_ID_INVALID")
        if self.has_experiment(experiment_id):
            existing = self.runtimes[experiment_id].world
            if (
                existing.interpretation.source_text == interpretation.source_text
                and existing.seed == seed
            ):
                return existing.model_copy(deep=True)
            raise ValueError("EXPERIMENT_ID_CONFLICT")
        world = WorldStateV6(
            experiment_id=experiment_id,
            journey_step=JourneyStep.CENTRAL_INTERPRETATION,
            status=V32ExperimentStatus.AWAITING_INTERPRETATION_CONFIRMATION,
            interpretation=interpretation,
            seed=seed,
        )
        world.versions.update(
            {
                "province_agent_model": self.agent_provider.model_name_for("province_proposal"),
                "automaker_agent_model": self.agent_provider.model_name_for("automaker_final"),
                "agent_provider_mode": self.agent_provider.run_mode,
            }
        )
        runtime = V32Runtime(world=world)
        self.runtimes[experiment_id] = runtime
        await self._emit(
            runtime,
            "interpretation.generated",
            payload={"interpretation_id": interpretation.interpretation_id},
        )
        await self._persist(runtime)
        return world.model_copy(deep=True)

    async def confirm_interpretation(
        self, experiment_id: str, interpretation: PolicyInterpretation
    ) -> WorldStateV6:
        runtime = self._runtime(experiment_id)
        async with runtime.lock:
            confirmed_interpretation = interpretation.model_copy(update={"status": "confirmed"})
            if runtime.world.status is not V32ExperimentStatus.AWAITING_INTERPRETATION_CONFIRMATION:
                if runtime.world.interpretation == confirmed_interpretation:
                    return runtime.world.model_copy(deep=True)
                raise ValueError("interpretation cannot be changed after confirmation")
            original = runtime.world.interpretation
            if interpretation.interpretation_id != original.interpretation_id:
                raise ValueError("INTERPRETATION_ID_MISMATCH")
            if interpretation.source_text != original.source_text:
                raise ValueError("INTERPRETATION_SOURCE_TEXT_MISMATCH")
            if interpretation.executable_policy.reference_policy_year != 2025:
                raise ValueError("INTERPRETATION_POLICY_YEAR_INVALID")
            runtime.world.interpretation = confirmed_interpretation
            runtime.world.journey_step = JourneyStep.EXPERIMENT_DESIGN
            runtime.world.status = V32ExperimentStatus.AWAITING_DESIGN_CONFIRMATION
            await self._emit(
                runtime,
                "interpretation.confirmed",
                payload={"interpretation_id": interpretation.interpretation_id},
            )
            await self._persist(runtime)
            return runtime.world.model_copy(deep=True)

    async def confirm_design(self, experiment_id: str, design: ExperimentDesign) -> WorldStateV6:
        runtime = self._runtime(experiment_id)
        async with runtime.lock:
            if runtime.world.status is not V32ExperimentStatus.AWAITING_DESIGN_CONFIRMATION:
                if runtime.world.design == design:
                    return runtime.world.model_copy(deep=True)
                raise ValueError("design cannot be changed in the current status")
            runtime.world.design = design
            runtime.world.journey_step = JourneyStep.BASELINE_CONFIRMATION
            runtime.world.status = V32ExperimentStatus.AWAITING_BASELINE_CONFIRMATION
            await self._emit(
                runtime,
                "design.confirmed",
                payload={"experiment_type": design.experiment_type.value},
            )
            await self._persist(runtime)
            return runtime.world.model_copy(deep=True)

    async def confirm_baseline(
        self, experiment_id: str, *, expected_data_version: str | None = None
    ) -> WorldStateV6:
        runtime = self._runtime(experiment_id)
        async with runtime.lock:
            if runtime.world.status is not V32ExperimentStatus.AWAITING_BASELINE_CONFIRMATION:
                if runtime.world.baseline is not None:
                    if (
                        expected_data_version is not None
                        and expected_data_version != runtime.world.baseline.data_version
                    ):
                        raise ValueError(
                            "BASELINE_DATA_VERSION_MISMATCH: expected "
                            f"{expected_data_version}, frozen {runtime.world.baseline.data_version}"
                        )
                    return runtime.world.model_copy(deep=True)
                raise ValueError("baseline cannot be confirmed in the current status")
            if runtime.world.design is None:
                raise ValueError("experiment design is required")
            if (
                expected_data_version is not None
                and expected_data_version != self.m29.manifest.data_version
            ):
                raise ValueError(
                    "BASELINE_DATA_VERSION_MISMATCH: expected "
                    f"{expected_data_version}, active {self.m29.manifest.data_version}"
                )
            snapshot_payload = {
                "profiles": self.profiles,
                "automakers": self.automaker_profiles,
                "personas": self.personas,
                "relations": self.relation_network,
                "m29_snapshot_hash": self.m29.manifest.snapshot_hash,
                "seed": runtime.world.seed,
                "versions": runtime.world.versions,
            }
            state_hash = canonical_hash(snapshot_payload)
            checkpoint_id = f"checkpoint_v32_{state_hash[:16]}"
            runtime.world.baseline = BaselineSnapshot(
                checkpoint_id=checkpoint_id,
                state_hash=state_hash,
                quality_counts=[
                    QualityCount(
                        quality=V32DataQuality.VERIFIED,
                        field_count=(
                            self.m29.manifest.quality_counts.get("trusted", 0)
                            + self.m29.manifest.counts.get("derived_features", 0)
                        ),
                        explanation="可信公开来源与具备合理依据的统一推算，详情保留来源和计算方法。",
                    ),
                ],
                missing_value_policy=self.m29.manifest.missing_value_policy,
                uncovered_content=runtime.world.interpretation.unmodeled_clauses,
                data_version=self.m29.manifest.data_version,
                relation_network_version=self.m29.relation_network.schema_version,
            )
            runtime.world.relation_network = self.relation_network
            runtime.world.automaker_personas = self.automaker_personas
            runtime.world.versions["cache_key"] = canonical_hash(
                {
                    "interpretation": runtime.world.interpretation,
                    "design": runtime.world.design,
                    "baseline_hash": state_hash,
                    "seed": runtime.world.seed,
                    "versions": runtime.world.versions,
                }
            )
            runtime.world.branches = {
                "control": BranchRuntimeState(
                    branch_id="control",
                    kind=BranchKind.CONTROL,
                    label="原始方案",
                    parent_checkpoint_id=checkpoint_id,
                    policy=runtime.world.design.control_policy,
                    event_applied=self._event_applies(
                        runtime.world.design.event_plan, BranchKind.CONTROL
                    ),
                ),
                "treatment": BranchRuntimeState(
                    branch_id="treatment",
                    kind=BranchKind.TREATMENT,
                    label="干预方案",
                    parent_checkpoint_id=checkpoint_id,
                    policy=runtime.world.design.treatment_policy,
                    event_applied=self._event_applies(
                        runtime.world.design.event_plan, BranchKind.TREATMENT
                    ),
                ),
            }
            for branch in runtime.world.branches.values():
                branch.province_resource_envelopes = {
                    code: self._province_envelope(branch, code) for code in MAINLAND_PROVINCE_CODES
                }
                branch.automaker_resource_envelopes = {
                    automaker_id: self._automaker_envelope(branch, automaker_id)
                    for automaker_id in AUTOMAKER_IDS
                }
            runtime.world.journey_step = JourneyStep.SIMULATION_RUN
            runtime.world.status = V32ExperimentStatus.READY
            await self._emit(
                runtime, "baseline.confirmed", payload={"checkpoint_id": checkpoint_id}
            )
            await self._emit(runtime, "branches.created", payload={"branch_count": 2})
            await self._persist(runtime)
            return runtime.world.model_copy(deep=True)

    @staticmethod
    def _event_applies(event: EventPlan | None, kind: BranchKind) -> bool:
        return bool(event and (event.branch_scope == "both" or kind is BranchKind.TREATMENT))

    async def run(
        self, experiment_id: str, *, until_round: SimulationRound | None = None
    ) -> WorldStateV6:
        runtime = self._runtime(experiment_id)
        async with runtime.lock:
            for branch in runtime.world.branches.values():
                self._assert_round_prefix(branch)
            if runtime.world.status not in {
                V32ExperimentStatus.READY,
                V32ExperimentStatus.RUNNING,
            }:
                if runtime.world.status is V32ExperimentStatus.COMPLETED:
                    return runtime.world.model_copy(deep=True)
                raise ValueError("experiment is not ready to run")
            runtime.world.status = V32ExperimentStatus.RUNNING
            target = until_round or SimulationRound.ENVIRONMENT_SETTLEMENT
            if (
                target is SimulationRound.ENVIRONMENT_SETTLEMENT
                and self.cache_enabled
                and self._restore_cache(runtime)
            ):
                await self._emit(
                    runtime,
                    "cache.hit",
                    payload={"cache_key": runtime.world.versions["cache_key"]},
                )
                await self._persist(runtime)
                return runtime.world.model_copy(deep=True)
            for round_name in ROUND_SEQUENCE:
                if all(
                    round_name in branch.completed_rounds
                    for branch in runtime.world.branches.values()
                ):
                    if round_name is target:
                        break
                    continue
                if round_name is SimulationRound.PROVINCE_REVISION:
                    await self._execute_province_revision_round(runtime)
                elif round_name is SimulationRound.PROVINCE_COUNTER_RESPONSE:
                    await self._province_counter_response_round(runtime)
                else:
                    await asyncio.gather(
                        *(
                            self._execute_round(runtime, branch, round_name)
                            for branch in runtime.world.branches.values()
                        )
                    )
                # Round gate: no branch can advance until both branches completed the same round.
                if not all(
                    round_name in branch.completed_rounds
                    for branch in runtime.world.branches.values()
                ):
                    raise RuntimeError(f"round gate incomplete: {round_name.value}")
                for branch in runtime.world.branches.values():
                    self._assert_round_prefix(branch)
                for branch in runtime.world.branches.values():
                    fallback_count = self._round_fallback_count(branch, round_name)
                    await self._emit(
                        runtime,
                        f"{round_name.value}.completed",
                        branch_id=branch.branch_id,
                        round_name=round_name,
                        payload={
                            "province_action_count": len(
                                branch.province_final_actions or branch.province_initial_actions
                            ),
                            "automaker_action_count": len(
                                branch.automaker_final_actions or branch.automaker_initial_actions
                            ),
                            "fallback_count": fallback_count,
                        },
                    )
                await self._emit(
                    runtime,
                    "round.completed",
                    round_name=round_name,
                    payload={"round": round_name.value, "branch_count": 2},
                )
                await self._persist(runtime)
                if round_name is target:
                    break
            if all(
                SimulationRound.ENVIRONMENT_SETTLEMENT in branch.completed_rounds
                for branch in runtime.world.branches.values()
            ):
                runtime.comparison = self._build_comparison(runtime.world)
                runtime.world.status = V32ExperimentStatus.COMPLETED
                runtime.world.journey_step = JourneyStep.RESULT_REVIEW
                await self._emit(
                    runtime,
                    "comparison.completed",
                    payload={"delta_gap": runtime.comparison.delta_gap},
                )
            else:
                runtime.world.status = V32ExperimentStatus.READY
            await self._persist(runtime)
            return runtime.world.model_copy(deep=True)

    @staticmethod
    def _round_fallback_count(branch: BranchRuntimeState, round_name: SimulationRound) -> int:
        actions = {
            SimulationRound.PROVINCE_INITIAL: branch.province_initial_actions.values(),
            SimulationRound.AUTOMAKER_INITIAL: branch.automaker_initial_actions.values(),
            SimulationRound.PROVINCE_REVISION: branch.province_final_actions.values(),
            SimulationRound.AUTOMAKER_NEGOTIATION: branch.automaker_negotiation_actions.values(),
            SimulationRound.PROVINCE_COUNTER_RESPONSE: (),
            SimulationRound.AUTOMAKER_FINAL: branch.automaker_final_actions.values(),
            SimulationRound.ENVIRONMENT_SETTLEMENT: (),
        }[round_name]
        return sum(action.fallback_used for action in actions)

    @staticmethod
    def _assert_round_prefix(branch: BranchRuntimeState) -> None:
        expected = list(SimulationRound)[: len(branch.completed_rounds)]
        if branch.completed_rounds != expected:
            raise RuntimeError(
                f"ROUND_SEQUENCE_INVALID: {branch.branch_id} completed rounds are not a prefix"
            )

    async def _execute_round(
        self, runtime: V32Runtime, branch: BranchRuntimeState, round_name: SimulationRound
    ) -> None:
        branch.current_round = round_name
        if round_name is SimulationRound.PROVINCE_INITIAL:
            await self._province_initial(runtime.world, branch)
        elif round_name is SimulationRound.AUTOMAKER_INITIAL:
            await self._automaker_actions(runtime.world, branch, stage="initial")
        elif round_name is SimulationRound.PROVINCE_REVISION:
            raise RuntimeError("province revision must use the synchronized 3A/3B gate")
        elif round_name is SimulationRound.AUTOMAKER_NEGOTIATION:
            await self._automaker_actions(runtime.world, branch, stage="negotiation")
        elif round_name is SimulationRound.PROVINCE_COUNTER_RESPONSE:
            raise RuntimeError("counter responses must use the synchronized gate")
        elif round_name is SimulationRound.AUTOMAKER_FINAL:
            await self._automaker_actions(runtime.world, branch, stage="final")
        else:
            self._settle_environment(runtime.world, branch)
        branch.completed_rounds.append(round_name)

    def _relations(self, source: str, relation_type: str) -> list[ProvinceRelation]:
        return [
            relation
            for relation in self.relation_network.relations
            if relation.source_code == source and relation.relation_type == relation_type
        ]

    def _province_envelope(self, branch: BranchRuntimeState, code: str) -> ProvinceResourceEnvelope:
        profile = self.profiles[code]
        share = branch.policy.share_for_region(profile.policy_region.value)
        available = _clamp(
            0.30 + 0.32 * profile.fiscal_capacity + 0.18 * share,
            0.30,
            0.78,
        )
        cap = _clamp(available * 0.72, 0.20, 0.60)
        return ProvinceResourceEnvelope(
            envelope_id=_stable_id("province_envelope", branch.branch_id, code, available),
            branch_id=branch.branch_id,
            province_code=code,
            available_policy_budget=available,
            consumer_cap=cap,
            fixed_cost_cap=cap,
            variable_cost_cap=cap,
            fiscal_risk_limit=_clamp(0.64 + 0.25 * profile.fiscal_capacity),
            evidence_refs=[
                f"policy:{branch.policy.policy_id}",
                *[f"fact:{item}" for item in self.m29.province_profiles[code].fact_refs[:2]],
            ],
        )

    def _automaker_envelope(
        self, branch: BranchRuntimeState, automaker_id: str
    ) -> AutomakerResourceEnvelope:
        persona = self.automaker_personas[automaker_id]
        market_budget = round(
            max(
                8.0,
                min(
                    20.0,
                    11.0
                    + 7.0 * persona.growth_goal
                    + 3.0 * persona.channel_expansion_tendency
                    - 5.0 * persona.cashflow_constraint,
                ),
            ),
            4,
        )
        max_expand = max(
            2,
            min(
                5,
                round(
                    2
                    + 2.5 * persona.channel_expansion_tendency
                    + 0.5 * persona.growth_goal
                    - persona.cashflow_constraint
                ),
            ),
        )
        max_facilities = (
            3
            if persona.new_capacity_willingness >= 0.70
            else 2
            if persona.new_capacity_willingness >= 0.45
            else 1
        )
        return AutomakerResourceEnvelope(
            envelope_id=_stable_id(
                "automaker_envelope", branch.branch_id, automaker_id, market_budget
            ),
            branch_id=branch.branch_id,
            automaker_id=automaker_id,
            national_market_budget=market_budget,
            max_expand_provinces=max_expand,
            facility_budget=round(
                max_facilities * (0.45 + 0.45 * persona.new_capacity_willingness), 4
            ),
            max_facility_targets=max_facilities,
            cashflow_constraint=persona.cashflow_constraint,
            capacity_pressure=persona.capacity_pressure,
            management_capacity=_clamp(
                1
                - 0.45 * persona.cashflow_constraint
                - 0.25 * persona.capacity_pressure
                + 0.25 * persona.channel_expansion_tendency
            ),
            evidence_refs=[
                f"persona:{automaker_id}",
                *[
                    f"fact:{item}"
                    for item in self.m29.automaker_profiles[automaker_id].fact_refs[:2]
                ],
            ],
        )

    @staticmethod
    def _validate_province_resources(
        action: ProvinceActionV5, envelope: ProvinceResourceEnvelope
    ) -> None:
        if action.overall_support_intensity > envelope.available_policy_budget + 1e-6:
            raise ValueError("province action exceeds available policy budget")
        allocations = (
            action.overall_support_intensity * action.subsidy_mix.consumer,
            action.overall_support_intensity * action.subsidy_mix.fixed_cost,
            action.overall_support_intensity * action.subsidy_mix.variable_cost,
        )
        caps = (envelope.consumer_cap, envelope.fixed_cost_cap, envelope.variable_cost_cap)
        if any(value > cap + 1e-6 for value, cap in zip(allocations, caps, strict=True)):
            raise ValueError("province tool allocation exceeds its resource cap")

    @staticmethod
    def _validate_automaker_resources(
        action: AutomakerActionV2, envelope: AutomakerResourceEnvelope
    ) -> None:
        total_market = sum(
            item.sales_investment_intensity for item in action.province_market_actions
        )
        expand_count = sum(
            item.channel_strategy is ChannelStrategy.EXPAND
            for item in action.province_market_actions
        )
        facility_total = sum(item.investment_intensity for item in action.facility_actions)
        if total_market > envelope.national_market_budget + 1e-6:
            raise ValueError("automaker national market budget exceeded")
        if expand_count > envelope.max_expand_provinces:
            raise ValueError("automaker channel expansion slot exceeded")
        if (
            len(action.facility_actions) > envelope.max_facility_targets
            or facility_total > envelope.facility_budget + 1e-6
        ):
            raise ValueError("automaker facility resource envelope exceeded")

    @staticmethod
    def _validate_enterprise_offer_responses(
        action: AutomakerActionV2, offers: list[ProvinceEnterpriseOffer]
    ) -> None:
        expected = {item.offer_id for item in offers}
        actual = {item.offer_id for item in action.enterprise_offer_responses}
        if expected != actual:
            raise ValueError("every received enterprise offer requires an explicit response")
        if sum(item.decision == "accept" for item in action.enterprise_offer_responses) > 5:
            raise ValueError("automaker can accept at most five enterprise offers")

    @staticmethod
    def _validate_final_offer_transitions(
        action: AutomakerActionV2,
        negotiation_action: AutomakerActionV2,
        counter_responses: list[ProvinceCounterOfferResponse],
    ) -> None:
        negotiation = {
            item.offer_id: item for item in negotiation_action.enterprise_offer_responses
        }
        accepted_counters = {
            item.counter_offer_id for item in counter_responses if item.decision == "accept"
        }
        for response in action.enterprise_offer_responses:
            previous = negotiation.get(response.offer_id)
            if previous is None:
                raise ValueError("final response requires a frozen negotiation response")
            can_accept = previous.decision == "accept" or (
                previous.decision == "counteroffer"
                and previous.counter_offer_id in accepted_counters
            )
            if response.decision == "counteroffer":
                raise ValueError("final confirmation cannot create a new counteroffer")
            if response.decision == "accept" and not can_accept:
                raise ValueError("final confirmation cannot accept a rejected negotiation path")

    def _finalize_enterprise_matches(self, branch: BranchRuntimeState) -> None:
        """Turn explicit final-round responses into deterministic, resource-safe matches."""
        by_offer = {item.offer_id: item for item in branch.province_enterprise_offers}
        branch.province_enterprise_offer_responses = []
        branch.province_enterprise_matches = []
        for automaker_id, action in branch.automaker_final_actions.items():
            envelope = branch.automaker_resource_envelopes[automaker_id]
            accepted = 0
            for response in action.enterprise_offer_responses:
                offer = by_offer[response.offer_id]
                branch.province_enterprise_offer_responses.append(response)
                legal = (
                    offer.target_automaker_id == automaker_id
                    and offer.channel_commitment_share + offer.industry_coordination_share <= 1
                    and offer.source_province_code in branch.province_final_actions
                )
                status = "rejected"
                channel = 0.0
                industry = 0.0
                summary = response.rejection_reason or "车企模拟主体未接受该资源包。"
                cooperation_actions: list[str] = []
                action_summary = ""
                province_action_ref: str | None = None
                automaker_action_ref: str | None = None
                if response.decision == "accept" and legal and accepted < 5:
                    accepted += 1
                    # Contributions are indices, never monetary commitments. They are bounded
                    # by existing provincial support and the automaker's remaining management room.
                    province_action = branch.province_final_actions[offer.source_province_code]
                    capacity = min(1.0, envelope.management_capacity)
                    channel = round(
                        min(
                            1.2,
                            1.2
                            * offer.channel_commitment_share
                            * province_action.overall_support_intensity
                            * capacity,
                        ),
                        4,
                    )
                    industry = round(
                        min(
                            1.0,
                            1.0
                            * offer.industry_coordination_share
                            * province_action.overall_support_intensity
                            * capacity,
                        ),
                        4,
                    )
                    status = "matched"
                    summary = "双方资源合法且车企明确接受；渠道与产业协同进入确定性环境。"
                    market_action = next(
                        item
                        for item in action.province_market_actions
                        if item.province_code == offer.source_province_code
                    )
                    if offer.channel_commitment_share > 0:
                        cooperation_actions.append(
                            "channel_expansion"
                            if market_action.channel_strategy is ChannelStrategy.EXPAND
                            else "channel_maintenance"
                        )
                    if offer.industry_coordination_share > 0:
                        cooperation_actions.append("industry_coordination")
                    facility = next(
                        (
                            item
                            for item in action.facility_actions
                            if item.province_code == offer.source_province_code
                        ),
                        None,
                    )
                    if facility is not None:
                        cooperation_actions.append(
                            {
                                FacilityActionKind.NEW_PLANT: "facility_new_plant",
                                FacilityActionKind.EXPAND: "facility_expansion",
                                FacilityActionKind.DELAY: "facility_delay",
                            }[facility.action]
                        )
                    cooperation_actions.append("policy_support")
                    action_labels = {
                        "channel_expansion": "渠道扩张",
                        "channel_maintenance": "渠道投入维持",
                        "facility_new_plant": "模拟新建产能意向",
                        "facility_expansion": "模拟扩产意向",
                        "facility_delay": "模拟延后产能意向",
                        "industry_coordination": "产业协同",
                        "policy_support": (
                            f"省级{_primary_policy_focus(province_action.subsidy_mix)}支持"
                        ),
                    }
                    action_summary = (
                        "合作内容："
                        + "、".join(action_labels[item] for item in cooperation_actions)
                        + "。"
                    )
                    province_action_ref = province_action.action_id
                    automaker_action_ref = action.action_id
                elif response.decision == "accept":
                    status = "resource_invalid"
                    summary = "接受意向未通过资源或接受上限校验，贡献为零。"
                branch.province_enterprise_matches.append(
                    ProvinceEnterpriseMatch(
                        match_id=_stable_id(
                            "province_enterprise_match", branch.branch_id, response.offer_id
                        ),
                        branch_id=branch.branch_id,
                        offer_id=response.offer_id,
                        response_id=response.response_id,
                        province_code=offer.source_province_code,
                        automaker_id=automaker_id,
                        status=status,
                        channel_contribution=channel,
                        industry_contribution=industry,
                        cooperation_actions=cooperation_actions,
                        action_summary=action_summary,
                        province_action_ref=province_action_ref,
                        automaker_action_ref=automaker_action_ref,
                        evidence_refs=offer.evidence_refs,
                        summary=summary,
                    )
                )

    def _derive_competition_outcomes(self, branch: BranchRuntimeState) -> None:
        """Record only near-miss losses that are supported by the frozen competition graph."""
        branch.competition_outcomes = []
        for automaker_id, action in branch.automaker_initial_actions.items():
            ranked = sorted(
                action.province_signals,
                key=lambda item: (item.investment_inclination, item.province_code),
                reverse=True,
            )
            winners = [item for item in ranked if item.decision == "expand"]
            for loser_rank, loser in enumerate(
                ranked[len(winners) : len(winners) + 3], start=len(winners) + 1
            ):
                related = [
                    relation
                    for winner in winners
                    for relation in self.relation_network.relations
                    if relation.relation_type == "competition"
                    and {relation.source_code, relation.target_code}
                    == {loser.province_code, winner.province_code}
                ]
                if not related:
                    continue
                relation = max(related, key=lambda item: item.weight)
                winner = next(
                    item
                    for item in winners
                    if item.province_code in {relation.source_code, relation.target_code}
                    and item.province_code != loser.province_code
                )
                rank = next(
                    index
                    for index, item in enumerate(ranked, start=1)
                    if item.province_code == winner.province_code
                )
                closeness = 1 - min(
                    1.0, abs(winner.investment_inclination - loser.investment_inclination) / 0.20
                )
                loss = round(100 * relation.weight * max(0.10, closeness) * 0.12, 4)
                branch.competition_outcomes.append(
                    CompetitionOutcome(
                        outcome_id=_stable_id(
                            "competition",
                            branch.branch_id,
                            automaker_id,
                            loser.province_code,
                            winner.province_code,
                        ),
                        branch_id=branch.branch_id,
                        automaker_id=automaker_id,
                        resource_type="channel_slot",
                        winner_province_code=winner.province_code,
                        loser_province_code=loser.province_code,
                        winner_rank=rank,
                        loser_rank=loser_rank,
                        relation_weight=relation.weight,
                        loss_index=loss,
                        trigger_condition="车企有限渠道扩张名额由竞争省获得，落选省处于临界排名窗口。",
                        evidence_refs=relation.evidence_refs,
                    )
                )
            facility_winners = [
                item
                for item in ranked
                if any(
                    facility.province_code == item.province_code
                    and facility.action.value in {"new_plant", "expand"}
                    for facility in action.facility_actions
                )
            ]
            for _loser_rank, loser in enumerate(
                [item for item in ranked if item not in facility_winners][:3], start=1
            ):
                related = [
                    relation
                    for winner in facility_winners
                    for relation in self.relation_network.relations
                    if relation.relation_type == "competition"
                    and {relation.source_code, relation.target_code}
                    == {loser.province_code, winner.province_code}
                ]
                if not related:
                    continue
                relation = max(related, key=lambda item: item.weight)
                winner = next(
                    item
                    for item in facility_winners
                    if item.province_code in {relation.source_code, relation.target_code}
                    and item.province_code != loser.province_code
                )
                winner_rank = next(
                    index
                    for index, item in enumerate(ranked, start=1)
                    if item.province_code == winner.province_code
                )
                actual_loser_rank = next(
                    index
                    for index, item in enumerate(ranked, start=1)
                    if item.province_code == loser.province_code
                )
                closeness = 1 - min(
                    1.0, abs(winner.investment_inclination - loser.investment_inclination) / 0.20
                )
                branch.competition_outcomes.append(
                    CompetitionOutcome(
                        outcome_id=_stable_id(
                            "competition_facility",
                            branch.branch_id,
                            automaker_id,
                            loser.province_code,
                            winner.province_code,
                        ),
                        branch_id=branch.branch_id,
                        automaker_id=automaker_id,
                        resource_type="facility_slot",
                        winner_province_code=winner.province_code,
                        loser_province_code=loser.province_code,
                        winner_rank=winner_rank,
                        loser_rank=actual_loser_rank,
                        relation_weight=relation.weight,
                        loss_index=round(100 * relation.weight * max(0.10, closeness) * 0.10, 4),
                        trigger_condition="车企有限产能重点名额由竞争省获得，落选省处于临界排名窗口。",
                        evidence_refs=relation.evidence_refs,
                    )
                )

    def _build_counter_offers(self, branch: BranchRuntimeState) -> None:
        offers = {item.offer_id: item for item in branch.province_enterprise_offers}
        branch.automaker_counter_offers = []
        for automaker_id, action in branch.automaker_negotiation_actions.items():
            for response in action.enterprise_offer_responses:
                if response.decision != "counteroffer":
                    continue
                offer = offers[response.offer_id]
                branch.automaker_counter_offers.append(
                    AutomakerCounterOffer(
                        counter_offer_id=response.counter_offer_id
                        or _stable_id(
                            "counter_offer", branch.branch_id, automaker_id, offer.offer_id
                        ),
                        branch_id=branch.branch_id,
                        offer_id=offer.offer_id,
                        automaker_id=automaker_id,
                        province_code=offer.source_province_code,
                        required_channel_share=round(
                            min(1.0, offer.channel_commitment_share + 0.04), 4
                        ),
                        required_industry_share=round(
                            min(1.0, offer.industry_coordination_share + 0.03), 4
                        ),
                        required_policy_focus=offer.offered_support_scope,
                        validity_condition="仅在省级既有财政包内重排资源且保留明确渠道扩张名额时生效。",
                        opportunity_cost="接受条件将压缩本省其他企业资源包和独立加码空间。",
                        evidence_refs=offer.evidence_refs,
                    )
                )

    async def _province_counter_response_round(self, runtime: V32Runtime) -> None:
        """All provincial counter-offer decisions are frozen before any final automaker action."""

        async def resolve_branch(branch: BranchRuntimeState) -> None:
            branch.current_round = SimulationRound.PROVINCE_COUNTER_RESPONSE
            by_province = {
                code: [
                    item for item in branch.automaker_counter_offers if item.province_code == code
                ]
                for code in MAINLAND_PROVINCE_CODES
            }

            async def resolve_one(code: str) -> list[ProvinceCounterOfferResponse]:
                incoming = by_province[code]
                ranked = sorted(
                    incoming,
                    key=lambda item: (
                        item.required_channel_share + item.required_industry_share,
                        item.counter_offer_id,
                    ),
                    reverse=True,
                )
                accepted = ranked[0].counter_offer_id if ranked else None
                fallback = ProvinceCounterOfferResponseBatch(
                    province_code=code,
                    responses=[
                        ProvinceCounterOfferResponse(
                            response_id=_stable_id(
                                "counter_response", branch.branch_id, code, item.counter_offer_id
                            ),
                            branch_id=branch.branch_id,
                            counter_offer_id=item.counter_offer_id,
                            province_code=code,
                            decision="accept" if item.counter_offer_id == accepted else "reject",
                            rejection_reason=None
                            if item.counter_offer_id == accepted
                            else "本轮仅保留一个可承受的企业条件。",
                            opportunity_cost="接受后减少其他资源包的可用协调空间。"
                            if item.counter_offer_id == accepted
                            else "拒绝后保留本省既有政策配置。",
                            change_condition=(
                                "车企继续保留本省 Top-K 渠道名额且资源不超出冻结财政包。"
                            ),
                            evidence_refs=item.evidence_refs,
                        )
                        for item in incoming
                    ],
                    decision_reasons=[
                        DecisionReason(
                            decision="逐项回应企业条件报价",
                            trigger_ref=incoming[0].counter_offer_id
                            if incoming
                            else branch.province_final_actions[code].action_id,
                            affected_fields=["enterprise_resource_package"],
                            summary="在既有财政空间和明确机会成本下最多接受一项反报价。",
                        )
                    ],
                    opportunity_costs=[
                        OpportunityCost(
                            chosen_action="保留一个条件成交名额",
                            forgone_or_delayed_action="并行接受多项企业条件",
                            resource_source="省级既有政策预算",
                            summary="避免对同一财政空间重复承诺。",
                        )
                    ],
                )
                batch = await self._resolve_agent(
                    branch,
                    agent_id=code,
                    kind="province_counter_response",
                    instruction="逐项接受或拒绝企业反报价；最多接受一项，不得新增财政、工具或现实承诺。",
                    payload={
                        "branch_id": branch.branch_id,
                        "province": self.m29.province_profiles[code],
                        "resource_envelope": branch.province_resource_envelopes[code],
                        "counter_offers": incoming,
                        "fallback": fallback,
                    },
                    response_type=ProvinceCounterOfferResponseBatch,
                    fallback=lambda fallback=fallback: fallback,
                )
                expected = {item.counter_offer_id for item in incoming}
                if (
                    batch.province_code != code
                    or {item.counter_offer_id for item in batch.responses} != expected
                ):
                    self._mark_orchestrator_fallback(
                        branch, agent_id=code, kind="province_counter_response", value=fallback
                    )
                    batch = fallback
                return batch.responses

            results = await asyncio.gather(*(resolve_one(code) for code in MAINLAND_PROVINCE_CODES))
            branch.province_counter_offer_responses = [
                item for result in results for item in result
            ]
            for code, responses in zip(MAINLAND_PROVINCE_CODES, results, strict=True):
                branch.decision_traces.append(
                    ProvinceDecisionTrace(
                        trace_id=_stable_id("counter_response_trace", branch.branch_id, code),
                        branch_id=branch.branch_id,
                        agent_id=code,
                        round=SimulationRound.PROVINCE_COUNTER_RESPONSE,
                        primary_goal="在既有财政空间内回应企业条件报价",
                        primary_choice=(
                            "接受一项企业条件"
                            if any(item.decision == "accept" for item in responses)
                            else "拒绝本轮企业条件"
                        ),
                        constraints=["不得新增财政或政策工具", "每省最多接受一项条件报价"],
                        observations=[
                            DecisionObservation(
                                source_type="automaker",
                                source_id=item.counter_offer_id,
                                observation_type="counter_offer",
                                summary="车企提出在既有资源包内调整条件的模拟请求。",
                                data_quality=V32DataQuality.PROXY,
                                evidence_refs=item.evidence_refs,
                            )
                            for item in by_province[code]
                        ],
                        initial_action_id=branch.province_final_actions[code].action_id,
                        alternatives_considered=["接受条件", "拒绝并保留既有政策"],
                        final_action_id=branch.province_final_actions[code].action_id,
                        decision_reasons=[
                            DecisionReason(
                                decision="回应企业反报价",
                                trigger_ref=responses[0].counter_offer_id
                                if responses
                                else branch.province_final_actions[code].action_id,
                                affected_fields=["enterprise_resource_package"],
                                summary="已对全部收到的企业条件报价形成显式回应。",
                            )
                        ],
                        rejected_alternatives=[],
                        change_conditions=[
                            ChangeCondition(
                                field="top_k_channel_slot",
                                operator="gte",
                                threshold=1,
                                action_if_met="在预算不变条件下重新评估企业条件",
                                evidence_refs=[
                                    f"action:{branch.province_final_actions[code].action_id}"
                                ],
                            )
                        ],
                        opportunity_costs=[
                            OpportunityCost(
                                chosen_action="保留一个条件成交名额",
                                forgone_or_delayed_action="并行接受多项企业条件",
                                resource_source="省级既有政策预算",
                                summary="避免对冻结财政空间重复承诺。",
                            )
                        ],
                        reasoning_summary="企业条件报价以显式接受或拒绝记录，不构成现实招商或合同。",
                        evidence_refs=[f"action:{branch.province_final_actions[code].action_id}"],
                        data_quality=V32DataQuality.PROXY,
                        confidence=TraceConfidence.MEDIUM,
                        confidence_basis="条件报价基于冻结资源包和代理画像，不代表现实企业协商结果。",
                        affected_agents=[item.automaker_id for item in by_province[code]],
                        peer_signals=[],
                        enterprise_signals=[item.automaker_id for item in by_province[code]],
                    )
                )
            branch.completed_rounds.append(SimulationRound.PROVINCE_COUNTER_RESPONSE)

        await asyncio.gather(
            *(resolve_branch(branch) for branch in runtime.world.branches.values())
        )

    def _event_visible(
        self,
        world: WorldStateV6,
        branch: BranchRuntimeState,
        agent_type: str,
        round_name: SimulationRound,
    ) -> bool:
        event = world.design.event_plan if world.design else None
        if not event or not branch.event_applied:
            return False
        trigger_round = {
            EventTriggerPoint.BEFORE_PROVINCE_INITIAL: SimulationRound.PROVINCE_INITIAL,
            EventTriggerPoint.AFTER_PROVINCE_INITIAL: SimulationRound.AUTOMAKER_INITIAL,
            EventTriggerPoint.AFTER_AUTOMAKER_INITIAL: SimulationRound.PROVINCE_REVISION,
        }[event.trigger_point]
        if round_name.order >= trigger_round.order:
            return True
        return event.advance_notice and agent_type in event.informed_agent_types

    async def _province_initial(self, world: WorldStateV6, branch: BranchRuntimeState) -> None:
        for code in MAINLAND_PROVINCE_CODES:
            profile = self.profiles[code]
            share = branch.policy.share_for_region(profile.policy_region.value)
            fiscal_space = _clamp(
                0.55 * profile.fiscal_capacity + 0.25 * (1 - profile.fiscal_rigidity) + 0.20 * share
            )
            envelope = branch.province_resource_envelopes[code]
            support = min(
                _clamp(0.22 + 0.42 * fiscal_space + 0.18 * profile.nev_industry_base),
                envelope.available_policy_budget,
            )
            consumer = 0.30 + 0.24 * profile.willingness_to_pay_index + 0.10 * profile.market_scale
            fixed = (
                0.27 + 0.25 * profile.vehicle_manufacturing_base + 0.10 * profile.nev_industry_base
            )
            variable = (
                0.23
                + 0.20 * (1 - profile.energy_cost_index)
                + 0.12 * (1 - profile.logistics_cost_index)
            )
            event_visible = self._event_visible(
                world, branch, "province", SimulationRound.PROVINCE_INITIAL
            )
            if event_visible and world.design and world.design.event_plan:
                consumer, fixed, variable = self._event_mix_shift(
                    world.design.event_plan, consumer, fixed, variable
                )
            mix = _normalize_mix(consumer, fixed, variable)
            action_id = _stable_id(
                "province_action",
                world.experiment_id,
                branch.branch_id,
                code,
                "initial",
                support,
                mix,
            )
            action = ProvinceActionV5(
                action_id=action_id,
                branch_id=branch.branch_id,
                province_code=code,
                round=SimulationRound.PROVINCE_INITIAL,
                overall_support_intensity=support,
                subsidy_mix=mix,
                response_mode="maintain",
                observed_peer_codes=[
                    item.target_code for item in self._relations(code, "observation")
                ],
                competition_peer_codes=[
                    item.target_code for item in self._relations(code, "competition")
                ],
                coordination_target_codes=[],
                primary_policy_focus=_primary_policy_focus(mix),
                reason_codes=[
                    "fiscal_space",
                    "central_share_relief",
                    "industry_and_demand_balance",
                ],
                summary=f"{profile.short_name}在财政空间内平衡消费激活、产能进入和运营成本支持。",
            )
            candidate_action = action
            action = await self._resolve_agent(
                branch,
                agent_id=code,
                kind="province_initial",
                instruction="在给定约束内选择省级初始支持强度和三类工具份额。",
                payload={
                    "profile": profile,
                    "raw_fact_summary": self.m29.province_profiles[code].fact_summary,
                    "raw_fact_refs": [
                        f"fact:{item}" for item in self.m29.province_profiles[code].fact_refs
                    ],
                    "derived_features": self.m29.province_profiles[code].feature_values,
                    "persona": self.personas[code],
                    "policy": branch.policy,
                    "resource_envelope": envelope,
                    "event_visible": event_visible,
                    "deterministic_candidate": action,
                },
                response_type=ProvinceActionV5,
                fallback=lambda action=candidate_action: action,
            )
            try:
                self._validate_province_resources(action, envelope)
            except ValueError:
                action = candidate_action.model_copy(update={"fallback_used": True})
                self._mark_orchestrator_fallback(
                    branch,
                    agent_id=code,
                    kind="province_initial",
                    value=action,
                )
                self._validate_province_resources(action, envelope)
            branch.province_initial_actions[code] = action
            observations = [
                DecisionObservation(
                    source_type="policy",
                    source_id=branch.policy.policy_id,
                    observation_type="central_cost_share",
                    summary=f"当前地区中央承担比例为 {share:.0%}。",
                    data_quality=V32DataQuality.SCENARIO_ASSUMPTION,
                    evidence_refs=[f"policy:{branch.policy.policy_id}"],
                )
            ]
            if event_visible and world.design and world.design.event_plan:
                observations.append(self._event_observation(world.design.event_plan))
            branch.decision_traces.append(
                ProvinceDecisionTrace(
                    trace_id=_stable_id("trace", action.action_id),
                    branch_id=branch.branch_id,
                    agent_id=code,
                    round=SimulationRound.PROVINCE_INITIAL,
                    primary_goal="在财政约束内平衡需求激活与产业承载",
                    primary_choice=f"以{_primary_policy_focus(action.subsidy_mix)}作为本轮主要政策取向。",
                    constraints=[item.value for item in self.personas[code].key_constraints],
                    observations=observations,
                    alternatives_considered=["消费优先", "固定成本优先", "运营成本优先"],
                    decision_reasons=[
                        DecisionReason(
                            decision="冻结初始三类政策组合",
                            trigger_ref=envelope.envelope_id,
                            affected_fields=["overall_support_intensity", "subsidy_mix"],
                            summary="支持强度和三类配置均受冻结资源包上限约束。",
                        )
                    ],
                    rejected_alternatives=[
                        RejectedAlternative(
                            alternative="三类工具同时加码",
                            rejection_basis="会超过可用政策预算或单项工具上限。",
                            evidence_refs=[f"resource:{envelope.envelope_id}"],
                        )
                    ],
                    change_conditions=[
                        ChangeCondition(
                            field="available_policy_budget",
                            operator="gte",
                            threshold=round(envelope.available_policy_budget + 0.05, 4),
                            action_if_met="在不突破财政警戒线时提高总体支持强度",
                            evidence_refs=[f"resource:{envelope.envelope_id}"],
                        )
                    ],
                    opportunity_costs=[
                        OpportunityCost(
                            chosen_action="维持三类工具平衡",
                            forgone_or_delayed_action="单一工具全面加码",
                            resource_source="省级可用政策预算",
                            summary="将有限预算保留给后续企业反馈与合作调整。",
                        )
                    ],
                    fallback_reason=(
                        "Agent Provider 不可用或输出未通过结构/资源校验。"
                        if action.fallback_used
                        else None
                    ),
                    fallback_scope="本省初始行动" if action.fallback_used else None,
                    final_action_id=action.action_id,
                    reasoning_summary=action.summary,
                    evidence_refs=[
                        *[
                            f"fact:{item}"
                            for item in self.m29.province_profiles[code].fact_refs[:3]
                        ],
                        f"policy:{branch.policy.policy_id}",
                    ],
                    data_quality=V32DataQuality.PROXY,
                    confidence=TraceConfidence.MEDIUM,
                    confidence_basis="M29 原始事实已引用，决策画像仍是可反算的派生代理特征。",
                    affected_agents=[],
                )
            )

    @staticmethod
    def _event_mix_shift(
        event: EventPlan, consumer: float, fixed: float, variable: float
    ) -> tuple[float, float, float]:
        shift = 0.04 * event.intensity.magnitude
        channels = " ".join(event.mechanism_channels).lower()
        if "consumer" in channels or "wtp" in channels or "oil" in event.template_id:
            return consumer + shift, fixed - shift / 2, variable - shift / 2
        if "battery" in channels or "supply" in channels:
            return consumer - shift / 2, fixed, variable + shift / 2
        return consumer - shift / 2, fixed + shift, variable - shift / 2

    @staticmethod
    def _event_observation(event: EventPlan) -> DecisionObservation:
        return DecisionObservation(
            source_type="event",
            source_id=event.event_plan_id,
            observation_type="scenario_information",
            summary=f"已知情景：{event.name}，强度为{event.intensity.value}。",
            data_quality=V32DataQuality.SCENARIO_ASSUMPTION,
            evidence_refs=event.evidence_refs,
        )

    def _province_score(
        self,
        automaker_id: str,
        code: str,
        action: ProvinceActionV5,
        event: EventPlan | None,
    ) -> float:
        profile = self.profiles[code]
        automaker = self.automaker_profiles[automaker_id]
        persona = self.automaker_personas[automaker_id]
        coverage = next(
            item.coverage_index
            for item in automaker.channel_coverage_by_province
            if item.province_code == code
        )
        terms = [
            (0.24 * persona.market_sensitivity, profile.willingness_to_pay_index),
            (0.24 * persona.subsidy_sensitivity, action.overall_support_intensity),
            (0.18 * persona.supply_chain_sensitivity, profile.nev_industry_base),
            (0.14 * persona.supply_chain_sensitivity, 1 - profile.battery_supply_distance_index),
            (0.12 * persona.channel_expansion_tendency, coverage),
            (0.08 * persona.market_sensitivity, automaker.sales_growth_index),
        ]
        denominator = sum(weight for weight, _ in terms)
        score = sum(weight * value for weight, value in terms) / denominator
        score -= 0.08 * persona.cashflow_constraint
        score -= 0.05 * persona.capacity_pressure * profile.land_cost_index
        if event:
            magnitude = event.intensity.magnitude
            if event.template_id == EventTemplateId.INTELLIGENT_DRIVING_UPGRADE.value:
                score += (
                    0.06
                    * magnitude
                    * persona.intelligent_driving_stage
                    * profile.intelligent_driving_readiness_index
                )
            elif event.template_id == EventTemplateId.L3_ENTERPRISE_LIABILITY_INCREASE.value:
                score -= 0.07 * magnitude * persona.regulation_sensitivity
            elif event.template_id == EventTemplateId.BATTERY_NODE_UPGRADE_SICHUAN.value:
                score += (
                    0.06
                    * magnitude
                    * persona.supply_chain_sensitivity
                    * (1 - profile.battery_supply_distance_index)
                )
            elif event.template_id == EventTemplateId.OIL_PRICE_RISE.value:
                score += (
                    0.05
                    * magnitude
                    * persona.market_sensitivity
                    * profile.oil_price_sensitivity_index
                )
            elif event.template_id == EventTemplateId.OIL_PRICE_FALL.value:
                score -= (
                    0.04
                    * magnitude
                    * persona.market_sensitivity
                    * profile.oil_price_sensitivity_index
                )
        return _clamp(score)

    def _fallback_market_reallocation(
        self,
        *,
        automaker_id: str,
        source_actions: dict[str, ProvinceActionV5],
        initial_actions: dict[str, ProvinceActionV5],
        market_actions: list[ProvinceMarketAction],
        max_expand_provinces: int,
    ) -> tuple[list[ProvinceMarketAction], str | None]:
        """Make the explicit non-model fallback expose a real, conserved trade-off.

        The recipient and donor are selected from policy changes and the frozen
        automaker persona. No province or pair is preselected. A live/cached Luna
        result bypasses this candidate entirely.
        """

        persona = self.automaker_personas[automaker_id]

        def policy_fit(action: ProvinceActionV5) -> float:
            support = action.overall_support_intensity
            return support * (
                persona.subsidy_sensitivity
                + persona.market_sensitivity * action.subsidy_mix.consumer
                + persona.new_capacity_willingness * action.subsidy_mix.fixed_cost
                + persona.supply_chain_sensitivity * action.subsidy_mix.variable_cost
            )

        changes = {
            code: policy_fit(source_actions[code]) - policy_fit(initial_actions[code])
            for code in MAINLAND_PROVINCE_CODES
        }
        recipient = max(changes, key=lambda code: (changes[code], code))
        donor = min(changes, key=lambda code: (changes[code], code))
        spread = changes[recipient] - changes[donor]
        if recipient == donor or spread <= 1e-6:
            return market_actions, None

        by_code = {item.province_code: item for item in market_actions}
        donor_value = by_code[donor].sales_investment_intensity
        recipient_value = by_code[recipient].sales_investment_intensity
        transfer = min(0.04, donor_value, 1 - recipient_value)
        if transfer < 0.005:
            return market_actions, None

        updated_values = {code: item.sales_investment_intensity for code, item in by_code.items()}
        updated_values[donor] -= transfer
        updated_values[recipient] += transfer
        expand_codes = set(
            sorted(
                updated_values,
                key=lambda code: (updated_values[code], code),
                reverse=True,
            )[:max_expand_provinces]
        )
        updated = [
            item.model_copy(
                update={
                    "sales_investment_intensity": _clamp(updated_values[item.province_code]),
                    "channel_strategy": (
                        ChannelStrategy.EXPAND
                        if item.province_code in expand_codes
                        else ChannelStrategy.MAINTAIN
                        if updated_values[item.province_code] >= 0.42
                        else ChannelStrategy.REDUCE
                    ),
                }
            )
            for item in market_actions
        ]
        recipient_name = policy_region_catalog()[recipient].short_name
        donor_name = policy_region_catalog()[donor].short_name
        return (
            updated,
            f"向{recipient_name}增加的渠道投入来自减少{donor_name}投入，保持全国市场预算守恒。",
        )

    async def _automaker_actions(
        self, world: WorldStateV6, branch: BranchRuntimeState, *, stage: str
    ) -> None:
        round_name = {
            "initial": SimulationRound.AUTOMAKER_INITIAL,
            "negotiation": SimulationRound.AUTOMAKER_NEGOTIATION,
            "final": SimulationRound.AUTOMAKER_FINAL,
        }[stage]
        negotiated = stage != "initial"
        final = stage == "final"
        if final:
            branch.top_k_reallocations = []
        source_actions = (
            branch.province_final_actions if negotiated else branch.province_initial_actions
        )
        if set(source_actions) != set(MAINLAND_PROVINCE_CODES):
            raise RuntimeError("automaker round requires complete province actions")
        event = (
            world.design.event_plan
            if world.design and self._event_visible(world, branch, "automaker", round_name)
            else None
        )
        for automaker_id in AUTOMAKER_IDS:
            scores = {
                code: self._province_score(automaker_id, code, source_actions[code], event)
                for code in MAINLAND_PROVINCE_CODES
            }
            ranked = sorted(scores, key=lambda code: (scores[code], code), reverse=True)
            priority_codes = ranked[:6]
            market_actions: list[ProvinceMarketAction] = []
            for code in MAINLAND_PROVINCE_CODES:
                score = scores[code]
                strategy = (
                    ChannelStrategy.EXPAND
                    if score >= 0.62
                    else ChannelStrategy.MAINTAIN
                    if score >= 0.42
                    else ChannelStrategy.REDUCE
                )
                market_actions.append(
                    ProvinceMarketAction(
                        province_code=code,
                        sales_investment_intensity=score,
                        channel_strategy=strategy,
                    )
                )
            persona = self.automaker_personas[automaker_id]
            facilities: list[FacilityAction] = []
            facility_limit = (
                3
                if persona.new_capacity_willingness >= 0.70
                else 2
                if persona.new_capacity_willingness >= 0.45
                else 1
            )
            for code in ranked[:facility_limit]:
                action_kind = FacilityActionKind.EXPAND
                existing = {
                    item.province_code
                    for item in self.automaker_profiles[automaker_id].production_footprint
                }
                if code not in existing and persona.new_capacity_willingness >= 0.55:
                    action_kind = FacilityActionKind.NEW_PLANT
                elif persona.cashflow_constraint > 0.70:
                    action_kind = FacilityActionKind.DELAY
                facilities.append(
                    FacilityAction(
                        province_code=code,
                        action=action_kind,
                        investment_intensity=_clamp(
                            scores[code] * persona.new_capacity_willingness
                        ),
                    )
                )
            mean_top = fmean(scores[code] for code in priority_codes)
            roi = "high" if mean_top >= 0.67 else "medium" if mean_top >= 0.48 else "low"
            previous = branch.automaker_initial_actions.get(automaker_id) if negotiated else None
            action_id = _stable_id(
                "automaker_action",
                world.experiment_id,
                branch.branch_id,
                automaker_id,
                round_name,
                market_actions,
                facilities,
            )
            envelope = self._automaker_envelope(branch, automaker_id)
            branch.automaker_resource_envelopes[automaker_id] = envelope
            market_scale = min(
                1.0,
                envelope.national_market_budget
                / max(0.0001, sum(item.sales_investment_intensity for item in market_actions)),
            )
            expand_codes = set(ranked[: envelope.max_expand_provinces])
            negotiation_reallocation: str | None = None
            if final and branch.automaker_counter_offers:
                counter_by_id = {
                    item.counter_offer_id: item
                    for item in branch.automaker_counter_offers
                    if item.automaker_id == automaker_id
                }
                rejected_codes = {
                    counter_by_id[item.counter_offer_id].province_code
                    for item in branch.province_counter_offer_responses
                    if item.decision == "reject" and item.counter_offer_id in counter_by_id
                }
                accepted_codes = {
                    counter_by_id[item.counter_offer_id].province_code
                    for item in branch.province_counter_offer_responses
                    if item.decision == "accept" and item.counter_offer_id in counter_by_id
                }
                released = sorted(expand_codes & rejected_codes)
                eligible = [
                    code
                    for code in ranked
                    if code not in expand_codes and code not in rejected_codes
                ]
                for loser, replacement in zip(released, eligible, strict=False):
                    expand_codes.remove(loser)
                    expand_codes.add(replacement)
                    rejected_response = next(
                        item
                        for item in branch.province_counter_offer_responses
                        if item.decision == "reject"
                        and item.counter_offer_id in counter_by_id
                        and counter_by_id[item.counter_offer_id].province_code == loser
                    )
                    branch.top_k_reallocations.append(
                        TopKReallocation(
                            reallocation_id=_stable_id(
                                "top_k_reallocation",
                                branch.branch_id,
                                automaker_id,
                                loser,
                                replacement,
                            ),
                            branch_id=branch.branch_id,
                            automaker_id=automaker_id,
                            resource_type="channel_slot",
                            released_province_code=loser,
                            recipient_province_code=replacement,
                            reason="省级拒绝企业条件后释放渠道名额，并由下一合格省份承接。",
                            evidence_refs=rejected_response.evidence_refs,
                        )
                    )
                if released:
                    negotiation_reallocation = (
                        f"{len(released)} 个未接受条件的渠道名额已重配给下一合格省份；"
                        f"已接受条件省份 {len(accepted_codes)} 个。"
                    )
            market_actions = [
                item.model_copy(
                    update={
                        "sales_investment_intensity": _clamp(
                            item.sales_investment_intensity * market_scale
                        ),
                        "channel_strategy": (
                            ChannelStrategy.EXPAND
                            if item.province_code in expand_codes
                            else ChannelStrategy.MAINTAIN
                            if item.sales_investment_intensity >= 0.42
                            else ChannelStrategy.REDUCE
                        ),
                    }
                )
                for item in market_actions
            ]
            market_actions = _conserve_market_budget(
                market_actions, envelope.national_market_budget
            )
            reallocation_cost: str | None = None
            if final and previous:
                market_actions, reallocation_cost = self._fallback_market_reallocation(
                    automaker_id=automaker_id,
                    source_actions=source_actions,
                    initial_actions=branch.province_initial_actions,
                    market_actions=market_actions,
                    max_expand_provinces=envelope.max_expand_provinces,
                )
                market_actions = _conserve_market_budget(
                    market_actions, envelope.national_market_budget
                )
            facility_scale = min(
                1.0,
                envelope.facility_budget
                / max(0.0001, sum(item.investment_intensity for item in facilities)),
            )
            facilities = [
                item.model_copy(
                    update={
                        "investment_intensity": _clamp(item.investment_intensity * facility_scale)
                    }
                )
                for item in facilities[: envelope.max_facility_targets]
            ]
            action_id = _stable_id(
                "automaker_action",
                world.experiment_id,
                branch.branch_id,
                automaker_id,
                round_name,
                market_actions,
                facilities,
            )
            province_signals = [
                AutomakerProvinceSignal(
                    signal_id=_stable_id("automaker_signal", action_id, code),
                    action_id=action_id,
                    automaker_id=automaker_id,
                    province_code=code,
                    decision=(
                        "expand"
                        if code in expand_codes
                        else "maintain"
                        if code not in ranked[-3:]
                        else "reduce"
                    ),
                    investment_direction=(
                        "increase"
                        if scores[code] >= 0.62
                        else "maintain"
                        if scores[code] >= 0.42
                        else "decrease"
                    ),
                    investment_inclination=scores[code],
                    attraction_factors=["市场规模", "政策支持", "供应链可达性"],
                    primary_constraints=["现金流约束", "产能与管理半径"],
                    reconsideration_condition="市场吸引力、政策支持或资源约束发生可验证变化。",
                    evidence_refs=[
                        f"feature:{self.m29.province_profiles[code].feature_refs['market_scale']}",
                        f"feature:{self.m29.province_profiles[code].feature_refs['supply_chain_complementarity_index']}",
                    ],
                )
                for code in MAINLAND_PROVINCE_CODES
            ]
            received_enterprise_offers = (
                [
                    item
                    for item in branch.province_enterprise_offers
                    if item.target_automaker_id == automaker_id
                ]
                if negotiated
                else []
            )
            ordered_offers = sorted(
                received_enterprise_offers,
                key=lambda item: (
                    item.channel_commitment_share + item.industry_coordination_share,
                    -item.priority,
                    item.offer_id,
                ),
                reverse=True,
            )
            accepted_counter_ids = {
                item.counter_offer_id
                for item in branch.province_counter_offer_responses
                if item.decision == "accept"
            }
            negotiation_action = branch.automaker_negotiation_actions.get(automaker_id)
            negotiation_by_offer = {
                item.offer_id: item
                for item in (
                    negotiation_action.enterprise_offer_responses
                    if negotiation_action is not None
                    else []
                )
            }
            deterministic_offer_responses: list[ProvinceEnterpriseOfferResponse] = []
            for index, offer in enumerate(ordered_offers):
                counter_offer_id = _stable_id(
                    "counter_offer", branch.branch_id, automaker_id, offer.offer_id
                )
                prior_response = negotiation_by_offer.get(offer.offer_id)
                proposes_counter = stage == "negotiation" and index < min(
                    3, envelope.max_expand_provinces
                )
                confirms_offer = (
                    stage == "final"
                    and prior_response is not None
                    and (
                        prior_response.decision == "accept"
                        or (
                            prior_response.decision == "counteroffer"
                            and prior_response.counter_offer_id in accepted_counter_ids
                        )
                    )
                )
                deterministic_offer_responses.append(
                    ProvinceEnterpriseOfferResponse(
                        response_id=_stable_id(
                            "enterprise_offer_response",
                            branch.branch_id,
                            automaker_id,
                            round_name,
                            offer.offer_id,
                        ),
                        branch_id=branch.branch_id,
                        offer_id=offer.offer_id,
                        automaker_id=automaker_id,
                        decision=(
                            "counteroffer"
                            if proposes_counter
                            else "accept"
                            if confirms_offer
                            else "reject"
                        ),
                        rejection_reason=(
                            None
                            if proposes_counter or confirms_offer
                            else (
                                "全国渠道与产业协同名额已被更高匹配度资源包占用或条件未获省级接受。"
                            )
                        ),
                        counter_offer_id=counter_offer_id if proposes_counter else None,
                        opportunity_cost=(
                            "条件成交将占用本车企的渠道名额与管理资源。"
                            if proposes_counter
                            else "未成交资源将转向下一合格省份。"
                        ),
                        evidence_refs=offer.evidence_refs,
                    )
                )
            action = AutomakerActionV2(
                action_id=action_id,
                previous_action_id=previous.action_id if previous else None,
                branch_id=branch.branch_id,
                automaker_id=automaker_id,
                round=round_name,
                province_market_actions=market_actions,
                province_signals=province_signals,
                facility_actions=facilities,
                enterprise_offer_responses=deterministic_offer_responses,
                primary_commitment=(
                    f"优先在{policy_region_catalog()[priority_codes[0]].short_name}配置渠道与产能资源。"
                ),
                simulated_roi_band=roi,
                reason_codes=[
                    "market_fit",
                    "subsidy_support",
                    "supply_chain",
                    "cashflow_and_capacity_constraint",
                ],
                summary=(
                    f"{automaker_catalog()[automaker_id].display_name}模拟主体在现金流与"
                    f"全国资源约束下完成31省渠道投入决定，并优先配置一项主承诺。"
                ),
                resource_envelope_id=envelope.envelope_id,
                opportunity_costs=[
                    *([negotiation_reallocation] if negotiation_reallocation else []),
                    *([reallocation_cost] if reallocation_cost else []),
                    "扩大部分省份渠道将占用全国市场预算并压缩其他省份投入。",
                    "新增或扩产意向将占用产能与管理资源。",
                ][:6],
            )
            deterministic_action = action
            action = await self._resolve_agent(
                branch,
                agent_id=automaker_id,
                kind=f"automaker_{stage}",
                instruction=(
                    "根据31省政策、冻结Persona和可见事件，为每省明确选择扩张、维持或收缩；"
                    "谈判轮须逐项接受、拒绝或提出条件反报价；最终确认轮须只确认已经成交的资源包并重配被拒资源。"
                ),
                payload={
                    "profile": self.automaker_profiles[automaker_id],
                    "raw_fact_summary": self.m29.automaker_profiles[automaker_id].fact_summary,
                    "raw_fact_refs": [
                        f"fact:{item}"
                        for item in self.m29.automaker_profiles[automaker_id].fact_refs
                    ],
                    "derived_features": self.m29.automaker_profiles[automaker_id].feature_values,
                    "persona": persona,
                    "province_actions": source_actions,
                    "event": event,
                    "previous_action": previous,
                    "enterprise_offers": received_enterprise_offers,
                    "counter_offer_responses": branch.province_counter_offer_responses,
                    "deterministic_candidate": action,
                },
                response_type=AutomakerActionV2,
                fallback=lambda action=deterministic_action: action,
            )
            try:
                self._validate_automaker_resources(action, envelope)
                self._validate_enterprise_offer_responses(action, received_enterprise_offers)
                if final:
                    self._validate_final_offer_transitions(
                        action,
                        branch.automaker_negotiation_actions[automaker_id],
                        branch.province_counter_offer_responses,
                    )
            except ValueError:
                action = deterministic_action.model_copy(update={"fallback_used": True})
                self._mark_orchestrator_fallback(
                    branch,
                    agent_id=automaker_id,
                    kind=f"automaker_{stage}",
                    value=action,
                )
                self._validate_automaker_resources(action, envelope)
                self._validate_enterprise_offer_responses(action, received_enterprise_offers)
                if final:
                    self._validate_final_offer_transitions(
                        action,
                        branch.automaker_negotiation_actions[automaker_id],
                        branch.province_counter_offer_responses,
                    )
            destination = (
                branch.automaker_initial_actions
                if stage == "initial"
                else branch.automaker_negotiation_actions
                if stage == "negotiation"
                else branch.automaker_final_actions
            )
            destination[automaker_id] = action
            deltas: list[ActionDelta] = []
            if previous:
                previous_map = {
                    item.province_code: item for item in previous.province_market_actions
                }
                for item in action.province_market_actions:
                    before = previous_map[item.province_code].sales_investment_intensity
                    if abs(item.sales_investment_intensity - before) >= 0.005:
                        deltas.append(
                            ActionDelta(
                                field=f"province_market_actions.{item.province_code}",
                                before=before,
                                after=item.sales_investment_intensity,
                                display_summary=(
                                    f"{policy_region_catalog()[item.province_code].short_name}"
                                    f"投入强度变化 "
                                    f"{item.sales_investment_intensity - before:+.3f}。"
                                ),
                                trigger_refs=[previous.action_id],
                            )
                        )
            observations = [
                DecisionObservation(
                    source_type="province",
                    source_id=source_actions[code].action_id,
                    observation_type="province_policy",
                    summary=(
                        f"{policy_region_catalog()[code].short_name}支持强度 "
                        f"{source_actions[code].overall_support_intensity:.2f}。"
                    ),
                    data_quality=V32DataQuality.PROXY,
                    evidence_refs=[f"action:{source_actions[code].action_id}"],
                )
                for code in priority_codes[:4]
            ]
            if event:
                observations.append(self._event_observation(event))
            branch.decision_traces.append(
                AutomakerDecisionTrace(
                    trace_id=_stable_id("trace", action.action_id),
                    branch_id=branch.branch_id,
                    agent_id=automaker_id,
                    round=round_name,
                    primary_goal="在现金流和产能约束下提高全国市场与产能布局匹配度",
                    primary_choice=action.primary_commitment,
                    constraints=[
                        f"现金流约束 {persona.cashflow_constraint:.2f}",
                        f"产能压力 {persona.capacity_pressure:.2f}",
                    ],
                    observations=observations,
                    initial_action_id=previous.action_id if previous else None,
                    alternatives_considered=["渠道扩张优先", "产能布局优先", "现金流约束优先"],
                    final_action_id=action.action_id,
                    action_delta=deltas[:20],
                    decision_reasons=[
                        DecisionReason(
                            decision="为31省作出明确渠道决定并保留一项主承诺",
                            trigger_ref=envelope.envelope_id,
                            affected_fields=["province_market_actions", "facility_actions"],
                            summary="31省投入、渠道扩张和设施意向共同消耗冻结资源包。",
                        )
                    ],
                    rejected_alternatives=[
                        RejectedAlternative(
                            alternative="同时扩大所有省份投入",
                            rejection_basis="超过全国市场投入预算和管理能力。",
                            evidence_refs=[f"resource:{envelope.envelope_id}"],
                        )
                    ],
                    change_conditions=[
                        ChangeCondition(
                            field="province_policy_score",
                            operator="gte",
                            threshold=0.62,
                            action_if_met="重新评估并争取进入渠道扩张名额",
                            evidence_refs=[f"resource:{envelope.envelope_id}"],
                        )
                    ],
                    opportunity_costs=[
                        OpportunityCost(
                            chosen_action="集中资源于明确的渠道与产能行动",
                            forgone_or_delayed_action=item,
                            resource_source="全国市场与设施资源包",
                            summary=item,
                        )
                        for item in action.opportunity_costs
                    ],
                    fallback_reason=(
                        "Agent Provider 不可用或全国资源约束校验未通过。"
                        if action.fallback_used
                        else None
                    ),
                    fallback_scope=("本车企当轮全国行动" if action.fallback_used else None),
                    reasoning_summary=action.summary,
                    evidence_refs=[
                        *[
                            f"fact:{item}"
                            for item in self.m29.automaker_profiles[automaker_id].fact_refs[:3]
                        ],
                        f"persona:{automaker_id}",
                    ],
                    data_quality=V32DataQuality.PROXY,
                    confidence=TraceConfidence.MEDIUM,
                    confidence_basis="企业公开资料映射为冻结代理指标，不是企业未来行动概率。",
                    affected_agents=priority_codes,
                    received_enterprise_offer_refs=[
                        f"offer:{item.offer_id}" for item in action.enterprise_offer_responses
                    ],
                    enterprise_offer_response_refs=[
                        f"offer-response:{item.response_id}"
                        for item in action.enterprise_offer_responses
                    ],
                )
            )
        if stage == "initial":
            self._derive_competition_outcomes(branch)
        elif stage == "negotiation":
            self._build_counter_offers(branch)
        else:
            self._finalize_enterprise_matches(branch)

    async def _execute_province_revision_round(self, runtime: V32Runtime) -> None:
        branches = list(runtime.world.branches.values())
        for branch in branches:
            branch.current_round = SimulationRound.PROVINCE_REVISION
        await asyncio.gather(
            *(self._province_proposal_subround(runtime.world, branch) for branch in branches)
        )
        if any(len(branch.province_proposed_actions) != 31 for branch in branches):
            raise RuntimeError("all 31 province proposals must freeze before responses")
        for branch in branches:
            await self._emit(
                runtime,
                "province_proposals.frozen",
                branch_id=branch.branch_id,
                round_name=SimulationRound.PROVINCE_REVISION,
                payload={
                    "province_count": 31,
                    "proposal_count": len(branch.province_coordination_proposals),
                },
            )
        await asyncio.gather(
            *(self._province_response_subround(runtime.world, branch) for branch in branches)
        )
        for branch in branches:
            if len(branch.province_final_actions) != 31:
                raise RuntimeError("province response gate requires 31 final actions")
            branch.completed_rounds.append(SimulationRound.PROVINCE_REVISION)
            await self._emit(
                runtime,
                "province_responses.completed",
                branch_id=branch.branch_id,
                round_name=SimulationRound.PROVINCE_REVISION,
                payload={
                    "response_count": len(branch.province_coordination_responses),
                    "matched_count": sum(
                        item.status == "matched" for item in branch.coordination_records
                    ),
                },
            )

    def _enterprise_signals(
        self, branch: BranchRuntimeState, province_code: str
    ) -> list[AutomakerProvinceSignal]:
        signals = [
            next(item for item in action.province_signals if item.province_code == province_code)
            for action in branch.automaker_initial_actions.values()
        ]
        if len(signals) != 10:
            raise RuntimeError("each province must receive ten automaker signals")
        return signals

    def _partner_cards(self, source_code: str) -> list[dict[str, object]]:
        prior_by_target = {
            item.target_code: item for item in self._relations(source_code, "coordination")
        }
        return [
            {
                "province_code": code,
                "name": self.profiles[code].short_name,
                "fact_summary": self.m29.province_profiles[code].fact_summary,
                "features": {
                    key: self.m29.province_profiles[code].feature_values[key]
                    for key in (
                        "market_scale",
                        "nev_industry_base",
                        "vehicle_manufacturing_base",
                        "supply_chain_complementarity_index",
                        "rd_activity",
                        "logistics_cost_index",
                    )
                },
                "existing_relation": code in prior_by_target,
                "relation_weight": prior_by_target[code].weight
                if code in prior_by_target
                else None,
                "relation_refs": prior_by_target[code].evidence_refs
                if code in prior_by_target
                else [],
                "fact_refs": [
                    f"fact:{item}" for item in self.m29.province_profiles[code].fact_refs[:2]
                ],
            }
            for code in MAINLAND_PROVINCE_CODES
            if code != source_code
        ]

    def _fallback_proposal_batch(
        self, world: WorldStateV6, branch: BranchRuntimeState, code: str
    ) -> ProvinceProposalBatch:
        initial = branch.province_initial_actions[code]
        competition_loss = sum(
            item.loss_index
            for item in branch.competition_outcomes
            if item.loser_province_code == code
        )
        observation_codes = [item.target_code for item in self._relations(code, "observation")]
        competition_codes = [item.target_code for item in self._relations(code, "competition")]
        cards = self._partner_cards(code)
        ranked = sorted(
            cards,
            key=lambda item: (
                bool(item["existing_relation"]),
                float(item["relation_weight"] or 0),
                float(item["features"]["supply_chain_complementarity_index"]),
                str(item["province_code"]),
            ),
            reverse=True,
        )
        partner = ranked[0]
        target = str(partner["province_code"])
        relation_refs = list(partner["relation_refs"])
        evidence_refs = relation_refs or [
            *[f"fact:{item}" for item in self.m29.province_profiles[code].fact_refs[:1]],
            *list(partner["fact_refs"])[:1],
        ]
        counter_shift = min(0.06, competition_loss / 100)
        action = ProvinceActionV5(
            action_id=_stable_id(
                "province_proposed_action", world.experiment_id, branch.branch_id, code
            ),
            previous_action_id=initial.action_id,
            branch_id=branch.branch_id,
            province_code=code,
            round=SimulationRound.PROVINCE_REVISION,
            overall_support_intensity=min(
                branch.province_resource_envelopes[code].available_policy_budget,
                round(initial.overall_support_intensity + counter_shift, 4),
            ),
            subsidy_mix=(
                _normalize_mix(
                    initial.subsidy_mix.consumer + counter_shift,
                    initial.subsidy_mix.fixed_cost + counter_shift / 2,
                    initial.subsidy_mix.variable_cost,
                )
                if competition_loss > 0
                else initial.subsidy_mix
            ),
            response_mode="differentiate" if competition_loss > 0 else "maintain",
            observed_peer_codes=observation_codes,
            competition_peer_codes=competition_codes,
            coordination_target_codes=[target],
            primary_policy_focus=_primary_policy_focus(initial.subsidy_mix),
            reason_codes=[
                "agent_context_review",
                "competition_counteraction" if competition_loss > 0 else "coordination_soft_prior",
            ],
            summary=(
                "规则兜底基于有限渠道名额产生的竞争损失调整政策，并发起可拒绝协同提议。"
                if competition_loss > 0
                else "规则兜底仅维持初始政策，并从现有关系上下文发起一项可拒绝的协同提议。"
            ),
            fallback_used=True,
        )
        proposal = ProvinceCoordinationProposal(
            proposal_id=_stable_id("coordination_proposal", branch.branch_id, code, target),
            branch_id=branch.branch_id,
            source_province_code=code,
            target_province_code=target,
            priority=1,
            basis_type="existing_relation" if relation_refs else "inferred_from_context",
            cooperation_focus="supply_chain",
            offered_capability="共享本省产业节点、市场或运营能力",
            requested_capability="获得对方供应链、研发测试或物流互补能力",
            source_success_delta=SubsidyMixDelta(consumer=-0.02, variable_cost=0.02),
            target_success_delta=SubsidyMixDelta(fixed_cost=0.02, variable_cost=-0.02),
            fallback_delta=SubsidyMixDelta(),
            evidence_completeness=0.65 if relation_refs else 0.45,
            complementarity=float(partner["features"]["supply_chain_complementarity_index"]),
            goal_alignment=0.6,
            public_reason="合作对象来自冻结关系和产业上下文；该输出仅在模型不可用时接管。",
            evidence_refs=evidence_refs[:8],
        )
        envelope = branch.province_resource_envelopes[code]
        enterprise_signals = sorted(
            self._enterprise_signals(branch, code),
            key=lambda item: (item.investment_inclination, item.automaker_id),
            reverse=True,
        )
        enterprise_offers: list[ProvinceEnterpriseOffer] = []
        if initial.overall_support_intensity >= 0.42:
            for priority, signal in enumerate(enterprise_signals[:2], start=1):
                enterprise_offers.append(
                    ProvinceEnterpriseOffer(
                        offer_id=_stable_id(
                            "province_enterprise_offer", branch.branch_id, code, signal.automaker_id
                        ),
                        branch_id=branch.branch_id,
                        source_province_code=code,
                        target_automaker_id=signal.automaker_id,
                        priority=priority,
                        channel_commitment_share=round(0.14 - 0.02 * (priority - 1), 4),
                        industry_coordination_share=round(0.10 - 0.01 * (priority - 1), 4),
                        offered_support_scope=_primary_policy_focus(initial.subsidy_mix),
                        activation_condition="车企明确接受且不突破双方冻结资源包。",
                        opportunity_cost="该资源包只从既有政策优先级中调度，会压缩其他渠道或产业协同空间。",
                        public_reason="基于本省最终政策取向与车企初步信号发起模拟协同资源包。",
                        evidence_refs=signal.evidence_refs[:4],
                    )
                )
        return ProvinceProposalBatch(
            province_code=code,
            proposed_action=action,
            proposals=[proposal],
            enterprise_decision="offer" if enterprise_offers else "no_offer",
            enterprise_no_offer_reason=None
            if enterprise_offers
            else "当前政策强度不足以在不挤占基本政策目标的前提下发起资源包。",
            enterprise_offers=enterprise_offers,
            decision_reasons=[
                DecisionReason(
                    decision="维持政策并发起协同提议",
                    trigger_ref=envelope.envelope_id,
                    affected_fields=["subsidy_mix", "coordination_target_codes"],
                    summary="在资源包内保留政策结构，把潜在变化放到合作条件中。",
                )
            ],
            rejected_alternatives=[
                RejectedAlternative(
                    alternative="无条件提高总体支持",
                    rejection_basis="缺少可说明的预算来源与机会成本。",
                    evidence_refs=[f"resource:{envelope.envelope_id}"],
                )
            ],
            change_conditions=[
                ChangeCondition(
                    field="accepted_coordination_count",
                    operator="gte",
                    threshold=1,
                    action_if_met="应用双方约定的三类工具份额调整",
                    evidence_refs=evidence_refs[:2],
                )
            ],
            opportunity_costs=[
                OpportunityCost(
                    chosen_action="保留合作调整空间",
                    forgone_or_delayed_action="立即扩大单省补贴",
                    resource_source="省级可用政策预算",
                    summary="合作未确认前不预占额外预算。",
                )
            ],
        )

    async def _province_proposal_subround(
        self, world: WorldStateV6, branch: BranchRuntimeState
    ) -> None:
        if set(branch.automaker_initial_actions) != set(AUTOMAKER_IDS):
            raise RuntimeError("proposal subround requires all automaker initial actions")

        async def resolve_one(code: str) -> ProvinceProposalBatch:
            fallback = self._fallback_proposal_batch(world, branch, code)
            peers = fallback.proposed_action.observed_peer_codes
            event = (
                world.design.event_plan
                if world.design
                and self._event_visible(
                    world, branch, "province", SimulationRound.PROVINCE_REVISION
                )
                else None
            )
            batch = await self._resolve_agent(
                branch,
                agent_id=code,
                kind="province_proposal",
                instruction=(
                    "基于本省事实、三名观察Peer行动、十家车企对本省的完整评价和30省合作画像，"
                    "自主调整政策，并独立决定0至2项省际协同和0至2项定向省企资源包；未发起省企资源包时必须明确说明原因。"
                    "现有关系只是软先验；网外对象必须引用至少两项上下文。"
                ),
                payload={
                    "experiment_id": world.experiment_id,
                    "branch_id": branch.branch_id,
                    "province": self.m29.province_profiles[code],
                    "persona": self.personas[code],
                    "resource_envelope": branch.province_resource_envelopes[code],
                    "initial_action": branch.province_initial_actions[code],
                    "peer_actions": {peer: branch.province_initial_actions[peer] for peer in peers},
                    "automaker_signals": self._enterprise_signals(branch, code),
                    "competition_relations": self._relations(code, "competition"),
                    "competition_outcomes": [
                        item
                        for item in branch.competition_outcomes
                        if item.loser_province_code == code
                    ],
                    "coordination_priors": self._relations(code, "coordination"),
                    "partner_cards": self._partner_cards(code),
                    "event": event,
                },
                response_type=ProvinceProposalBatch,
                fallback=lambda fallback=fallback: fallback,
            )
            try:
                if (
                    batch.province_code != code
                    or batch.proposed_action.branch_id != branch.branch_id
                ):
                    raise ValueError("proposal identity mismatch")
                self._validate_province_resources(
                    batch.proposed_action, branch.province_resource_envelopes[code]
                )
                known = set(MAINLAND_PROVINCE_CODES)
                if any(item.target_province_code not in known for item in batch.proposals):
                    raise ValueError("unknown coordination target")
                if any(
                    item.target_automaker_id not in AUTOMAKER_IDS
                    for item in batch.enterprise_offers
                ):
                    raise ValueError("unknown enterprise offer target")
                if (
                    len(batch.enterprise_offers)
                    > branch.province_resource_envelopes[code].max_enterprise_offers
                ):
                    raise ValueError("enterprise offer budget exceeded")
                return batch
            except ValueError:
                self._mark_orchestrator_fallback(
                    branch,
                    agent_id=code,
                    kind="province_proposal",
                    value=fallback,
                )
                return fallback

        batches = await asyncio.gather(*(resolve_one(code) for code in MAINLAND_PROVINCE_CODES))
        for batch in batches:
            branch.province_proposed_actions[batch.province_code] = batch.proposed_action
            branch.province_proposal_batches[batch.province_code] = batch
            branch.province_coordination_proposals.extend(batch.proposals)
            branch.province_enterprise_offers.extend(batch.enterprise_offers)

    def _fallback_response_batch(
        self, branch: BranchRuntimeState, code: str, incoming: list[ProvinceCoordinationProposal]
    ) -> ProvinceResponseBatch:
        ranked = sorted(
            incoming,
            key=lambda item: (
                item.evidence_completeness,
                item.complementarity,
                item.goal_alignment,
                -item.priority,
                item.proposal_id,
            ),
            reverse=True,
        )
        accepted_id = ranked[0].proposal_id if ranked else None
        base = branch.province_proposed_actions[code]
        responses = [
            ProvinceCoordinationResponse(
                response_id=_stable_id(
                    "coordination_response", branch.branch_id, code, item.proposal_id
                ),
                branch_id=branch.branch_id,
                proposal_id=item.proposal_id,
                responding_province_code=code,
                decision="accept" if item.proposal_id == accepted_id else "reject",
                conditions_checked=["合作目标一致", "资源包可承受", "机会成本已说明"],
                rejection_reason=None
                if item.proposal_id == accepted_id
                else "同轮只保留一个生效合作。",
                opportunity_cost=(
                    "接受后将减少单省独立加码空间。"
                    if item.proposal_id == accepted_id
                    else "拒绝后保留本省预算与管理资源。"
                ),
                final_action_ref=base.action_id,
                evidence_refs=item.evidence_refs[:8],
            )
            for item in incoming
        ]
        return ProvinceResponseBatch(
            province_code=code,
            base_final_action=base,
            responses=responses,
            decision_reasons=[
                DecisionReason(
                    decision="逐项核验收到的合作提议",
                    trigger_ref=incoming[0].proposal_id if incoming else base.action_id,
                    affected_fields=["coordination_target_codes", "subsidy_mix"],
                    summary="规则兜底仅按证据完整度和互补度选择一个可承受提议。",
                )
            ],
            opportunity_costs=[
                OpportunityCost(
                    chosen_action="最多接受一项合作",
                    forgone_or_delayed_action="并行接受多项合作",
                    resource_source="省级管理能力与政策预算",
                    summary="避免同一轮对有限资源重复承诺。",
                )
            ],
        )

    async def _province_response_subround(
        self, world: WorldStateV6, branch: BranchRuntimeState
    ) -> None:
        proposals = list(branch.province_coordination_proposals)

        async def resolve_one(code: str) -> ProvinceResponseBatch:
            incoming = [item for item in proposals if item.target_province_code == code]
            fallback = self._fallback_response_batch(branch, code, incoming)
            batch = await self._resolve_agent(
                branch,
                agent_id=code,
                kind="province_response",
                instruction=(
                    "读取所有发给本省的冻结合作提议，逐项接受或拒绝；最多接受一项，"
                    "说明条件、拒绝原因和机会成本，不读取另一分支。"
                ),
                payload={
                    "experiment_id": world.experiment_id,
                    "branch_id": branch.branch_id,
                    "province": self.m29.province_profiles[code],
                    "persona": self.personas[code],
                    "resource_envelope": branch.province_resource_envelopes[code],
                    "proposed_action": branch.province_proposed_actions[code],
                    "incoming_proposals": incoming,
                    "source_partner_cards": [
                        next(
                            item
                            for item in self._partner_cards(code)
                            if item["province_code"] == proposal.source_province_code
                        )
                        for proposal in incoming
                    ],
                },
                response_type=ProvinceResponseBatch,
                fallback=lambda fallback=fallback: fallback,
            )
            try:
                if (
                    batch.province_code != code
                    or batch.base_final_action.branch_id != branch.branch_id
                ):
                    raise ValueError("response identity mismatch")
                expected = {item.proposal_id for item in incoming}
                actual = {item.proposal_id for item in batch.responses}
                if expected != actual:
                    raise ValueError("every incoming proposal requires one response")
                self._validate_province_resources(
                    batch.base_final_action, branch.province_resource_envelopes[code]
                )
                return batch
            except ValueError:
                self._mark_orchestrator_fallback(
                    branch,
                    agent_id=code,
                    kind="province_response",
                    value=fallback,
                )
                return fallback

        batches = await asyncio.gather(*(resolve_one(code) for code in MAINLAND_PROVINCE_CODES))
        response_batches = {item.province_code: item for item in batches}
        branch.province_response_batches = response_batches
        branch.province_coordination_responses = [
            response for batch in batches for response in batch.responses
        ]
        self._finalize_coordination(branch, response_batches)
        self._build_province_revision_traces(branch, response_batches)

    @staticmethod
    def _apply_subsidy_delta(action: ProvinceActionV5, delta: SubsidyMixDelta) -> ProvinceActionV5:
        mix = SubsidyMix(
            consumer=round(action.subsidy_mix.consumer + delta.consumer, 6),
            fixed_cost=round(action.subsidy_mix.fixed_cost + delta.fixed_cost, 6),
            variable_cost=round(action.subsidy_mix.variable_cost + delta.variable_cost, 6),
        )
        return action.model_copy(update={"subsidy_mix": mix})

    def _finalize_coordination(
        self, branch: BranchRuntimeState, response_batches: dict[str, ProvinceResponseBatch]
    ) -> None:
        proposals = sorted(
            branch.province_coordination_proposals,
            key=lambda item: (item.priority, item.proposal_id),
        )
        response_by_proposal = {
            item.proposal_id: item for item in branch.province_coordination_responses
        }
        actions = {code: batch.base_final_action for code, batch in response_batches.items()}
        occupied: set[str] = set()
        matched: list[ProvinceCoordinationProposal] = []
        records: list[CoordinationRecord] = []
        for proposal in proposals:
            response = response_by_proposal.get(proposal.proposal_id)
            status = "unmatched"
            summary = "目标省份未返回有效接受，保留提议但贡献为零。"
            if response and response.decision == "reject":
                status = "rejected"
                summary = response.rejection_reason or "目标省份拒绝合作。"
            elif response and not (
                {proposal.source_province_code, proposal.target_province_code} & occupied
            ):
                try:
                    source_action = self._apply_subsidy_delta(
                        actions[proposal.source_province_code], proposal.source_success_delta
                    )
                    target_action = self._apply_subsidy_delta(
                        actions[proposal.target_province_code], proposal.target_success_delta
                    )
                    self._validate_province_resources(
                        source_action,
                        branch.province_resource_envelopes[proposal.source_province_code],
                    )
                    self._validate_province_resources(
                        target_action,
                        branch.province_resource_envelopes[proposal.target_province_code],
                    )
                    actions[proposal.source_province_code] = source_action
                    actions[proposal.target_province_code] = target_action
                    occupied.update({proposal.source_province_code, proposal.target_province_code})
                    matched.append(proposal)
                    status = "matched"
                    summary = "提议被接受且双方资源合法，合作进入最终政策。"
                except ValueError:
                    status = "resource_invalid"
                    summary = "接受意向超出双方资源约束，贡献为零并使用备选行动。"
            elif response:
                summary = "提议虽被接受，但主体已按Agent优先级生效另一项合作。"
            pair = sorted((proposal.source_province_code, proposal.target_province_code))
            relation_refs = [
                ref
                for edge in self.relation_network.relations
                if edge.relation_type == "coordination"
                and {edge.source_code, edge.target_code} == set(pair)
                for ref in edge.evidence_refs
            ]
            records.append(
                CoordinationRecord(
                    coordination_id=_stable_id(
                        "coordination", branch.branch_id, proposal.proposal_id
                    ),
                    proposal_id=proposal.proposal_id,
                    response_id=response.response_id if response else None,
                    eligibility_ref=(
                        relation_refs[0] if relation_refs else f"context:{proposal.proposal_id}"
                    ),
                    branch_id=branch.branch_id,
                    left_province_code=pair[0],
                    right_province_code=pair[1],
                    status=status,
                    contribution=(
                        round(1.5 * fmean((proposal.complementarity, proposal.goal_alignment)), 4)
                        if status == "matched"
                        else 0
                    ),
                    evidence_refs=(relation_refs or proposal.evidence_refs)[:8],
                    summary=summary,
                )
            )
        for code, action in actions.items():
            own_matched = [
                item
                for item in matched
                if code in {item.source_province_code, item.target_province_code}
            ]
            if not own_matched:
                own_proposals = sorted(
                    [item for item in proposals if item.source_province_code == code],
                    key=lambda item: (item.priority, item.proposal_id),
                )
                if own_proposals:
                    try:
                        fallback_action = self._apply_subsidy_delta(
                            action, own_proposals[0].fallback_delta
                        )
                        self._validate_province_resources(
                            fallback_action, branch.province_resource_envelopes[code]
                        )
                        action = fallback_action
                    except ValueError:
                        pass
            targets = [
                item.target_province_code
                if item.source_province_code == code
                else item.source_province_code
                for item in own_matched
            ]
            mode = "coordinate" if targets else action.response_mode
            reasons = list(
                dict.fromkeys(
                    [
                        *action.reason_codes,
                        "coordination_matched" if targets else "coordination_not_matched",
                    ]
                )
            )[:8]
            action_id = _stable_id(
                "province_action", branch.branch_id, code, action.subsidy_mix, mode, targets
            )
            branch.province_final_actions[code] = action.model_copy(
                update={
                    "action_id": action_id,
                    "response_mode": mode,
                    "coordination_target_codes": targets,
                    "reason_codes": reasons,
                    "summary": (
                        f"读取3个观察Peer、10家车企评价及合作响应后形成最终政策；"
                        f"生效合作 {len(targets)} 项。"
                    ),
                }
            )
        for record in records:
            record.applied_action_refs = (
                [
                    branch.province_final_actions[record.left_province_code].action_id,
                    branch.province_final_actions[record.right_province_code].action_id,
                ]
                if record.status == "matched"
                else []
            )
        branch.coordination_records = records

    def _build_province_revision_traces(
        self, branch: BranchRuntimeState, response_batches: dict[str, ProvinceResponseBatch]
    ) -> None:
        for code in MAINLAND_PROVINCE_CODES:
            initial = branch.province_initial_actions[code]
            final = branch.province_final_actions[code]
            proposal_batch = branch.province_proposal_batches[code]
            response_batch = response_batches[code]
            signals = self._enterprise_signals(branch, code)
            incoming = [
                item
                for item in branch.province_coordination_proposals
                if item.target_province_code == code
            ]
            records = [
                item
                for item in branch.coordination_records
                if code in {item.left_province_code, item.right_province_code}
            ]
            trigger_refs = [
                *[item.signal_id for item in signals],
                *[item.proposal_id for item in proposal_batch.proposals],
                *[item.response_id for item in response_batch.responses],
            ]
            support_delta = final.overall_support_intensity - initial.overall_support_intensity
            consumer_delta = final.subsidy_mix.consumer - initial.subsidy_mix.consumer
            fixed_delta = final.subsidy_mix.fixed_cost - initial.subsidy_mix.fixed_cost
            variable_delta = final.subsidy_mix.variable_cost - initial.subsidy_mix.variable_cost
            deltas = [
                ActionDelta(
                    field=field,
                    before=before,
                    after=after,
                    display_summary=summary,
                    trigger_refs=trigger_refs[:8] or [initial.action_id],
                )
                for field, before, after, summary in (
                    (
                        "overall_support_intensity",
                        initial.overall_support_intensity,
                        final.overall_support_intensity,
                        f"总体支持强度 {support_delta:+.3f}",
                    ),
                    (
                        "subsidy_mix.consumer",
                        initial.subsidy_mix.consumer,
                        final.subsidy_mix.consumer,
                        f"消费端份额 {consumer_delta:+.3f}",
                    ),
                    (
                        "subsidy_mix.fixed_cost",
                        initial.subsidy_mix.fixed_cost,
                        final.subsidy_mix.fixed_cost,
                        f"固定成本份额 {fixed_delta:+.3f}",
                    ),
                    (
                        "subsidy_mix.variable_cost",
                        initial.subsidy_mix.variable_cost,
                        final.subsidy_mix.variable_cost,
                        f"可变成本份额 {variable_delta:+.3f}",
                    ),
                )
            ]
            observations = [
                DecisionObservation(
                    source_type="province",
                    source_id=branch.province_initial_actions[peer].action_id,
                    observation_type="limited_peer_action",
                    summary=f"读取{policy_region_catalog()[peer].short_name}初始行动。",
                    data_quality=V32DataQuality.PROXY,
                    evidence_refs=[f"action:{branch.province_initial_actions[peer].action_id}"],
                )
                for peer in final.observed_peer_codes[:3]
            ]
            observations.extend(
                DecisionObservation(
                    source_type="automaker",
                    source_id=item.automaker_id,
                    observation_type="automaker_province_signal",
                    summary=(
                        f"{automaker_catalog()[item.automaker_id].display_name}对本省明确选择"
                        f"{item.decision}，投入倾向 "
                        f"{item.investment_inclination:.2f}。"
                    ),
                    data_quality=V32DataQuality.PROXY,
                    evidence_refs=item.evidence_refs[:6],
                )
                for item in signals
            )
            branch.decision_traces.append(
                ProvinceDecisionTrace(
                    trace_id=_stable_id("trace", final.action_id),
                    branch_id=branch.branch_id,
                    agent_id=code,
                    round=SimulationRound.PROVINCE_REVISION,
                    primary_goal="基于完整企业反馈与有限省际信息自主调整政策并协作",
                    primary_choice=(
                        f"以{final.primary_policy_focus}作为最终政策取向；"
                        f"省企资源包决策为{proposal_batch.enterprise_decision}。"
                    ),
                    constraints=[
                        *[item.value for item in self.personas[code].key_constraints],
                        "政策预算上限 "
                        f"{branch.province_resource_envelopes[code].available_policy_budget:.2f}",
                    ][:8],
                    observations=observations[:20],
                    initial_action_id=initial.action_id,
                    alternatives_considered=[
                        "保持初始结构",
                        "独立调整",
                        "提出合作",
                        "拒绝资源不匹配的合作",
                    ],
                    final_action_id=final.action_id,
                    action_delta=deltas,
                    decision_reasons=[
                        *proposal_batch.decision_reasons,
                        *response_batch.decision_reasons,
                    ][:12],
                    rejected_alternatives=proposal_batch.rejected_alternatives,
                    change_conditions=proposal_batch.change_conditions,
                    opportunity_costs=[
                        *proposal_batch.opportunity_costs,
                        *response_batch.opportunity_costs,
                    ][:8],
                    fallback_reason=(
                        "3A 提议或 3B 响应由显式规则接管。"
                        if (
                            proposal_batch.proposed_action.fallback_used
                            or response_batch.base_final_action.fallback_used
                        )
                        else None
                    ),
                    fallback_scope=(
                        "本省合作提议与响应"
                        if (
                            proposal_batch.proposed_action.fallback_used
                            or response_batch.base_final_action.fallback_used
                        )
                        else None
                    ),
                    coordination_proposal_refs=[
                        item.proposal_id for item in proposal_batch.proposals
                    ],
                    received_proposal_refs=[
                        *[item.proposal_id for item in incoming],
                        *[item.offer_id for item in proposal_batch.enterprise_offers],
                    ],
                    coordination_response_refs=[
                        item.response_id for item in response_batch.responses
                    ],
                    coordination_match_refs=[item.coordination_id for item in records],
                    reasoning_summary=final.summary,
                    evidence_refs=[
                        f"action:{initial.action_id}",
                        *[
                            f"action:{branch.automaker_initial_actions[item.automaker_id].action_id}"
                            for item in signals[:5]
                        ],
                        *[ref for item in proposal_batch.proposals for ref in item.evidence_refs],
                    ][:12],
                    data_quality=V32DataQuality.PROXY,
                    confidence=TraceConfidence.MEDIUM,
                    confidence_basis="依据完整度来自M29上下文、3个Peer行动、10家车企评价及实际提议响应。",
                    affected_agents=list(
                        dict.fromkeys(
                            [
                                *[item.automaker_id for item in signals],
                                *[item.target_province_code for item in proposal_batch.proposals],
                                *[item.source_province_code for item in incoming],
                            ]
                        )
                    )[:40],
                    peer_signals=final.observed_peer_codes[:3],
                    enterprise_signals=[item.automaker_id for item in signals],
                )
            )

    def _legacy_policy(self, policy: PolicyV4) -> PolicySchema:
        return self.default_policy.model_copy(
            update={
                "policy_id": policy.policy_id,
                "west_central_share": policy.west_central_share,
                "central_central_share": policy.central_central_share,
                "east_central_share": policy.east_central_share,
                "status": PolicyStatus.APPROVED,
                "mechanism_version": "nev-policy-env-v3",
            }
        )

    @staticmethod
    def _legacy_province_action(action: ProvinceActionV5) -> ProvinceAction:
        mode = {
            "maintain": PeerResponseMode.HOLD,
            "follow": PeerResponseMode.FOLLOW,
            "differentiate": PeerResponseMode.DIFFERENTIATE,
            "coordinate": PeerResponseMode.COORDINATE,
        }[action.response_mode]
        return ProvinceAction(
            action_id=action.action_id,
            previous_action_id=f"baseline_{action.province_code}",
            province_code=action.province_code,
            phase=Phase.Y2_Q1,
            overall_support_intensity=action.overall_support_intensity,
            subsidy_mix=action.subsidy_mix,
            peer_response_mode=mode,
            observed_peer_codes=action.observed_peer_codes[:3],
            reason_codes=[ProvinceReasonCode.FISCAL_SPACE, ProvinceReasonCode.PEER_DIFFERENTIATION],
            summary=action.summary[:80],
            run_mode=RunMode.FAKE,
        )

    @staticmethod
    def _legacy_automaker_action(action: AutomakerActionV2) -> AutomakerAction:
        return AutomakerAction(
            action_id=action.action_id,
            previous_action_id=f"baseline_{action.automaker_id}",
            automaker_id=action.automaker_id,
            phase=Phase.Y2_Q2,
            province_market_actions=action.province_market_actions,
            facility_actions=action.facility_actions,
            simulated_roi_band=SimulatedRoiBand(action.simulated_roi_band),
            reason_codes=[
                AutomakerReasonCode.SUBSIDY_SUPPORT,
                AutomakerReasonCode.FINANCIAL_CONSTRAINT,
            ],
            summary=action.summary[:80],
            run_mode=RunMode.FAKE,
        )

    def _legacy_event(
        self, event: EventPlan | None
    ) -> tuple[EventScenario | None, dict[str, ProvinceEventResponse] | None]:
        if event is None:
            return None, None
        template_id = EventTemplateId(event.template_id)
        template = event_scenario_catalog()[template_id]
        intensity = EventIntensity(event.intensity.value)
        scenario = EventScenario(
            scenario_id=event.event_plan_id,
            template_id=template_id,
            family=template.family,
            title=event.name,
            intensity=intensity,
            magnitude=intensity.magnitude,
            target_province_codes=template.target_province_codes,
            provenance_refs=event.evidence_refs,
        )
        channels = " ".join(event.mechanism_channels).lower()
        focus = (
            EventPolicyFocus.CONSUMER_SUPPORT
            if "consumer" in channels or "wtp" in channels
            else EventPolicyFocus.SUPPLY_CHAIN_COORDINATION
            if "supply" in channels or "battery" in channels
            else EventPolicyFocus.REGULATORY_PILOT
        )
        responses = {
            code: ProvinceEventResponse(
                response_id=_stable_id("event_response", event.event_plan_id, code),
                scenario_id=event.event_plan_id,
                province_code=code,
                response_mode=PeerResponseMode.HOLD,
                policy_focus=focus,
                response_intensity=event.intensity.magnitude,
                subsidy_mix_delta=SubsidyMixDelta(),
                evidence_refs=event.evidence_refs,
                summary=f"{policy_region_catalog()[code].short_name}按冻结事件暴露进入环境结算。",
            )
            for code in MAINLAND_PROVINCE_CODES
        }
        return scenario, responses

    def _coordination_matches(self, branch: BranchRuntimeState) -> list[CoordinationMatch]:
        matches: list[CoordinationMatch] = []
        for item in branch.coordination_records:
            matches.append(
                CoordinationMatch(
                    match_id=item.coordination_id,
                    scenario_id="v32_frozen_coordination",
                    left_province_code=item.left_province_code,
                    right_province_code=item.right_province_code,
                    status=(
                        CoordinationStatus.MATCHED
                        if item.status == "matched"
                        else CoordinationStatus.UNMATCHED
                    ),
                    policy_focus=EventPolicyFocus.SUPPLY_CHAIN_COORDINATION,
                    complementarity=_clamp(item.contribution / 1.5 if item.contribution else 0.5),
                    contribution=min(5, item.contribution),
                    evidence_refs=[f"relation:{item.coordination_id}"],
                )
            )
        return matches

    def _province_utility(
        self, branch: BranchRuntimeState, code: str, competition: tuple[float, float]
    ) -> ProvinceUtility:
        """A frozen, inspectable utility projection; it never authorizes an Agent action."""
        state = branch.province_states[code]
        axes = self.personas[code].axes
        raw_weights = {
            "demand": 0.22 + 0.08 * axes.consumption_activation,
            "industry": 0.22 + 0.08 * axes.industry_attraction,
            "enterprise": 0.16 + 0.06 * axes.industry_attraction,
            "coordination": 0.08 + 0.08 * axes.supply_chain_coordination,
            "fiscal": 0.18 + 0.08 * (1 - axes.fiscal_capacity),
            "competition": 0.14 + 0.08 * axes.peer_response_sensitivity,
        }
        total = sum(raw_weights.values())
        weights = {key: value / total for key, value in raw_weights.items()}
        enterprise_gain = min(
            100.0,
            100
            * sum(
                item.channel_contribution + item.industry_contribution
                for item in branch.province_enterprise_matches
                if item.province_code == code and item.status == "matched"
            ),
        )
        coordination_gain = min(
            100.0,
            25
            * sum(
                item.contribution
                for item in branch.coordination_records
                if item.status == "matched"
                and code in {item.left_province_code, item.right_province_code}
            ),
        )
        competition_loss = min(100.0, 100 * sum(competition))
        utility = (
            weights["demand"] * state.demand_index
            + weights["industry"] * state.industry_activity_index
            + weights["enterprise"] * enterprise_gain
            + weights["coordination"] * coordination_gain
            - weights["fiscal"] * state.fiscal_pressure_index
            - weights["competition"] * competition_loss
        )
        refs = [f"action:{branch.province_final_actions[code].action_id}"]
        refs.extend(
            f"competition:{item.outcome_id}"
            for item in branch.competition_outcomes
            if item.loser_province_code == code
        )
        return ProvinceUtility(
            utility_id=_stable_id("utility", branch.branch_id, code),
            branch_id=branch.branch_id,
            province_code=code,
            demand_index=state.demand_index,
            industry_index=state.industry_activity_index,
            enterprise_gain=round(enterprise_gain, 4),
            coordination_gain=round(coordination_gain, 4),
            fiscal_pressure=state.fiscal_pressure_index,
            competition_loss=round(competition_loss, 4),
            weights=weights,
            utility_index=round(utility, 4),
            evidence_refs=refs[:12],
        )

    def _settle_environment(self, world: WorldStateV6, branch: BranchRuntimeState) -> None:
        if set(branch.province_final_actions) != set(MAINLAND_PROVINCE_CODES) or set(
            branch.automaker_final_actions
        ) != set(AUTOMAKER_IDS):
            raise RuntimeError("environment settlement requires complete final actions")
        event = world.design.event_plan if world.design and branch.event_applied else None
        legacy_event, event_responses = self._legacy_event(event)
        enterprise_effects: dict[str, tuple[float, float]] = {}
        for match in branch.province_enterprise_matches:
            if match.status != "matched":
                continue
            channel, industry = enterprise_effects.get(match.province_code, (0.0, 0.0))
            enterprise_effects[match.province_code] = (
                round(channel + match.channel_contribution, 4),
                round(industry + match.industry_contribution, 4),
            )
        competition_effects: dict[str, tuple[float, float]] = {}
        for outcome in branch.competition_outcomes:
            channel, facility = competition_effects.get(outcome.loser_province_code, (0.0, 0.0))
            scaled = round(outcome.loss_index / 100, 4)
            competition_effects[outcome.loser_province_code] = (
                round(channel + (scaled if outcome.resource_type == "channel_slot" else 0), 4),
                round(facility + (scaled if outcome.resource_type == "facility_slot" else 0), 4),
            )
        settlement = ChinaPolicyEnv(
            profiles=self.profiles,
            automaker_profiles=self.automaker_profiles,
            policy=self._legacy_policy(branch.policy),
        ).settle_year(
            policy=self._legacy_policy(branch.policy),
            province_actions={
                code: self._legacy_province_action(action)
                for code, action in branch.province_final_actions.items()
            },
            automaker_actions={
                key: self._legacy_automaker_action(action)
                for key, action in branch.automaker_final_actions.items()
            },
            phase=Phase.Y2_Q4,
            event_scenario=legacy_event,
            event_responses=event_responses,
            coordination_matches=self._coordination_matches(branch),
            province_enterprise_effects=enterprise_effects,
            competition_effects=competition_effects,
        )
        branch.province_states = settlement.province_states
        branch.national_metrics = settlement.national_metrics
        totals: dict[str, float] = {}
        for contribution in settlement.mechanism_contributions.values():
            for term in contribution.terms:
                totals[term.name] = round(totals.get(term.name, 0) + term.contribution, 4)
        branch.mechanism_totals = totals
        branch.province_utilities = {
            code: self._province_utility(branch, code, competition_effects.get(code, (0.0, 0.0)))
            for code in MAINLAND_PROVINCE_CODES
        }
        if event and "consumer" in event.affected_subjects:
            effect = round(
                fmean(state.event_exposure_index for state in settlement.province_states.values())
                * (
                    0.12
                    if event.template_id == EventTemplateId.OIL_PRICE_RISE.value
                    else -0.08
                    if event.template_id == EventTemplateId.OIL_PRICE_FALL.value
                    else 0.05
                ),
                4,
            )
            branch.consumer_responses.append(
                ConsumerResponseRecord(
                    response_id=_stable_id(
                        "consumer_response", branch.branch_id, event.event_plan_id
                    ),
                    branch_id=branch.branch_id,
                    event_plan_id=event.event_plan_id,
                    affected_province_codes=list(MAINLAND_PROVINCE_CODES),
                    demand_effect_index=effect,
                    summary="消费者不作为 Agent；该记录由确定性环境根据事件暴露生成。",
                )
            )

    def _build_comparison(self, world: WorldStateV6) -> ComparisonResultV6:
        control = world.branches["control"]
        treatment = world.branches["treatment"]
        delta_gap = round(
            treatment.national_metrics.regional_development_gap
            - control.national_metrics.regional_development_gap,
            4,
        )
        gap_direction = (
            "narrowed" if delta_gap < -0.01 else "widened" if delta_gap > 0.01 else "unchanged"
        )
        metric_names = (
            "regional_development_gap",
            "central_fiscal_burden",
            "local_fiscal_pressure",
            "nev_demand",
            "new_investment_concentration",
            "industrial_agglomeration",
        )
        metrics = {
            name: MetricComparison(
                control=getattr(control.national_metrics, name),
                treatment=getattr(treatment.national_metrics, name),
                delta=round(
                    getattr(treatment.national_metrics, name)
                    - getattr(control.national_metrics, name),
                    4,
                ),
            )
            for name in metric_names
        }
        province_deltas = [
            ProvinceOutcomeDelta(
                province_code=code,
                province_name=policy_region_catalog()[code].short_name,
                development_delta=round(
                    treatment.province_states[code].development_index
                    - control.province_states[code].development_index,
                    4,
                ),
                demand_delta=round(
                    treatment.province_states[code].demand_index
                    - control.province_states[code].demand_index,
                    4,
                ),
                industry_delta=round(
                    treatment.province_states[code].industry_activity_index
                    - control.province_states[code].industry_activity_index,
                    4,
                ),
                fiscal_pressure_delta=round(
                    treatment.province_states[code].fiscal_pressure_index
                    - control.province_states[code].fiscal_pressure_index,
                    4,
                ),
            )
            for code in MAINLAND_PROVINCE_CODES
        ]
        automaker_deltas: list[AutomakerOutcomeDelta] = []
        for automaker_id in AUTOMAKER_IDS:
            left = control.automaker_final_actions[automaker_id]
            right = treatment.automaker_final_actions[automaker_id]
            left_map = {
                item.province_code: item.sales_investment_intensity
                for item in left.province_market_actions
            }
            right_map = {
                item.province_code: item.sales_investment_intensity
                for item in right.province_market_actions
            }
            changes = [abs(right_map[code] - left_map[code]) for code in MAINLAND_PROVINCE_CODES]
            automaker_deltas.append(
                AutomakerOutcomeDelta(
                    automaker_id=automaker_id,
                    display_name=automaker_catalog()[automaker_id].display_name,
                    changed_province_count=sum(value >= 0.005 for value in changes),
                    maximum_intensity_delta=round(max(changes), 4),
                    facility_changed=left.facility_actions != right.facility_actions,
                )
            )
        ranked = sorted(province_deltas, key=lambda item: item.development_delta, reverse=True)
        mechanism_deltas = {
            key: round(
                treatment.mechanism_totals.get(key, 0) - control.mechanism_totals.get(key, 0), 4
            )
            for key in set(control.mechanism_totals) | set(treatment.mechanism_totals)
        }
        top_mechanisms = sorted(
            mechanism_deltas, key=lambda key: abs(mechanism_deltas[key]), reverse=True
        )[:3]
        positive_key = max(
            mechanism_deltas,
            key=lambda key: (mechanism_deltas[key], abs(mechanism_deltas[key]), key),
        )
        cost_key = min(
            mechanism_deltas,
            key=lambda key: (mechanism_deltas[key], -abs(mechanism_deltas[key]), key),
        )
        risk_key = next(
            (
                key
                for key in (
                    "automaker_financial_constraint",
                    "local_fiscal_constraint",
                    "concentration_adjustment",
                )
                if key in mechanism_deltas
            ),
            top_mechanisms[-1],
        )
        strongest_province = max(
            MAINLAND_PROVINCE_CODES,
            key=lambda code: (
                sum(
                    abs(
                        getattr(treatment.province_final_actions[code].subsidy_mix, field)
                        - getattr(treatment.province_initial_actions[code].subsidy_mix, field)
                    )
                    for field in ("consumer", "fixed_cost", "variable_cost")
                ),
                code,
            ),
        )
        strongest_automaker = max(
            AUTOMAKER_IDS,
            key=lambda automaker_id: (
                sum(
                    abs(final.sales_investment_intensity - initial.sales_investment_intensity)
                    for initial, final in zip(
                        treatment.automaker_initial_actions[automaker_id].province_market_actions,
                        treatment.automaker_final_actions[automaker_id].province_market_actions,
                        strict=True,
                    )
                ),
                automaker_id,
            ),
        )
        strongest_record = max(
            treatment.coordination_records,
            key=lambda item: (
                item.status == "matched",
                item.contribution,
                len(item.evidence_refs),
                item.coordination_id,
            ),
        )
        province_action = treatment.province_final_actions[strongest_province]
        automaker_action = treatment.automaker_final_actions[strongest_automaker]

        def chain_nodes(mechanism_key: str, metric_label: str) -> list[MechanismNode]:
            nodes = [
                MechanismNode(
                    node_type="policy",
                    ref=f"policy:{treatment.policy.policy_id}",
                    label="干预方案政策输入",
                ),
                MechanismNode(
                    node_type="agent_action",
                    ref=f"action:{province_action.action_id}",
                    label=f"{policy_region_catalog()[strongest_province].short_name}省级最终行动",
                ),
            ]
            if strongest_record.status == "matched":
                nodes.append(
                    MechanismNode(
                        node_type="coordination_match",
                        ref=f"match:{strongest_record.coordination_id}",
                        label=(
                            f"{policy_region_catalog()[strongest_record.left_province_code].short_name}"
                            f"—{policy_region_catalog()[strongest_record.right_province_code].short_name}"
                            "自主合作生效"
                        ),
                        contribution=strongest_record.contribution,
                    )
                )
            nodes.extend(
                [
                    MechanismNode(
                        node_type="agent_action",
                        ref=f"action:{automaker_action.action_id}",
                        label=f"{automaker_catalog()[strongest_automaker].display_name}全国资源重新分配",
                    ),
                    MechanismNode(
                        node_type="environment",
                        ref=f"mechanism:{mechanism_key}",
                        label=MECHANISM_LABELS.get(mechanism_key, "其他确定性机制"),
                        contribution=mechanism_deltas[mechanism_key],
                    ),
                    MechanismNode(
                        node_type="metric",
                        ref=f"comparison:{world.experiment_id}",
                        label=metric_label,
                    ),
                ]
            )
            return nodes

        labels = {
            "narrowed": "干预方案下区域差距缩小",
            "widened": "干预方案下区域差距扩大",
            "unchanged": "两方案区域差距基本不变",
        }
        event_robustness = (
            "两分支承受同一冻结事件，差异来自政策。"
            if world.design and world.design.experiment_type is ExperimentType.POLICY_STRESS_TEST
            else "仅干预方案应用事件，差异来自事件。"
            if world.design and world.design.experiment_type is ExperimentType.EVENT_COUNTERFACTUAL
            else "本实验无事件，不作事件稳健性推断。"
        )
        same_policy = _policy_values(control.policy) == _policy_values(treatment.policy)
        same_event = bool(control.event_applied) == bool(treatment.event_applied)
        return ComparisonResultV6(
            experiment_id=world.experiment_id,
            experiment_type=world.design.experiment_type,
            control_branch_id=control.branch_id,
            treatment_branch_id=treatment.branch_id,
            conclusion=f"{labels[gap_direction]}，变化 {delta_gap:+.2f} 个模拟指数点。",
            gap_direction=gap_direction,
            delta_gap=delta_gap,
            national_metrics=metrics,
            province_deltas=province_deltas,
            automaker_deltas=automaker_deltas,
            top_beneficiaries=[item.province_name for item in ranked[:3]],
            top_pressured=[item.province_name for item in ranked[-3:]],
            fiscal_tradeoff=(
                f"中央财政负担 {metrics['central_fiscal_burden'].delta:+.2f} 点，"
                f"地方财政压力 {metrics['local_fiscal_pressure'].delta:+.2f} 点。"
            ),
            event_robustness=event_robustness,
            mechanism_chains=[
                MechanismChain(
                    category="positive",
                    title="主要正向机制",
                    nodes=chain_nodes(positive_key, "正向结果指标"),
                    contribution_delta=mechanism_deltas[positive_key],
                    evidence_refs=[
                        f"action:{province_action.action_id}",
                        f"action:{automaker_action.action_id}",
                        f"mechanism:{positive_key}",
                    ],
                ),
                MechanismChain(
                    category="cost",
                    title="主要代价机制",
                    nodes=chain_nodes(cost_key, "财政与集中度代价"),
                    contribution_delta=mechanism_deltas[cost_key],
                    evidence_refs=[
                        f"action:{province_action.action_id}",
                        f"action:{automaker_action.action_id}",
                        f"mechanism:{cost_key}",
                    ],
                ),
                MechanismChain(
                    category="reversal_risk",
                    title="结论反转风险",
                    nodes=chain_nodes(risk_key, "区域差距结论"),
                    contribution_delta=mechanism_deltas[risk_key],
                    evidence_refs=[
                        f"action:{province_action.action_id}",
                        f"action:{automaker_action.action_id}",
                        f"mechanism:{risk_key}",
                    ],
                ),
            ],
            sensitivity_findings=[
                SensitivityFinding(
                    input_group="省级支持强度输入",
                    direction="上调时需求与财政压力同时上升",
                    affected_metric="新能源汽车需求",
                    local_effect=0.12,
                ),
                SensitivityFinding(
                    input_group="车企现金流约束输入",
                    direction="约束加强时优先省份的明确投入决定下调",
                    affected_metric="产业集聚度",
                    local_effect=-0.08,
                ),
            ],
            active_difference="event" if same_policy else "policy",
            same_policy=same_policy,
            same_event=same_event,
            checkpoint_id=world.baseline.checkpoint_id,
            competition_loss_delta=round(
                sum(item.loss_index for item in treatment.competition_outcomes)
                - sum(item.loss_index for item in control.competition_outcomes),
                4,
            ),
            coordination_gain_delta=round(
                sum(
                    item.contribution
                    for item in treatment.coordination_records
                    if item.status == "matched"
                )
                - sum(
                    item.contribution
                    for item in control.coordination_records
                    if item.status == "matched"
                ),
                4,
            ),
            top_k_reallocation_count=sum(
                len(branch.top_k_reallocations) for branch in (control, treatment)
            ),
            counteroffer_acceptance_rate=round(
                sum(
                    item.decision == "accept"
                    for branch in (control, treatment)
                    for item in branch.province_counter_offer_responses
                )
                / max(
                    1,
                    sum(
                        len(branch.province_counter_offer_responses)
                        for branch in (control, treatment)
                    ),
                ),
                4,
            ),
        )

    async def _emit(
        self,
        runtime: V32Runtime,
        event_type: str,
        *,
        branch_id: str | None = None,
        round_name: SimulationRound | None = None,
        payload: dict[str, str | int | float | bool | None] | None = None,
    ) -> EventV6:
        runtime.event_counter += 1
        event = EventV6(
            event_id=f"evt_v32_{runtime.event_counter:08d}",
            type=event_type,
            experiment_id=runtime.world.experiment_id,
            branch_id=branch_id,
            journey_step=runtime.world.journey_step,
            round=round_name,
            payload=payload or {},
        )
        runtime.events.append(event)
        async with runtime.condition:
            runtime.condition.notify_all()
        return event

    async def _persist(self, runtime: V32Runtime) -> None:
        experiment_dir = self.runtime_dir / runtime.world.experiment_id
        world_payload = runtime.world.model_dump(mode="json")
        event_payloads = [event.model_dump(mode="json") for event in runtime.events]
        comparison_payload = (
            runtime.comparison.model_dump(mode="json") if runtime.comparison else None
        )
        snapshot_payload = {
            "schema_version": RUNTIME_SNAPSHOT_SCHEMA,
            "event_counter": runtime.event_counter,
            "world": world_payload,
            "events": event_payloads,
            "comparison": comparison_payload,
            "world_hash": canonical_hash(runtime.world),
            "replay_hash": canonical_hash(runtime.events),
            "comparison_hash": canonical_hash(runtime.comparison) if runtime.comparison else None,
        }
        world_text = json.dumps(world_payload, ensure_ascii=False, indent=2)
        replay_lines = [event.model_dump_json() for event in runtime.events]
        comparison_text = (
            json.dumps(comparison_payload, ensure_ascii=False, indent=2)
            if comparison_payload is not None
            else None
        )
        snapshot_text = json.dumps(snapshot_payload, ensure_ascii=False, indent=2)
        await asyncio.to_thread(
            self._persist_files,
            experiment_dir,
            world_text,
            replay_lines,
            comparison_text,
            snapshot_text,
        )

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        temporary_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        try:
            with temporary_path.open("w", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, path)
        finally:
            temporary_path.unlink(missing_ok=True)

    @classmethod
    def _persist_files(
        cls,
        experiment_dir: Path,
        world_text: str,
        replay_lines: list[str],
        comparison_text: str | None,
        snapshot_text: str,
    ) -> None:
        experiment_dir.mkdir(parents=True, exist_ok=True)
        # The snapshot is the atomic recovery truth. Compatibility mirrors may lag,
        # but can never move recovery ahead of this commit after a process crash.
        cls._atomic_write(experiment_dir / "runtime-snapshot.json", snapshot_text)
        cls._atomic_write(experiment_dir / "state.json", world_text)
        cls._append_replay(experiment_dir / "replay.jsonl", replay_lines)
        comparison_path = experiment_dir / "comparison.json"
        if comparison_text is not None:
            cls._atomic_write(comparison_path, comparison_text)
        elif comparison_path.exists():
            comparison_path.unlink()
        directory_fd = os.open(experiment_dir, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)

    @staticmethod
    def _append_replay(path: Path, replay_lines: list[str]) -> None:
        existing_lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
        if len(existing_lines) > len(replay_lines):
            raise ValueError("RUNTIME_REPLAY_AHEAD_OF_SNAPSHOT")
        for index, existing_line in enumerate(existing_lines):
            try:
                existing_event = EventV6.model_validate_json(existing_line)
                expected_event = EventV6.model_validate_json(replay_lines[index])
            except (ValueError, TypeError) as exc:
                raise ValueError("RUNTIME_REPLAY_MIRROR_INVALID") from exc
            if existing_event != expected_event:
                raise ValueError("RUNTIME_REPLAY_PREFIX_MISMATCH")
        missing_lines = replay_lines[len(existing_lines) :]
        if not missing_lines:
            return
        payload = ("\n".join(missing_lines) + "\n").encode("utf-8")
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            view = memoryview(payload)
            while view:
                written = os.write(descriptor, view)
                view = view[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def _cache_path(self, world: WorldStateV6) -> Path:
        return self.cache_dir / f"{world.versions['cache_key']}.json"

    def export_cache(self, experiment_id: str) -> Path:
        runtime = self._runtime(experiment_id)
        if runtime.comparison is None or runtime.world.status is not V32ExperimentStatus.COMPLETED:
            raise ValueError("only completed V3.2 experiments can be cached")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path = self._cache_path(runtime.world)
        payload = {
            "schema_version": "v32-m32-agent-cache-v1",
            "cache_key": runtime.world.versions["cache_key"],
            "versions": runtime.world.versions,
            "agent_provider": {
                "mode": self.agent_provider.run_mode,
                "province_model": self.agent_provider.model_name_for("province_proposal"),
                "automaker_model": self.agent_provider.model_name_for("automaker_final"),
                "invocation_count": sum(
                    len(branch.agent_invocations) for branch in runtime.world.branches.values()
                ),
                "fallback_count": sum(
                    item.fallback_used
                    for branch in runtime.world.branches.values()
                    for item in branch.agent_invocations
                ),
            },
            "branches": {
                key: branch.model_dump(mode="json")
                for key, branch in runtime.world.branches.items()
            },
            "comparison": runtime.comparison.model_dump(mode="json"),
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        return path

    def _restore_cache(self, runtime: V32Runtime) -> bool:
        path = self._cache_path(runtime.world)
        if not path.exists():
            return False
        payload = json.loads(path.read_text(encoding="utf-8"))
        if (
            payload.get("schema_version") != "v32-m32-agent-cache-v1"
            or payload.get("cache_key") != runtime.world.versions.get("cache_key")
            or payload.get("versions") != runtime.world.versions
        ):
            return False
        runtime.world.branches = {
            key: BranchRuntimeState.model_validate(value)
            for key, value in payload["branches"].items()
        }
        runtime.comparison = ComparisonResultV6.model_validate(payload["comparison"])
        runtime.comparison.experiment_id = runtime.world.experiment_id
        runtime.world.status = V32ExperimentStatus.COMPLETED
        runtime.world.journey_step = JourneyStep.RESULT_REVIEW
        return True

    async def get_state(self, experiment_id: str) -> WorldStateV6:
        return self._runtime(experiment_id).world.model_copy(deep=True)

    async def get_comparison(self, experiment_id: str) -> ComparisonResultV6:
        comparison = self._runtime(experiment_id).comparison
        if comparison is None:
            raise ValueError("comparison is not available before settlement")
        return comparison.model_copy(deep=True)

    async def get_strategy_market(self, experiment_id: str) -> StrategyMarketSnapshot:
        world = self._runtime(experiment_id).world
        return StrategyMarketSnapshot(
            experiment_id=experiment_id,
            branches={key: value.model_copy(deep=True) for key, value in world.branches.items()},
            automaker_signal_count=sum(
                len(action.province_signals)
                for branch in world.branches.values()
                for action in branch.automaker_initial_actions.values()
            ),
            proposal_count=sum(
                len(branch.province_coordination_proposals) for branch in world.branches.values()
            ),
            response_count=sum(
                len(branch.province_coordination_responses) for branch in world.branches.values()
            ),
            matched_count=sum(
                item.status == "matched"
                for branch in world.branches.values()
                for item in branch.coordination_records
            ),
            enterprise_offer_count=sum(
                len(branch.province_enterprise_offers) for branch in world.branches.values()
            ),
            enterprise_response_count=sum(
                len(branch.province_enterprise_offer_responses)
                for branch in world.branches.values()
            ),
            enterprise_matched_count=sum(
                item.status == "matched"
                for branch in world.branches.values()
                for item in branch.province_enterprise_matches
            ),
            competition_outcome_count=sum(
                len(branch.competition_outcomes) for branch in world.branches.values()
            ),
            counteroffer_count=sum(
                len(branch.automaker_counter_offers) for branch in world.branches.values()
            ),
            counteroffer_response_count=sum(
                len(branch.province_counter_offer_responses) for branch in world.branches.values()
            ),
            top_k_reallocation_count=sum(
                len(branch.top_k_reallocations) for branch in world.branches.values()
            ),
        )

    async def get_presentation_summary(self, experiment_id: str) -> PresentationSummary:
        runtime = self._runtime(experiment_id)
        if runtime.comparison is None:
            raise ValueError("presentation summary requires a completed comparison")
        candidates = [
            (branch, record)
            for branch in runtime.world.branches.values()
            for record in branch.coordination_records
        ]
        if not candidates:
            raise ValueError("presentation summary requires at least one coordination record")

        def presentation_score(
            item: tuple[BranchRuntimeState, CoordinationRecord],
        ) -> tuple[int, float, float, int, str]:
            candidate_branch, candidate_record = item
            candidate_proposal = next(
                proposal
                for proposal in candidate_branch.province_coordination_proposals
                if proposal.proposal_id == candidate_record.proposal_id
            )
            related_codes = {
                candidate_proposal.source_province_code,
                candidate_proposal.target_province_code,
            }
            province_change = sum(
                abs(
                    candidate_branch.province_final_actions[code].subsidy_mix.consumer
                    - candidate_branch.province_initial_actions[code].subsidy_mix.consumer
                )
                + abs(
                    candidate_branch.province_final_actions[code].subsidy_mix.fixed_cost
                    - candidate_branch.province_initial_actions[code].subsidy_mix.fixed_cost
                )
                + abs(
                    candidate_branch.province_final_actions[code].subsidy_mix.variable_cost
                    - candidate_branch.province_initial_actions[code].subsidy_mix.variable_cost
                )
                for code in related_codes
            )
            automaker_change = max(
                (
                    abs(
                        final_item.sales_investment_intensity
                        - initial_by_code[final_item.province_code]
                    )
                    for automaker_id in AUTOMAKER_IDS
                    for initial_by_code in [
                        {
                            market.province_code: market.sales_investment_intensity
                            for market in candidate_branch.automaker_initial_actions[
                                automaker_id
                            ].province_market_actions
                        }
                    ]
                    for final_item in candidate_branch.automaker_final_actions[
                        automaker_id
                    ].province_market_actions
                    if final_item.province_code in related_codes
                ),
                default=0.0,
            )
            complete = int(candidate_record.status == "matched")
            return (
                complete,
                province_change + automaker_change,
                abs(candidate_record.contribution),
                len(candidate_record.evidence_refs),
                candidate_record.coordination_id,
            )

        branch, record = max(
            candidates,
            key=presentation_score,
        )
        proposal = next(
            item
            for item in branch.province_coordination_proposals
            if item.proposal_id == record.proposal_id
        )
        response = next(
            (
                item
                for item in branch.province_coordination_responses
                if item.response_id == record.response_id
            ),
            None,
        )
        source_name = policy_region_catalog()[proposal.source_province_code].short_name
        target_name = policy_region_catalog()[proposal.target_province_code].short_name
        source_signals = self._enterprise_signals(branch, proposal.source_province_code)
        strongest_signal = max(source_signals, key=lambda item: item.investment_inclination)
        largest_shift: tuple[str, float, str] | None = None
        related_codes = {
            proposal.source_province_code,
            proposal.target_province_code,
        }
        for automaker_id in AUTOMAKER_IDS:
            before = {
                item.province_code: item.sales_investment_intensity
                for item in branch.automaker_initial_actions[automaker_id].province_market_actions
            }
            for item in branch.automaker_final_actions[automaker_id].province_market_actions:
                if item.province_code not in related_codes:
                    continue
                delta = item.sales_investment_intensity - before[item.province_code]
                candidate = (automaker_id, abs(delta), item.province_code)
                if largest_shift is None or candidate[1:] > largest_shift[1:]:
                    largest_shift = candidate
        if largest_shift is None or largest_shift[1] <= 1e-9:
            for automaker_id in AUTOMAKER_IDS:
                before = {
                    item.province_code: item.sales_investment_intensity
                    for item in branch.automaker_initial_actions[
                        automaker_id
                    ].province_market_actions
                }
                for item in branch.automaker_final_actions[automaker_id].province_market_actions:
                    delta = item.sales_investment_intensity - before[item.province_code]
                    candidate = (automaker_id, abs(delta), item.province_code)
                    if largest_shift is None or candidate[1:] > largest_shift[1:]:
                        largest_shift = candidate
        assert largest_shift is not None
        automaker_id, _, shifted_code = largest_shift
        final_action = branch.automaker_final_actions[automaker_id]
        before_action = branch.automaker_initial_actions[automaker_id]
        before_value = next(
            item.sales_investment_intensity
            for item in before_action.province_market_actions
            if item.province_code == shifted_code
        )
        after_value = next(
            item.sales_investment_intensity
            for item in final_action.province_market_actions
            if item.province_code == shifted_code
        )
        result_word = "匹配" if record.status == "matched" else "未匹配"
        response_word = "接受" if response and response.decision == "accept" else "拒绝或未响应"
        signal_decision_label = {
            "expand": "扩大投入",
            "maintain": "维持投入",
            "reduce": "收缩投入",
        }[strongest_signal.decision]
        return PresentationSummary(
            experiment_id=experiment_id,
            scenes=[
                PresentationScene(
                    scene="policy_input",
                    title="政策输入形成双分支",
                    summary=(
                        f"原始方案与干预方案从同一基线派生；当前展示{branch.label}的自主互动链。"
                    ),
                    evidence_refs=[f"policy:{branch.policy.policy_id}"],
                ),
                PresentationScene(
                    scene="enterprise_feedback",
                    title=f"{automaker_catalog()[strongest_signal.automaker_id].display_name}反馈进入省级判断",
                    summary=(
                        f"该车企对{source_name}作出“{signal_decision_label}”的明确市场决定，"
                        f"投入倾向{strongest_signal.investment_inclination:.2f}。"
                    ),
                    evidence_refs=[
                        f"action:{strongest_signal.action_id}",
                        *strongest_signal.evidence_refs[:2],
                    ],
                ),
                PresentationScene(
                    scene="province_coordination",
                    title=f"{source_name}向{target_name}自主提出合作",
                    summary=(
                        f"合作依据为{proposal.public_reason}；对方{response_word}，最终{result_word}。"
                    ),
                    evidence_refs=[
                        f"proposal:{proposal.proposal_id}",
                        *([f"response:{response.response_id}"] if response else []),
                        f"match:{record.coordination_id}",
                    ],
                ),
                PresentationScene(
                    scene="resource_reallocation",
                    title=f"{automaker_catalog()[automaker_id].display_name}重新分配全国资源",
                    summary=(
                        f"{policy_region_catalog()[shifted_code].short_name}投入强度由"
                        f"{before_value:.3f}调整至{after_value:.3f}，并保留对应机会成本。"
                    ),
                    evidence_refs=[
                        f"match:{record.coordination_id}",
                        f"action:{before_action.action_id}",
                        f"action:{final_action.action_id}",
                    ],
                ),
                PresentationScene(
                    scene="policy_conclusion",
                    title="环境结算形成政策结论",
                    summary=runtime.comparison.conclusion,
                    evidence_refs=[f"comparison:{experiment_id}"],
                ),
            ],
        )

    async def get_presentation_timeline(self, experiment_id: str) -> PresentationTimeline:
        runtime = self._runtime(experiment_id)
        return PresentationProjectionService(
            runtime.world,
            runtime.events,
            runtime.comparison,
        ).build_timeline()

    async def get_presentation_frame(self, experiment_id: str, frame_id: str) -> PresentationFrame:
        runtime = self._runtime(experiment_id)
        return PresentationProjectionService(
            runtime.world,
            runtime.events,
            runtime.comparison,
        ).get_frame(frame_id)

    async def get_decision_traces(
        self,
        experiment_id: str,
        *,
        branch_id: str | None = None,
        agent_id: str | None = None,
        round_name: SimulationRound | None = None,
    ) -> list[DecisionTrace]:
        world = self._runtime(experiment_id).world
        branches = [world.branches[branch_id]] if branch_id else world.branches.values()
        traces = [trace for branch in branches for trace in branch.decision_traces]
        if agent_id:
            traces = [trace for trace in traces if trace.agent_id == agent_id]
        if round_name:
            traces = [trace for trace in traces if trace.round is round_name]
        return [trace.model_copy(deep=True) for trace in traces]

    async def get_province_detail(
        self, experiment_id: str, province_code: str
    ) -> dict[str, object]:
        if province_code not in self.profiles:
            raise KeyError(f"province not found: {province_code}")
        world = self._runtime(experiment_id).world
        persona = self.personas[province_code]
        persona_payload = persona.model_dump(mode="json")
        persona_payload["summary"] = (
            f"{self.profiles[province_code].short_name}本次实验画像更侧重"
            f"{PERSONA_TYPE_LABELS[persona.primary_type.value]}，主要约束为"
            f"{'、'.join(CONSTRAINT_LABELS[item.value] for item in persona.key_constraints)}。"
        )
        return {
            "schema_version": "province-agent-detail-v5",
            "experiment_id": experiment_id,
            "province_code": province_code,
            "profile": self.profiles[province_code].model_dump(mode="json"),
            "m29_profile": self.m29.province_profiles[province_code].model_dump(mode="json"),
            "persona": persona_payload,
            "data_quality": V32DataQuality.PROXY.value,
            "data_quality_label": "代理数据基线",
            "relations": {
                relation_type: [
                    item.model_dump(mode="json")
                    for item in self._relations(province_code, relation_type)
                ]
                for relation_type in ("observation", "competition", "coordination")
            },
            "branches": {
                key: {
                    "resource_envelope": branch.province_resource_envelopes.get(
                        province_code
                    ).model_dump(mode="json")
                    if province_code in branch.province_resource_envelopes
                    else None,
                    "initial_action": branch.province_initial_actions.get(province_code).model_dump(
                        mode="json"
                    )
                    if province_code in branch.province_initial_actions
                    else None,
                    "final_action": branch.province_final_actions.get(province_code).model_dump(
                        mode="json"
                    )
                    if province_code in branch.province_final_actions
                    else None,
                    "state": branch.province_states.get(province_code).model_dump(mode="json")
                    if province_code in branch.province_states
                    else None,
                    "decision_traces": [
                        trace.model_dump(mode="json")
                        for trace in branch.decision_traces
                        if trace.agent_id == province_code
                    ],
                    "coordination_records": [
                        item.model_dump(mode="json")
                        for item in branch.coordination_records
                        if province_code in {item.left_province_code, item.right_province_code}
                    ],
                    "coordination_proposals": [
                        item.model_dump(mode="json")
                        for item in branch.province_coordination_proposals
                        if province_code in {item.source_province_code, item.target_province_code}
                    ],
                    "coordination_responses": [
                        item.model_dump(mode="json")
                        for item in branch.province_coordination_responses
                        if item.responding_province_code == province_code
                    ],
                    "enterprise_offers": [
                        item.model_dump(mode="json")
                        for item in branch.province_enterprise_offers
                        if item.source_province_code == province_code
                    ],
                    "enterprise_offer_responses": [
                        item.model_dump(mode="json")
                        for item in branch.province_enterprise_offer_responses
                        if any(
                            offer.offer_id == item.offer_id
                            and offer.source_province_code == province_code
                            for offer in branch.province_enterprise_offers
                        )
                    ],
                    "competition_outcomes": [
                        item.model_dump(mode="json")
                        for item in branch.competition_outcomes
                        if item.loser_province_code == province_code
                        or item.winner_province_code == province_code
                    ],
                    "utility": branch.province_utilities.get(province_code).model_dump(mode="json")
                    if province_code in branch.province_utilities
                    else None,
                    "counter_offers": [
                        item.model_dump(mode="json")
                        for item in branch.automaker_counter_offers
                        if item.province_code == province_code
                    ],
                    "counter_offer_responses": [
                        item.model_dump(mode="json")
                        for item in branch.province_counter_offer_responses
                        if item.province_code == province_code
                    ],
                    "enterprise_matches": [
                        item.model_dump(mode="json")
                        for item in branch.province_enterprise_matches
                        if item.province_code == province_code
                    ],
                }
                for key, branch in world.branches.items()
            },
        }

    async def get_automaker_detail(
        self, experiment_id: str, automaker_id: str
    ) -> dict[str, object]:
        if automaker_id not in self.automaker_profiles:
            raise KeyError(f"automaker not found: {automaker_id}")
        world = self._runtime(experiment_id).world
        return {
            "schema_version": "automaker-detail-v4",
            "experiment_id": experiment_id,
            "automaker_id": automaker_id,
            "profile": self.automaker_profiles[automaker_id].model_dump(mode="json"),
            "m29_profile": self.m29.automaker_profiles[automaker_id].model_dump(mode="json"),
            "simulation_persona": self.automaker_personas[automaker_id].model_dump(mode="json"),
            "data_quality": V32DataQuality.PROXY.value,
            "data_quality_label": "代理数据基线",
            "branches": {
                key: {
                    "resource_envelope": branch.automaker_resource_envelopes.get(
                        automaker_id
                    ).model_dump(mode="json")
                    if automaker_id in branch.automaker_resource_envelopes
                    else None,
                    "initial_action": branch.automaker_initial_actions.get(automaker_id).model_dump(
                        mode="json"
                    )
                    if automaker_id in branch.automaker_initial_actions
                    else None,
                    "negotiation_action": branch.automaker_negotiation_actions.get(
                        automaker_id
                    ).model_dump(mode="json")
                    if automaker_id in branch.automaker_negotiation_actions
                    else None,
                    "final_action": branch.automaker_final_actions.get(automaker_id).model_dump(
                        mode="json"
                    )
                    if automaker_id in branch.automaker_final_actions
                    else None,
                    "decision_traces": [
                        trace.model_dump(mode="json")
                        for trace in branch.decision_traces
                        if trace.agent_id == automaker_id
                    ],
                    "enterprise_offers": [
                        item.model_dump(mode="json")
                        for item in branch.province_enterprise_offers
                        if item.target_automaker_id == automaker_id
                    ],
                    "enterprise_matches": [
                        item.model_dump(mode="json")
                        for item in branch.province_enterprise_matches
                        if item.automaker_id == automaker_id
                    ],
                    "competition_outcomes": [
                        item.model_dump(mode="json")
                        for item in branch.competition_outcomes
                        if item.automaker_id == automaker_id
                    ],
                    "counter_offers": [
                        item.model_dump(mode="json")
                        for item in branch.automaker_counter_offers
                        if item.automaker_id == automaker_id
                    ],
                    "counter_offer_responses": [
                        item.model_dump(mode="json")
                        for item in branch.province_counter_offer_responses
                        if item.counter_offer_id
                        in {
                            offer.counter_offer_id
                            for offer in branch.automaker_counter_offers
                            if offer.automaker_id == automaker_id
                        }
                    ],
                }
                for key, branch in world.branches.items()
            },
            "disclaimer": "数据来源与推算方法可在证据详情查看；模拟行动不代表真实企业承诺。",
        }

    async def get_events(
        self, experiment_id: str, *, after_event_id: str | None = None
    ) -> list[EventV6]:
        events = self._runtime(experiment_id).events
        if after_event_id:
            try:
                index = next(
                    index for index, event in enumerate(events) if event.event_id == after_event_id
                )
                events = events[index + 1 :]
            except StopIteration:
                pass
        return [event.model_copy(deep=True) for event in events]

    async def wait_for_events(
        self, experiment_id: str, after_event_id: str | None, timeout_seconds: float = 15
    ) -> list[EventV6]:
        runtime = self._runtime(experiment_id)
        existing = await self.get_events(experiment_id, after_event_id=after_event_id)
        if existing:
            return existing
        try:
            async with asyncio.timeout(timeout_seconds):
                async with runtime.condition:
                    await runtime.condition.wait()
        except TimeoutError:
            return []
        return await self.get_events(experiment_id, after_event_id=after_event_id)

    async def get_replay(self, experiment_id: str) -> list[dict[str, object]]:
        return [
            json.loads(event.model_dump_json()) for event in self._runtime(experiment_id).events
        ]

    async def get_audit(self, experiment_id: str, *, limit: int = 100) -> dict[str, object]:
        world = self._runtime(experiment_id).world
        records: list[dict[str, object]] = []
        sequence = 0
        for branch in world.branches.values():
            for trace in branch.decision_traces:
                sequence += 1
                records.append(
                    {
                        "schema_version": "audit-record-v1",
                        "record_id": f"audit_{trace.trace_id}",
                        "sequence": sequence,
                        "experiment_id": experiment_id,
                        "branch_id": branch.branch_id,
                        "round": trace.round.value,
                        "record_hash": canonical_hash(trace),
                        "payload": {
                            "record_type": "agent_invocation",
                            "actor_kind": trace.trace_type,
                            "actor_id": trace.agent_id,
                            "operation": trace.round.value,
                            "outcome": "succeeded",
                            "output_ids": [trace.final_action_id],
                            "decision_trace_id": trace.trace_id,
                        },
                    }
                )
            for invocation in branch.agent_invocations:
                sequence += 1
                records.append(
                    {
                        "schema_version": "audit-record-v1",
                        "record_id": f"audit_{invocation.invocation_id}",
                        "sequence": sequence,
                        "experiment_id": experiment_id,
                        "branch_id": branch.branch_id,
                        "round": None,
                        "record_hash": canonical_hash(invocation),
                        "payload": {
                            "record_type": "agent_provider_call",
                            "actor_kind": invocation.kind,
                            "actor_id": invocation.agent_id,
                            "operation": invocation.kind,
                            "outcome": "fallback" if invocation.fallback_used else "succeeded",
                            "output_ids": [invocation.output_hash],
                            "model": invocation.model,
                            "input_hash": invocation.input_hash,
                        },
                    }
                )
        visible = records[:limit]
        return {
            "records": visible,
            "next_sequence": len(visible) if len(records) > len(visible) else None,
        }

    async def get_evidence(self, experiment_id: str, evidence_id: str) -> dict[str, object]:
        runtime = self._runtime(experiment_id)
        world = runtime.world
        prefix, _, object_id = evidence_id.partition(":")
        if prefix in {"fact", "feature", "relation", "source"}:
            return self.m29.evidence(prefix, object_id)
        if prefix == "policy":
            if world.interpretation.executable_policy.policy_id == object_id:
                return {
                    "type": "policy",
                    "record": world.interpretation.executable_policy.model_dump(mode="json"),
                }
            for branch in world.branches.values():
                if branch.policy.policy_id == object_id:
                    return {
                        "type": "policy",
                        "record": branch.policy.model_dump(mode="json"),
                    }
        if prefix == "checkpoint" and world.baseline:
            return {
                "type": "baseline_snapshot",
                "record": world.baseline.model_dump(mode="json"),
            }
        if prefix == "comparison" and runtime.comparison:
            return {
                "type": "comparison",
                "record": runtime.comparison.model_dump(mode="json"),
            }
        if prefix in {"action", "automaker", "trace", "topk"}:
            for branch in world.branches.values():
                actions = [
                    *branch.province_initial_actions.values(),
                    *branch.province_final_actions.values(),
                    *branch.automaker_initial_actions.values(),
                    *branch.automaker_negotiation_actions.values(),
                    *branch.automaker_final_actions.values(),
                ]
                for action in actions:
                    if (
                        action.action_id == object_id
                        or getattr(action, "automaker_id", None) == object_id
                    ):
                        return {
                            "type": "action",
                            "record": action.model_dump(mode="json"),
                        }
        if prefix in {
            "proposal",
            "response",
            "match",
            "offer",
            "offer-response",
            "resource",
            "invocation",
            "competition",
            "utility",
            "counteroffer",
            "counterresponse",
        }:
            for branch in world.branches.values():
                objects: list[BaseModel] = [
                    *branch.province_coordination_proposals,
                    *branch.province_coordination_responses,
                    *branch.coordination_records,
                    *branch.province_enterprise_offers,
                    *branch.province_enterprise_offer_responses,
                    *branch.province_enterprise_matches,
                    *branch.competition_outcomes,
                    *branch.province_utilities.values(),
                    *branch.automaker_counter_offers,
                    *branch.province_counter_offer_responses,
                    *branch.province_resource_envelopes.values(),
                    *branch.automaker_resource_envelopes.values(),
                    *branch.agent_invocations,
                ]
                for item in objects:
                    identifiers = {
                        getattr(item, field, None)
                        for field in (
                            "proposal_id",
                            "response_id",
                            "coordination_id",
                            "offer_id",
                            "counter_offer_id",
                            "outcome_id",
                            "match_id",
                            "utility_id",
                            "envelope_id",
                            "invocation_id",
                        )
                    }
                    if object_id in identifiers:
                        return {
                            "type": prefix,
                            "record": item.model_dump(mode="json"),
                        }
                for trace in branch.decision_traces:
                    if trace.trace_id == object_id:
                        return {
                            "type": "decision_trace",
                            "record": trace.model_dump(mode="json"),
                        }
        if prefix == "mechanism":
            return {
                "type": "mechanism",
                "mechanism_code": object_id,
                "display_name": MECHANISM_LABELS.get(object_id, "其他确定性机制"),
                "branch_totals": {
                    key: branch.mechanism_totals.get(object_id, 0)
                    for key, branch in world.branches.items()
                },
            }
        raise KeyError(f"evidence not found: {evidence_id}")
