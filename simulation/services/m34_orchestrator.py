from __future__ import annotations

import asyncio
import json
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypeVar
from uuid import uuid4

from pydantic import BaseModel

from simulation.adapters.asyncio_adapter import AsyncioSimulationAdapter
from simulation.catalog import automaker_catalog
from simulation.domain_constants import AUTOMAKER_IDS, MAINLAND_PROVINCE_CODES
from simulation.envs.quarterly_policy_env import settle_quarter
from simulation.llm.m34_provider import M34AgentProvider, build_m34_agent_provider
from simulation.m29_data import M29Snapshot, load_m29_personas, load_m29_snapshot
from simulation.models.automaker import FacilityAction, ProvinceMarketAction
from simulation.models.common import BranchKind, ChannelStrategy, FacilityActionKind
from simulation.models.m34 import (
    TERMINAL_TRANSACTION_STATES,
    AgentKindM34,
    AgentTickDecision,
    AuthorizedInbox,
    AutomakerQuarterAction,
    BaselineSnapshotV3,
    BranchRuntimeStateV9,
    ComparisonResultV10,
    EngagementMode,
    EventPlanV2,
    EventV10,
    ExperimentDesignV2,
    InteractionMarket,
    InteractionMessage,
    InteractionSession,
    InteractionWave,
    MacroTick,
    MessageKind,
    MessageVisibility,
    MetricComparisonV10,
    ProvinceQuarterAction,
    QualityCountM34,
    ReconsiderationCondition,
    TickCheckpoint,
    TransactionState,
    WorldStateV10,
)
from simulation.models.province import SubsidyMix
from simulation.models.v32 import (
    AgentInvocationRecord,
    AutomakerResourceEnvelope,
    AutomakerSimulationPersona,
    ExperimentType,
    JourneyStep,
    PolicyInterpretation,
    PolicyV4,
    ProvinceRelation,
    ProvinceRelationNetwork,
    ProvinceResourceEnvelope,
    V32DataQuality,
    V32ExperimentStatus,
)
from simulation.services.m34_presentation import M34PresentationProjection
from simulation.services.replay import canonical_hash

ModelT = TypeVar("ModelT", bound=BaseModel)
EXPERIMENT_ID_PATTERN = re.compile(r"exp_m34_[0-9a-f]{12}\Z")
EVENT_ID_PATTERN = re.compile(r"evt_m34_(\d{8})\Z")
RUNTIME_SNAPSHOT_SCHEMA = "runtime-snapshot-v2"
MAX_CALLS_PER_TICK = 180
MAX_MESSAGES_PER_TICK = 500
MAX_CONDITION_ROUNDS_PER_PAIR = 2


def _stable_id(prefix: str, *parts: object) -> str:
    return f"{prefix}_{canonical_hash(parts)[:16]}"


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return round(max(minimum, min(maximum, value)), 6)


def _normalize_mix(consumer: float, fixed: float, variable: float) -> SubsidyMix:
    values = [max(0.001, consumer), max(0.001, fixed), max(0.001, variable)]
    total = sum(values)
    normalized = [round(item / total, 6) for item in values]
    normalized[-1] = round(1 - normalized[0] - normalized[1], 6)
    return SubsidyMix(consumer=normalized[0], fixed_cost=normalized[1], variable_cost=normalized[2])


@dataclass
class M34Runtime:
    world: WorldStateV10
    events: list[EventV10] = field(default_factory=list)
    comparison: ComparisonResultV10 | None = None
    event_counter: int = 0
    logical_sequence: int = 0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    condition: asyncio.Condition = field(default_factory=asyncio.Condition)


class M34Orchestrator:
    """Quarterly event-driven domain orchestrator with branch and wave barriers."""

    def __init__(
        self,
        legacy: AsyncioSimulationAdapter,
        *,
        runtime_dir: Path | str = Path("runtime/m34"),
        cache_dir: Path | str = Path("runtime/cache/v3_2_m34_luna"),
        cache_enabled: bool = False,
        agent_provider: M34AgentProvider | None = None,
    ) -> None:
        self.m29: M29Snapshot = load_m29_snapshot()
        self.profiles = self.m29.mechanism_province_profiles
        self.automaker_profiles = self.m29.mechanism_automaker_profiles
        self.personas = load_m29_personas(self.m29)
        self.default_policy = legacy.default_policy
        self.runtime_dir = Path(runtime_dir)
        self.cache_dir = Path(cache_dir)
        self.cache_enabled = cache_enabled
        self.agent_provider = agent_provider or build_m34_agent_provider(
            legacy.provider, self.cache_dir
        )
        self.runtimes: dict[str, M34Runtime] = {}
        self.relation_network = self._build_relation_network()
        self.automaker_personas = self._build_automaker_personas()

    def _build_relation_network(self) -> ProvinceRelationNetwork:
        relations: list[ProvinceRelation] = []
        for edge in self.m29.relation_network.edges:
            if edge.relation_type not in {"observation", "competition", "coordination"}:
                continue
            relations.append(
                ProvinceRelation(
                    source_code=edge.source_code,
                    target_code=edge.target_code,
                    relation_type=edge.relation_type,
                    weight=edge.weight,
                    evidence_refs=[f"relation:{edge.edge_id}"],
                )
            )
        return ProvinceRelationNetwork(relations=relations)

    def _build_automaker_personas(self) -> dict[str, AutomakerSimulationPersona]:
        result: dict[str, AutomakerSimulationPersona] = {}
        for index, automaker_id in enumerate(AUTOMAKER_IDS):
            profile = self.automaker_profiles[automaker_id]
            result[automaker_id] = AutomakerSimulationPersona(
                automaker_id=automaker_id,
                primary_price_band=("mass_market", "mainstream", "premium")[index % 3],
                technology_focus=("规模渠道", "智能化", "供应链效率")[index % 3],
                growth_goal=_clamp(0.45 + 0.35 * profile.sales_growth_index),
                cashflow_constraint=_clamp(1 - profile.liquidity_index),
                capacity_pressure=_clamp(profile.capacity_utilization_index),
                channel_expansion_tendency=_clamp(0.35 + 0.45 * profile.sales_growth_index),
                rd_investment_tendency=_clamp(0.45 + 0.03 * index),
                intelligent_driving_stage=_clamp(0.4 + 0.04 * index),
                new_capacity_willingness=_clamp(0.35 + 0.35 * profile.liquidity_index),
                subsidy_sensitivity=_clamp(0.4 + 0.03 * (index % 5)),
                market_sensitivity=_clamp(0.55 + 0.02 * (index % 4)),
                supply_chain_sensitivity=_clamp(0.5 + 0.025 * (index % 5)),
                regulation_sensitivity=_clamp(0.4 + 0.03 * (index % 4)),
                summary=f"{automaker_catalog()[automaker_id].display_name}模拟主体使用冻结代理画像。",
            )
        return result

    @staticmethod
    def _parse_share(text: str, name: str, default: float) -> float:
        match = re.search(rf"{name}[^0-9]{{0,12}}(100|\d{{1,2}}(?:\.\d+)?)\s*%", text)
        return _clamp(float(match.group(1)) / 100) if match else default

    def interpret_policy(self, source_text: str) -> PolicyInterpretation:
        source = source_text.strip()
        west = self._parse_share(source, "西部", 0.95)
        central = self._parse_share(source, "中部", 0.90)
        east = self._parse_share(source, "东部", 0.85)
        policy = PolicyV4(
            policy_id=_stable_id("policy", source, west, central, east),
            west_central_share=west,
            central_central_share=central,
            east_central_share=east,
        )
        return PolicyInterpretation(
            interpretation_id=_stable_id("interpretation", source),
            source_text=source,
            policy_goals=["比较中央承担比例的区域、财政与产业影响"],
            target_subjects=["31 个省级模拟主体", "10 家车企模拟主体"],
            policy_tools=["西部中央承担比例", "中部中央承担比例", "东部中央承担比例"],
            executable_policy=policy,
            execution_period="一个模拟年度（Q1–Q4 与季度内逻辑互动）",
            core_constraints=["结果由确定性环境计算", "模拟季度不代表现实响应日期"],
            ambiguities=[] if "%" in source else ["未给出完整比例，使用 2025 年参考基线。"],
            unmodeled_clauses=[],
            event_design_hints=["可在实验设计时冻结 0–3 个外生事件"],
            recommended_metrics=[
                "区域发展差距",
                "中央财政负担",
                "地方财政压力",
                "新能源汽车需求",
                "新增投资集中度",
                "产业集聚度",
            ],
            public_summary=(
                f"西部 {west:.0%}、中部 {central:.0%}、东部 {east:.0%}；"
                "按 Q1–Q4 运行并在 Q4 完成同源比较。"
            ),
        )

    async def create_experiment(
        self,
        policy_text: str,
        *,
        seed: int = 20260812,
        experiment_id: str | None = None,
    ) -> WorldStateV10:
        experiment_id = experiment_id or f"exp_m34_{uuid4().hex[:12]}"
        if not EXPERIMENT_ID_PATTERN.fullmatch(experiment_id):
            raise ValueError("EXPERIMENT_ID_INVALID")
        interpretation = self.interpret_policy(policy_text)
        if self.has_experiment(experiment_id):
            world = self.runtimes[experiment_id].world
            if (
                world.interpretation.source_text == interpretation.source_text
                and world.seed == seed
            ):
                return world.model_copy(deep=True)
            raise ValueError("EXPERIMENT_ID_CONFLICT")
        world = WorldStateV10(
            experiment_id=experiment_id,
            journey_step=JourneyStep.CENTRAL_INTERPRETATION,
            status=V32ExperimentStatus.AWAITING_INTERPRETATION_CONFIRMATION,
            interpretation=interpretation,
            seed=seed,
            central_call_count=1,
        )
        world.versions.update(
            {
                "province_agent_model": self.agent_provider.model_name_for("province_tick"),
                "automaker_agent_model": self.agent_provider.model_name_for("automaker_tick"),
                "agent_provider_mode": self.agent_provider.run_mode,
            }
        )
        runtime = M34Runtime(world=world)
        self.runtimes[experiment_id] = runtime
        await self._emit(runtime, "interpretation.generated")
        await self._persist(runtime)
        return world.model_copy(deep=True)

    async def confirm_interpretation(
        self, experiment_id: str, interpretation: PolicyInterpretation
    ) -> WorldStateV10:
        runtime = self._runtime(experiment_id)
        async with runtime.lock:
            confirmed = interpretation.model_copy(update={"status": "confirmed"})
            if runtime.world.status is not V32ExperimentStatus.AWAITING_INTERPRETATION_CONFIRMATION:
                if runtime.world.interpretation == confirmed:
                    return runtime.world.model_copy(deep=True)
                raise ValueError("interpretation cannot be changed after confirmation")
            if interpretation.interpretation_id != runtime.world.interpretation.interpretation_id:
                raise ValueError("INTERPRETATION_ID_MISMATCH")
            runtime.world.interpretation = confirmed
            runtime.world.journey_step = JourneyStep.EXPERIMENT_DESIGN
            runtime.world.status = V32ExperimentStatus.AWAITING_DESIGN_CONFIRMATION
            await self._emit(runtime, "interpretation.confirmed")
            await self._persist(runtime)
            return runtime.world.model_copy(deep=True)

    async def confirm_design(self, experiment_id: str, design: ExperimentDesignV2) -> WorldStateV10:
        runtime = self._runtime(experiment_id)
        async with runtime.lock:
            if runtime.world.status is not V32ExperimentStatus.AWAITING_DESIGN_CONFIRMATION:
                if runtime.world.design == design:
                    return runtime.world.model_copy(deep=True)
                raise ValueError("design cannot be changed in the current status")
            runtime.world.design = design
            runtime.world.journey_step = JourneyStep.BASELINE_CONFIRMATION
            runtime.world.status = V32ExperimentStatus.AWAITING_BASELINE_CONFIRMATION
            await self._emit(runtime, "design.confirmed")
            await self._persist(runtime)
            return runtime.world.model_copy(deep=True)

    async def confirm_baseline(
        self, experiment_id: str, *, expected_data_version: str | None = None
    ) -> WorldStateV10:
        runtime = self._runtime(experiment_id)
        async with runtime.lock:
            if runtime.world.status is not V32ExperimentStatus.AWAITING_BASELINE_CONFIRMATION:
                if runtime.world.baseline is not None:
                    return runtime.world.model_copy(deep=True)
                raise ValueError("baseline cannot be confirmed in the current status")
            if runtime.world.design is None:
                raise ValueError("experiment design is required")
            if expected_data_version and expected_data_version != self.m29.manifest.data_version:
                raise ValueError("BASELINE_DATA_VERSION_MISMATCH")
            state_hash = canonical_hash(
                {
                    "profiles": self.profiles,
                    "automakers": self.automaker_profiles,
                    "personas": self.personas,
                    "relations": self.relation_network,
                    "design": runtime.world.design,
                    "seed": runtime.world.seed,
                }
            )
            checkpoint_id = f"baseline_m34_{state_hash[:16]}"
            runtime.world.baseline = BaselineSnapshotV3(
                checkpoint_id=checkpoint_id,
                state_hash=state_hash,
                quality_counts=[
                    QualityCountM34(
                        quality=V32DataQuality.VERIFIED,
                        field_count=self.m29.manifest.quality_counts.get("trusted", 0),
                        explanation="M29 冻结事实与可反算派生层。",
                    )
                ],
                missing_value_policy=self.m29.manifest.missing_value_policy,
                uncovered_content=runtime.world.interpretation.unmodeled_clauses,
                data_version=self.m29.manifest.data_version,
                relation_network_version=self.m29.relation_network.schema_version,
            )
            runtime.world.relation_network = self.relation_network
            runtime.world.automaker_personas = self.automaker_personas
            runtime.world.branches = {
                role: self._branch(role, checkpoint_id, policy)
                for role, policy in (
                    ("control", runtime.world.design.control_policy),
                    ("treatment", runtime.world.design.treatment_policy),
                )
            }
            runtime.world.journey_step = JourneyStep.SIMULATION_RUN
            runtime.world.status = V32ExperimentStatus.READY
            runtime.world.versions["cache_key"] = canonical_hash(
                {
                    "interpretation": runtime.world.interpretation,
                    "design": runtime.world.design,
                    "baseline": state_hash,
                    "versions": runtime.world.versions,
                    "seed": runtime.world.seed,
                }
            )
            await self._emit(runtime, "baseline.confirmed")
            await self._emit(runtime, "branches.created")
            await self._persist(runtime)
            return runtime.world.model_copy(deep=True)

    def _branch(self, role: str, checkpoint_id: str, policy: PolicyV4) -> BranchRuntimeStateV9:
        kind = BranchKind.CONTROL if role == "control" else BranchKind.TREATMENT
        branch = BranchRuntimeStateV9(
            branch_id=role,
            kind=kind,
            label="原始方案" if role == "control" else "干预方案",
            parent_checkpoint_id=checkpoint_id,
            policy=policy,
        )
        branch.province_resource_envelopes = {
            code: self._province_envelope(branch, code) for code in MAINLAND_PROVINCE_CODES
        }
        branch.automaker_resource_envelopes = {
            automaker_id: self._automaker_envelope(branch, automaker_id)
            for automaker_id in AUTOMAKER_IDS
        }
        branch.remaining_province_budget = {
            code: envelope.available_policy_budget
            for code, envelope in branch.province_resource_envelopes.items()
        }
        branch.remaining_automaker_budget = {
            automaker_id: envelope.national_market_budget
            for automaker_id, envelope in branch.automaker_resource_envelopes.items()
        }
        return branch

    def _province_envelope(
        self, branch: BranchRuntimeStateV9, code: str
    ) -> ProvinceResourceEnvelope:
        profile = self.profiles[code]
        share = branch.policy.share_for_region(profile.policy_region.value)
        available = _clamp(0.30 + 0.32 * profile.fiscal_capacity + 0.18 * share, 0.30, 0.78)
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
            evidence_refs=[f"policy:{branch.policy.policy_id}", f"fact:{code}"],
        )

    def _automaker_envelope(
        self, branch: BranchRuntimeStateV9, automaker_id: str
    ) -> AutomakerResourceEnvelope:
        persona = self.automaker_personas[automaker_id]
        budget = round(
            max(
                8.0,
                min(
                    20.0,
                    11.0
                    + 7 * persona.growth_goal
                    + 3 * persona.channel_expansion_tendency
                    - 5 * persona.cashflow_constraint,
                ),
            ),
            4,
        )
        max_facilities = (
            1
            + int(persona.new_capacity_willingness >= 0.45)
            + int(persona.new_capacity_willingness >= 0.70)
        )
        return AutomakerResourceEnvelope(
            envelope_id=_stable_id("automaker_envelope", branch.branch_id, automaker_id, budget),
            branch_id=branch.branch_id,
            automaker_id=automaker_id,
            national_market_budget=budget,
            max_expand_provinces=max(2, min(5, round(2 + 3 * persona.channel_expansion_tendency))),
            facility_budget=round(max_facilities * 0.65, 4),
            max_facility_targets=max_facilities,
            cashflow_constraint=persona.cashflow_constraint,
            capacity_pressure=persona.capacity_pressure,
            management_capacity=_clamp(1 - 0.5 * persona.cashflow_constraint),
            evidence_refs=[f"persona:{automaker_id}"],
        )

    async def run(
        self, experiment_id: str, *, until_tick: MacroTick | None = None
    ) -> WorldStateV10:
        runtime = self._runtime(experiment_id)
        async with runtime.lock:
            if runtime.world.status not in {
                V32ExperimentStatus.READY,
                V32ExperimentStatus.RUNNING,
            }:
                if runtime.world.status is V32ExperimentStatus.COMPLETED:
                    target = until_tick or MacroTick.Q4
                    if target in runtime.world.branches["control"].completed_ticks:
                        return runtime.world.model_copy(deep=True)
                raise ValueError("experiment is not ready to run")
            target = until_tick or MacroTick.Q4
            completed_count = len(runtime.world.branches["control"].completed_ticks)
            if target.order < completed_count - 1:
                raise ValueError("RUN_TARGET_BEHIND_LAST_FROZEN_TICK")
            runtime.world.status = V32ExperimentStatus.RUNNING
            for tick in MacroTick:
                if tick.order < completed_count:
                    continue
                await self._run_tick(runtime, tick)
                if tick is target:
                    break
            if MacroTick.Q4 in runtime.world.branches["control"].completed_ticks:
                runtime.comparison = self._build_comparison(runtime.world)
                runtime.world.central_call_count = 2
                runtime.world.central_review = runtime.comparison.central_review
                runtime.world.status = V32ExperimentStatus.COMPLETED
                runtime.world.journey_step = JourneyStep.RESULT_REVIEW
                await self._emit(runtime, "comparison.completed", tick=MacroTick.Q4)
            else:
                runtime.world.status = V32ExperimentStatus.READY
            await self._persist(runtime)
            return runtime.world.model_copy(deep=True)

    async def _run_tick(self, runtime: M34Runtime, tick: MacroTick) -> None:
        branches = runtime.world.branches.values()
        if any(tick.order != len(branch.completed_ticks) for branch in branches):
            raise ValueError("TICK_PREFIX_INVALID")
        for branch in branches:
            branch.current_tick = tick
            branch.current_wave = InteractionWave.WAVE_0
        for wave in InteractionWave:
            candidate_ids = {
                branch.branch_id: self._candidate_ids(runtime.world, branch, tick, wave)
                for branch in branches
            }
            if not any(candidate_ids.values()):
                break
            # Branch and wave barrier: every inbox is frozen before any provider output is used.
            inboxes = {
                branch.branch_id: [
                    self._build_inbox(runtime.world, branch, tick, wave, agent_id)
                    for agent_id in candidate_ids[branch.branch_id]
                ]
                for branch in branches
            }
            for branch in branches:
                branch.current_wave = wave
                branch.inboxes.extend(inboxes[branch.branch_id])
            decisions_by_branch = await asyncio.gather(
                *(
                    self._collect_wave_decisions(
                        runtime.world, branch, tick, wave, inboxes[branch.branch_id]
                    )
                    for branch in branches
                )
            )
            for branch, decisions in zip(branches, decisions_by_branch, strict=True):
                self._commit_wave(runtime, branch, tick, wave, decisions)
                await self._emit(
                    runtime,
                    "interaction.wave.completed",
                    branch_id=branch.branch_id,
                    tick=tick,
                    wave=wave,
                    payload={
                        "agent_call_count": len(decisions),
                        "message_count": sum(len(item.outgoing_messages) for item in decisions),
                    },
                )
            await self._persist(runtime)
        for branch in branches:
            self._settle_tick(runtime.world, branch, tick)
            branch.completed_ticks.append(tick)
            branch.current_wave = None
            await self._emit(
                runtime,
                "environment.quarter.completed",
                branch_id=branch.branch_id,
                tick=tick,
                payload={"checkpoint_id": branch.checkpoints[tick].checkpoint_id},
            )
        if any(branch.completed_ticks != list(MacroTick)[: tick.order + 1] for branch in branches):
            raise RuntimeError("tick barrier incomplete")
        await self._persist(runtime)

    def _candidate_ids(
        self,
        world: WorldStateV10,
        branch: BranchRuntimeStateV9,
        tick: MacroTick,
        wave: InteractionWave,
    ) -> list[str]:
        if tick is MacroTick.Q1 and wave is InteractionWave.WAVE_0:
            return [*MAINLAND_PROVINCE_CODES, *AUTOMAKER_IDS]
        pending: set[str] = set()
        messages = [
            item for item in branch.messages if item.tick is tick and item.wave.order < wave.order
        ]
        prior_decisions = [
            item
            for item in branch.decisions
            if item.tick.order < tick.order or (item.tick is tick and item.wave.order < wave.order)
        ]
        attended = {
            message_id for item in prior_decisions for message_id in item.attended_message_ids
        }
        for message in messages:
            if message.message_id not in attended:
                pending.update(message.recipient_ids)
        for session in branch.sessions:
            if session.tick is tick and session.state not in TERMINAL_TRANSACTION_STATES:
                latest = next(
                    item
                    for item in reversed(branch.messages)
                    if item.session_id == session.session_id
                )
                pending.update(
                    participant
                    for participant in session.participant_ids
                    if participant != latest.sender_id
                )
        for decision in prior_decisions:
            if decision.deferred_until_tick is tick:
                pending.add(decision.agent_id)
            # A time/environment condition authorizes the next quarterly review once.
            # It must not repeatedly reactivate the same actor in later waves of the
            # current tick after that actor has already returned a decision.
            if decision.tick.order < tick.order and self._conditions_met(
                world, branch, tick, decision.reconsideration_conditions
            ):
                pending.add(decision.agent_id)
        for event in self._events_released(world, branch, tick, wave, exact=True):
            if "province" in event.affected_subjects:
                pending.update(MAINLAND_PROVINCE_CODES)
            if "automaker" in event.affected_subjects:
                pending.update(AUTOMAKER_IDS)
        if wave is InteractionWave.WAVE_0 and tick is not MacroTick.Q1:
            # Quarterly feedback itself is authorized new context. It reactivates only
            # actors whose structured conditions or event/transaction contexts require it.
            for decision in reversed(prior_decisions):
                if decision.agent_id in pending:
                    continue
                if decision.reconsideration_conditions:
                    pending.add(decision.agent_id)
        return sorted(pending, key=lambda item: (item not in MAINLAND_PROVINCE_CODES, item))

    @staticmethod
    def _conditions_met(
        world: WorldStateV10,
        branch: BranchRuntimeStateV9,
        tick: MacroTick,
        conditions: list[ReconsiderationCondition],
    ) -> bool:
        del world
        if not conditions:
            return False
        previous = branch.checkpoints.get(list(MacroTick)[tick.order - 1]) if tick.order else None
        for condition in conditions:
            if condition.source == "time" and condition.operator == "eq":
                if condition.threshold == tick.value:
                    return True
            if condition.source == "environment" and previous:
                value = getattr(previous.settlement.national_metrics, condition.field, None)
                if isinstance(value, (float, int)) and isinstance(
                    condition.threshold, (float, int)
                ):
                    if condition.operator == "gte" and value >= condition.threshold:
                        return True
                    if condition.operator == "lte" and value <= condition.threshold:
                        return True
        return False

    def _build_inbox(
        self,
        world: WorldStateV10,
        branch: BranchRuntimeStateV9,
        tick: MacroTick,
        wave: InteractionWave,
        agent_id: str,
    ) -> AuthorizedInbox:
        is_province = agent_id in MAINLAND_PROVINCE_CODES
        visible_messages = [
            item
            for item in branch.messages
            if item.tick is tick
            and item.wave.order < wave.order
            and self._message_visible_to(branch, item, agent_id)
        ]
        previous_checkpoint = (
            branch.checkpoints.get(list(MacroTick)[tick.order - 1]) if tick.order else None
        )
        own_summary = None
        public_summary = None
        if previous_checkpoint:
            national_metrics = previous_checkpoint.settlement.national_metrics
            public_summary = (
                f"全国需求指数 {national_metrics.nev_demand:.1f}，"
                f"区域差距 {national_metrics.regional_development_gap:.1f}。"
            )
            if is_province:
                state = previous_checkpoint.settlement.province_states[agent_id]
                own_summary = (
                    f"本省需求 {state.demand_index:.1f}，产业 {state.industry_activity_index:.1f}，"
                    f"财政压力 {state.fiscal_pressure_index:.1f}。"
                )
            else:
                state = previous_checkpoint.settlement.automaker_states[agent_id]
                own_summary = (
                    f"自身全国组合 ROI {state.simulated_roi_index:.1f}，"
                    f"销售活动 {state.sales_activity_index:.1f}。"
                )
        previous_decision = next(
            (item for item in reversed(branch.decisions) if item.agent_id == agent_id), None
        )
        pending_sessions = [
            item.session_id
            for item in branch.sessions
            if agent_id in item.participant_ids and item.state not in TERMINAL_TRANSACTION_STATES
        ]
        visible_events = [
            item.event_plan_id
            for item in self._events_released(world, branch, tick, wave, exact=False)
        ]
        payload = {
            "branch_id": branch.branch_id,
            "tick": tick,
            "wave": wave,
            "agent_id": agent_id,
            "message_ids": [item.message_id for item in visible_messages],
            "event_ids": visible_events,
            "own_summary": own_summary,
            "public_summary": public_summary,
            "pending_sessions": pending_sessions,
        }
        return AuthorizedInbox(
            inbox_id=_stable_id("inbox", payload),
            branch_id=branch.branch_id,
            tick=tick,
            wave=wave,
            agent_kind=AgentKindM34.PROVINCE if is_province else AgentKindM34.AUTOMAKER,
            agent_id=agent_id,
            message_ids=payload["message_ids"],
            public_policy_summary=(
                f"西部 {branch.policy.west_central_share:.0%}、中部 "
                f"{branch.policy.central_central_share:.0%}、东部 "
                f"{branch.policy.east_central_share:.0%}。"
            ),
            public_national_summary=public_summary,
            own_result_summary=own_summary,
            pending_session_ids=pending_sessions,
            visible_event_ids=visible_events,
            previous_decision_id=previous_decision.decision_id if previous_decision else None,
            context_hash=canonical_hash(payload),
        )

    def _message_visible_to(
        self, branch: BranchRuntimeStateV9, message: InteractionMessage, agent_id: str
    ) -> bool:
        if message.branch_id != branch.branch_id:
            return False
        if agent_id == message.sender_id or agent_id in message.recipient_ids:
            return True
        if message.visibility is MessageVisibility.PUBLIC:
            return True
        if message.visibility is MessageVisibility.OBSERVATION_NETWORK:
            return any(
                relation.relation_type == "observation"
                and relation.source_code == agent_id
                and relation.target_code == message.sender_id
                for relation in self.relation_network.relations
            )
        return False

    async def _collect_wave_decisions(
        self,
        world: WorldStateV10,
        branch: BranchRuntimeStateV9,
        tick: MacroTick,
        wave: InteractionWave,
        inboxes: list[AuthorizedInbox],
    ) -> list[AgentTickDecision]:
        tick_calls = sum(item.tick is tick for item in branch.decisions)
        allowed = max(0, MAX_CALLS_PER_TICK - tick_calls)
        if len(inboxes) > allowed:
            branch.interaction_budget_exhausted = True
            inboxes = inboxes[:allowed]
        return list(
            await asyncio.gather(
                *(self._resolve_decision(world, branch, inbox) for inbox in inboxes)
            )
        )

    async def _resolve_decision(
        self,
        world: WorldStateV10,
        branch: BranchRuntimeStateV9,
        inbox: AuthorizedInbox,
    ) -> AgentTickDecision:
        def fallback() -> AgentTickDecision:
            return self._fallback_decision(world, branch, inbox)

        decision = await self.agent_provider.resolve(
            kind=f"{inbox.agent_kind.value}_tick",
            instruction=(
                "基于授权 Inbox 决定 ignore、monitor、initiate、respond 或 revise；"
                "消息与资源必须满足 Schema 和年度剩余预算。"
            ),
            authorized_context=inbox.model_dump(mode="json"),
            response_type=AgentTickDecision,
            fallback=fallback,
        )
        try:
            self._validate_decision(branch, inbox, decision)
        except ValueError as error:
            # Resource and authorization validation is outside the JSON schema. A
            # syntactically valid Live/Cache result may still be illegal, in which
            # case the deterministic candidate is allowed to take over explicitly.
            decision = fallback().model_copy(
                update={"fallback_reason": f"domain_validation_failed:{type(error).__name__}"}
            )
            self._validate_decision(branch, inbox, decision)
        branch.agent_invocations.append(
            AgentInvocationRecord(
                invocation_id=_stable_id("invocation", decision.decision_id),
                branch_id=branch.branch_id,
                agent_id=inbox.agent_id,
                kind=f"{inbox.agent_kind.value}_tick",
                model=self.agent_provider.model_name_for(f"{inbox.agent_kind.value}_tick"),
                run_mode="fallback" if decision.fallback_used else self.agent_provider.run_mode,
                input_hash=canonical_hash(inbox),
                output_hash=canonical_hash(decision),
                output_schema=decision.schema_version,
                fallback_used=decision.fallback_used,
            )
        )
        return decision

    def _fallback_decision(
        self,
        world: WorldStateV10,
        branch: BranchRuntimeStateV9,
        inbox: AuthorizedInbox,
    ) -> AgentTickDecision:
        tick = inbox.tick
        wave = inbox.wave
        agent_id = inbox.agent_id
        previous = next(
            (item for item in reversed(branch.decisions) if item.agent_id == agent_id), None
        )
        engagement = (
            EngagementMode.RESPOND
            if inbox.pending_session_ids or inbox.message_ids
            else EngagementMode.REVISE
            if previous
            else EngagementMode.INITIATE
        )
        if inbox.agent_kind is AgentKindM34.PROVINCE:
            profile = self.profiles[agent_id]
            envelope = branch.province_resource_envelopes[agent_id]
            prior = branch.latest_province_actions.get(agent_id)
            event_shift = 0.015 * len(inbox.visible_event_ids)
            support = _clamp(
                prior.overall_support_intensity
                if prior
                else envelope.available_policy_budget * 0.82,
                0.05,
                envelope.available_policy_budget,
            )
            mix = (
                prior.subsidy_mix
                if prior
                else _normalize_mix(
                    0.3 + 0.35 * profile.willingness_to_pay_index + event_shift,
                    0.3 + 0.3 * profile.nev_industry_base,
                    0.3 + 0.25 * (1 - profile.logistics_cost_index),
                )
            )
            action = ProvinceQuarterAction(
                action_id=_stable_id("province_action", branch.branch_id, tick, wave, agent_id),
                branch_id=branch.branch_id,
                tick=tick,
                province_code=agent_id,
                overall_support_intensity=support,
                subsidy_mix=mix,
                public_summary="在年度财政空间内维持或重配三类支持。",
            )
            messages = self._fallback_province_messages(branch, inbox)
            return AgentTickDecision(
                decision_id=_stable_id("decision", branch.branch_id, tick, wave, agent_id),
                branch_id=branch.branch_id,
                tick=tick,
                wave=wave,
                agent_kind=inbox.agent_kind,
                agent_id=agent_id,
                inbox_id=inbox.inbox_id,
                engagement=engagement,
                attended_message_ids=inbox.message_ids,
                noticed_facts=[*inbox.visible_event_ids, *inbox.pending_session_ids][:12],
                province_action=action,
                outgoing_messages=messages,
                alternatives=["维持上一季度配置", "重配消费端与产业端支持"],
                opportunity_costs=["提高一类工具份额会压缩其他工具空间"],
                reconsideration_conditions=[
                    ReconsiderationCondition(
                        condition_id=_stable_id("condition", agent_id, tick, "next"),
                        source="time",
                        field="tick",
                        operator="eq",
                        threshold=(
                            list(MacroTick)[tick.order + 1].value
                            if tick is not MacroTick.Q4
                            else "Q4"
                        ),
                        action_if_met="读取新的季度结果后复评",
                    )
                ],
                evidence_refs=[f"inbox:{inbox.inbox_id}", f"policy:{branch.policy.policy_id}"],
                fallback_used=True,
                fallback_reason="fake_provider_deterministic_fallback",
            )
        action = self._fallback_automaker_action(branch, inbox)
        messages = self._fallback_automaker_messages(branch, inbox)
        return AgentTickDecision(
            decision_id=_stable_id("decision", branch.branch_id, tick, wave, agent_id),
            branch_id=branch.branch_id,
            tick=tick,
            wave=wave,
            agent_kind=inbox.agent_kind,
            agent_id=agent_id,
            inbox_id=inbox.inbox_id,
            engagement=engagement,
            attended_message_ids=inbox.message_ids,
            noticed_facts=[*inbox.visible_event_ids, *inbox.pending_session_ids][:12],
            automaker_action=action,
            outgoing_messages=messages,
            alternatives=["维持全国投入组合", "在现有资源内重配省份投入"],
            opportunity_costs=["增加一个省份的战略投入会挤占全国资源包"],
            reconsideration_conditions=[
                ReconsiderationCondition(
                    condition_id=_stable_id("condition", agent_id, tick, "next"),
                    source="time",
                    field="tick",
                    operator="eq",
                    threshold=(
                        list(MacroTick)[tick.order + 1].value if tick is not MacroTick.Q4 else "Q4"
                    ),
                    action_if_met="读取自身全国组合表现后复评",
                )
            ],
            evidence_refs=[f"inbox:{inbox.inbox_id}", f"persona:{agent_id}"],
            fallback_used=True,
            fallback_reason="fake_provider_deterministic_fallback",
        )

    def _fallback_province_messages(
        self, branch: BranchRuntimeStateV9, inbox: AuthorizedInbox
    ) -> list[InteractionMessage]:
        messages: list[InteractionMessage] = []
        pending = [item for item in branch.sessions if item.session_id in inbox.pending_session_ids]
        for session in pending[:2]:
            previous_message = next(
                item for item in reversed(branch.messages) if item.session_id == session.session_id
            )
            accept = int(canonical_hash((session.session_id, inbox.agent_id))[:2], 16) % 3 != 0
            state = TransactionState.ACCEPTED if accept else TransactionState.REJECTED
            messages.append(
                self._message(
                    branch,
                    inbox,
                    kind=MessageKind.TRANSACTION_RESPONSE,
                    visibility=MessageVisibility.PRIVATE,
                    recipients=[item for item in session.participant_ids if item != inbox.agent_id],
                    session_id=session.session_id,
                    state=state,
                    reply_to=previous_message.message_id,
                    resource_amount=previous_message.resource_amount,
                    summary="接受并进入资源校验。" if accept else "在当前资源约束下拒绝。",
                )
            )
        if not pending and inbox.tick is MacroTick.Q1 and inbox.wave is InteractionWave.WAVE_0:
            peers = sorted(
                relation.target_code
                for relation in self.relation_network.relations
                if relation.source_code == inbox.agent_id
                and relation.relation_type == "coordination"
            )
            if peers and int(inbox.agent_id) % 11 == 0:
                target = peers[0]
                session_id = _stable_id(
                    "session", branch.branch_id, inbox.tick, inbox.agent_id, target
                )
                messages.append(
                    self._message(
                        branch,
                        inbox,
                        kind=MessageKind.INTERPROVINCIAL_PROPOSAL,
                        visibility=MessageVisibility.PRIVATE,
                        recipients=[target],
                        session_id=session_id,
                        state=TransactionState.PROPOSED,
                        resource_amount=0.04,
                        summary="提出供应链与运营网络协同意向。",
                    )
                )
            if int(inbox.agent_id) % 13 == 0:
                target = AUTOMAKER_IDS[int(inbox.agent_id) % len(AUTOMAKER_IDS)]
                session_id = _stable_id(
                    "session", branch.branch_id, inbox.tick, inbox.agent_id, target
                )
                messages.append(
                    self._message(
                        branch,
                        inbox,
                        kind=MessageKind.PROVINCE_AUTOMAKER_PACKAGE,
                        visibility=MessageVisibility.PRIVATE,
                        recipients=[target],
                        session_id=session_id,
                        state=TransactionState.PROPOSED,
                        resource_amount=0.035,
                        summary="在现有三类工具内提出模拟协同资源包。",
                    )
                )
        return messages

    def _fallback_automaker_messages(
        self, branch: BranchRuntimeStateV9, inbox: AuthorizedInbox
    ) -> list[InteractionMessage]:
        messages: list[InteractionMessage] = []
        pending = [item for item in branch.sessions if item.session_id in inbox.pending_session_ids]
        for session in pending[:5]:
            previous = next(
                item for item in reversed(branch.messages) if item.session_id == session.session_id
            )
            selector = int(canonical_hash((session.session_id, inbox.agent_id))[:2], 16) % 4
            if selector == 0 and session.condition_rounds < MAX_CONDITION_ROUNDS_PER_PAIR:
                state = TransactionState.COUNTERED
                kind = MessageKind.AUTOMAKER_COUNTEROFFER
                summary = "在既有资源包内提出条件调整。"
            elif selector == 1:
                state = TransactionState.DEFERRED
                kind = MessageKind.TRANSACTION_RESPONSE
                summary = "暂缓至后续季度复评。"
            else:
                state = TransactionState.ACCEPTED
                kind = MessageKind.TRANSACTION_RESPONSE
                summary = "接受并进入资源校验。"
            messages.append(
                self._message(
                    branch,
                    inbox,
                    kind=kind,
                    visibility=MessageVisibility.PRIVATE,
                    recipients=[item for item in session.participant_ids if item != inbox.agent_id],
                    session_id=session.session_id,
                    state=state,
                    reply_to=previous.message_id,
                    resource_amount=previous.resource_amount,
                    summary=summary,
                )
            )
        return messages

    def _message(
        self,
        branch: BranchRuntimeStateV9,
        inbox: AuthorizedInbox,
        *,
        kind: MessageKind,
        visibility: MessageVisibility,
        recipients: list[str],
        session_id: str,
        state: TransactionState,
        resource_amount: float,
        summary: str,
        reply_to: str | None = None,
    ) -> InteractionMessage:
        message_id = _stable_id(
            "message",
            branch.branch_id,
            inbox.tick,
            inbox.wave,
            inbox.agent_id,
            recipients,
            session_id,
            state,
        )
        return InteractionMessage(
            message_id=message_id,
            branch_id=branch.branch_id,
            tick=inbox.tick,
            wave=inbox.wave,
            logical_sequence=0,
            kind=kind,
            visibility=visibility,
            sender_kind=inbox.agent_kind,
            sender_id=inbox.agent_id,
            recipient_ids=recipients,
            session_id=session_id,
            transaction_state=state,
            reply_to_message_id=reply_to,
            resource_amount=resource_amount,
            public_summary=summary,
            private_terms=summary,
            evidence_refs=[f"inbox:{inbox.inbox_id}"],
        )

    def _fallback_automaker_action(
        self, branch: BranchRuntimeStateV9, inbox: AuthorizedInbox
    ) -> AutomakerQuarterAction:
        automaker_id = inbox.agent_id
        persona = self.automaker_personas[automaker_id]
        envelope = branch.automaker_resource_envelopes[automaker_id]
        scores = []
        for code in MAINLAND_PROVINCE_CODES:
            profile = self.profiles[code]
            score = (
                0.35 * profile.market_scale
                + 0.25 * profile.willingness_to_pay_index
                + 0.20 * profile.nev_industry_base
                + 0.20 * (1 - profile.logistics_cost_index)
            )
            scores.append((code, score))
        score_total = sum(item[1] for item in scores)
        budget = min(
            envelope.national_market_budget,
            branch.remaining_automaker_budget.get(automaker_id, envelope.national_market_budget),
        )
        raw = {code: budget * score / score_total for code, score in scores}
        ordered = sorted(scores, key=lambda item: (-item[1], item[0]))
        expand_codes = {code for code, _ in ordered[: envelope.max_expand_provinces]}
        actions = [
            ProvinceMarketAction(
                province_code=code,
                sales_investment_intensity=_clamp(raw[code], 0, 1),
                channel_strategy=(
                    ChannelStrategy.EXPAND if code in expand_codes else ChannelStrategy.MAINTAIN
                ),
            )
            for code in MAINLAND_PROVINCE_CODES
        ]
        facility_codes = [code for code, _ in ordered[: envelope.max_facility_targets]]
        facilities = [
            FacilityAction(
                province_code=code,
                action=FacilityActionKind.EXPAND,
                investment_intensity=_clamp(
                    envelope.facility_budget / max(1, len(facility_codes)), 0, 1
                ),
            )
            for code in facility_codes
        ]
        return AutomakerQuarterAction(
            action_id=_stable_id(
                "automaker_action", branch.branch_id, inbox.tick, inbox.wave, automaker_id
            ),
            branch_id=branch.branch_id,
            tick=inbox.tick,
            automaker_id=automaker_id,
            province_market_actions=actions,
            facility_actions=facilities,
            public_summary=(
                "在冻结全国资源包内维持或重配市场、渠道与模拟产能意向。"
                if persona.cashflow_constraint < 0.7
                else "受现金流代理约束，保持审慎的全国资源组合。"
            ),
        )

    def _validate_decision(
        self,
        branch: BranchRuntimeStateV9,
        inbox: AuthorizedInbox,
        decision: AgentTickDecision,
    ) -> None:
        if (
            decision.branch_id != branch.branch_id
            or decision.tick is not inbox.tick
            or decision.wave is not inbox.wave
            or decision.agent_id != inbox.agent_id
            or decision.agent_kind is not inbox.agent_kind
            or decision.inbox_id != inbox.inbox_id
        ):
            raise ValueError("agent decision identity does not match authorized inbox")
        if not set(decision.attended_message_ids) <= set(inbox.message_ids):
            raise ValueError("decision attended unauthorized message")
        for message in decision.outgoing_messages:
            if (
                message.branch_id != branch.branch_id
                or message.tick is not inbox.tick
                or message.wave is not inbox.wave
                or message.sender_id != inbox.agent_id
            ):
                raise ValueError("outgoing message violates branch/tick/sender authorization")
        sent_this_tick = [
            item
            for item in branch.messages
            if item.tick is inbox.tick and item.sender_id == inbox.agent_id
        ]
        if inbox.agent_kind is AgentKindM34.PROVINCE:
            interprovincial_count = sum(
                item.kind is MessageKind.INTERPROVINCIAL_PROPOSAL
                for item in [*sent_this_tick, *decision.outgoing_messages]
            )
            province_automaker_count = sum(
                item.kind is MessageKind.PROVINCE_AUTOMAKER_PACKAGE
                for item in [*sent_this_tick, *decision.outgoing_messages]
            )
            if interprovincial_count > 2 or province_automaker_count > 2:
                raise ValueError("province cumulative per-tick interaction budget exceeded")
        else:
            private_transaction_count = sum(
                item.session_id is not None
                for item in [*sent_this_tick, *decision.outgoing_messages]
            )
            if private_transaction_count > 5:
                raise ValueError("automaker cumulative per-tick interaction budget exceeded")
        if decision.province_action:
            envelope = branch.province_resource_envelopes[inbox.agent_id]
            if (
                decision.province_action.overall_support_intensity
                > envelope.available_policy_budget
            ):
                raise ValueError("province action exceeds annual resource envelope")
        if decision.automaker_action:
            envelope = branch.automaker_resource_envelopes[inbox.agent_id]
            if (
                sum(
                    item.sales_investment_intensity
                    for item in decision.automaker_action.province_market_actions
                )
                > envelope.national_market_budget + 1e-4
            ):
                raise ValueError("automaker action exceeds national market budget")

    def _commit_wave(
        self,
        runtime: M34Runtime,
        branch: BranchRuntimeStateV9,
        tick: MacroTick,
        wave: InteractionWave,
        decisions: list[AgentTickDecision],
    ) -> None:
        existing_messages = sum(item.tick is tick for item in branch.messages)
        outgoing = sorted(
            [message for decision in decisions for message in decision.outgoing_messages],
            key=lambda item: item.message_id,
        )
        remaining = max(0, MAX_MESSAGES_PER_TICK - existing_messages)
        if len(outgoing) > remaining:
            branch.interaction_budget_exhausted = True
            allowed_ids = {item.message_id for item in outgoing[:remaining]}
            decisions = [
                item.model_copy(
                    update={
                        "outgoing_messages": [
                            message
                            for message in item.outgoing_messages
                            if message.message_id in allowed_ids
                        ]
                    }
                )
                for item in decisions
            ]
            outgoing = outgoing[:remaining]
        for message in outgoing:
            runtime.logical_sequence += 1
            message.logical_sequence = runtime.logical_sequence
        branch.decisions.extend(sorted(decisions, key=lambda item: item.agent_id))
        branch.messages.extend(outgoing)
        for decision in decisions:
            if decision.province_action:
                branch.latest_province_actions[decision.agent_id] = decision.province_action
            if decision.automaker_action:
                branch.latest_automaker_actions[decision.agent_id] = decision.automaker_action
        for message in outgoing:
            self._apply_message(branch, message)

    def _apply_message(self, branch: BranchRuntimeStateV9, message: InteractionMessage) -> None:
        if not message.session_id or not message.transaction_state:
            return
        session = next(
            (item for item in branch.sessions if item.session_id == message.session_id), None
        )
        if session is None:
            if message.transaction_state is not TransactionState.PROPOSED:
                raise ValueError("non-proposal message cannot create interaction session")
            session = InteractionSession(
                session_id=message.session_id,
                branch_id=branch.branch_id,
                tick=message.tick,
                participant_ids=sorted([message.sender_id, *message.recipient_ids])[:2],
                initiator_id=message.sender_id,
                state=TransactionState.PROPOSED,
                message_ids=[message.message_id],
                reserved_resource=message.resource_amount,
                evidence_refs=[f"message:{message.message_id}"],
            )
            branch.sessions.append(session)
            return
        if session.state in TERMINAL_TRANSACTION_STATES:
            # Two actors may have prepared responses from the same frozen wave inbox.
            # The first stable message settles the session; later same-wave messages
            # remain replay facts but cannot mutate the terminal transaction.
            return
        rounds = session.condition_rounds + int(
            message.transaction_state is TransactionState.COUNTERED
        )
        if rounds > MAX_CONDITION_ROUNDS_PER_PAIR:
            session.state = TransactionState.EXPIRED
            return
        state = message.transaction_state
        contribution = 0.0
        if state is TransactionState.ACCEPTED:
            valid = self._reserve_session_resource(branch, session, message.resource_amount)
            state = TransactionState.SETTLED if valid else TransactionState.RESOURCE_INVALID
            contribution = min(0.2, message.resource_amount) if valid else 0.0
        session.state = state
        session.condition_rounds = rounds
        session.message_ids.append(message.message_id)
        session.settled_contribution = contribution
        session.evidence_refs.append(f"message:{message.message_id}")

    @staticmethod
    def _reserve_session_resource(
        branch: BranchRuntimeStateV9,
        session: InteractionSession,
        amount: float,
    ) -> bool:
        initiator = session.initiator_id
        if initiator in branch.remaining_province_budget:
            available = branch.remaining_province_budget[initiator]
            if amount > available + 1e-9:
                return False
            branch.remaining_province_budget[initiator] = round(available - amount, 6)
            return True
        if initiator in branch.remaining_automaker_budget:
            available = branch.remaining_automaker_budget[initiator]
            if amount > available + 1e-9:
                return False
            branch.remaining_automaker_budget[initiator] = round(available - amount, 6)
            return True
        return False

    def _events_released(
        self,
        world: WorldStateV10,
        branch: BranchRuntimeStateV9,
        tick: MacroTick,
        wave: InteractionWave,
        *,
        exact: bool,
    ) -> list[EventPlanV2]:
        if not world.design:
            return []
        result = []
        for event in world.design.event_plans:
            if event.branch_scope == "treatment_only" and branch.kind is BranchKind.CONTROL:
                continue
            released = (tick.order, wave.order) >= (
                event.scheduled_tick.order,
                event.release_wave.order,
            )
            if exact:
                released = (tick, wave) == (event.scheduled_tick, event.release_wave)
            if released:
                result.append(event)
        return sorted(result, key=lambda item: item.event_plan_id)

    def _settle_tick(
        self, world: WorldStateV10, branch: BranchRuntimeStateV9, tick: MacroTick
    ) -> None:
        if set(branch.latest_province_actions) != set(MAINLAND_PROVINCE_CODES):
            raise ValueError("quarter cannot settle before all province actions exist")
        if set(branch.latest_automaker_actions) != set(AUTOMAKER_IDS):
            raise ValueError("quarter cannot settle before all automaker actions exist")
        previous = branch.checkpoints.get(list(MacroTick)[tick.order - 1]) if tick.order else None
        active_events = self._events_released(
            world, branch, tick, InteractionWave.WAVE_2, exact=False
        )
        settled_sessions = [
            item
            for item in branch.sessions
            if item.tick is tick and item.state is TransactionState.SETTLED
        ]
        settlement = settle_quarter(
            previous,
            (branch.policy, branch.latest_province_actions, branch.latest_automaker_actions),
            settled_sessions,
            active_events,
            branch_id=branch.branch_id,
            tick=tick,
        )
        branch.province_states = settlement.province_states
        branch.automaker_states = settlement.automaker_states
        branch.national_metrics = settlement.national_metrics
        branch.mechanism_totals = settlement.mechanism_totals
        decision_ids = [item.decision_id for item in branch.decisions if item.tick is tick]
        message_ids = [item.message_id for item in branch.messages if item.tick is tick]
        session_ids = [item.session_id for item in branch.sessions if item.tick is tick]
        parent = previous.checkpoint_id if previous else branch.parent_checkpoint_id
        payload = {
            "experiment_id": world.experiment_id,
            "branch_id": branch.branch_id,
            "tick": tick,
            "parent": parent,
            "settlement": settlement,
            "decisions": decision_ids,
            "messages": message_ids,
            "sessions": session_ids,
            "resources": {
                "province": branch.remaining_province_budget,
                "automaker": branch.remaining_automaker_budget,
            },
        }
        branch.checkpoints[tick] = TickCheckpoint(
            checkpoint_id=_stable_id("tick_checkpoint", payload),
            experiment_id=world.experiment_id,
            branch_id=branch.branch_id,
            tick=tick,
            parent_checkpoint_id=parent,
            settlement=settlement,
            decision_ids=decision_ids,
            message_ids=message_ids,
            session_ids=session_ids,
            resource_hash=canonical_hash(payload["resources"]),
            state_hash=canonical_hash(payload),
        )

    def _build_comparison(self, world: WorldStateV10) -> ComparisonResultV10:
        if world.design is None or world.baseline is None:
            raise ValueError("comparison requires design and baseline")
        control = world.branches["control"]
        treatment = world.branches["treatment"]
        c_metrics = control.checkpoints[MacroTick.Q4].settlement.national_metrics
        t_metrics = treatment.checkpoints[MacroTick.Q4].settlement.national_metrics
        fields = (
            "regional_development_gap",
            "central_fiscal_burden",
            "local_fiscal_pressure",
            "nev_demand",
            "new_investment_concentration",
            "industrial_agglomeration",
        )
        metrics = {
            field: MetricComparisonV10(
                control=getattr(c_metrics, field),
                treatment=getattr(t_metrics, field),
                delta=round(getattr(t_metrics, field) - getattr(c_metrics, field), 4),
            )
            for field in fields
        }
        delta_gap = metrics["regional_development_gap"].delta
        same_policy = (
            world.design.control_policy.west_central_share,
            world.design.control_policy.central_central_share,
            world.design.control_policy.east_central_share,
        ) == (
            world.design.treatment_policy.west_central_share,
            world.design.treatment_policy.central_central_share,
            world.design.treatment_policy.east_central_share,
        )
        same_event = all(item.branch_scope == "both" for item in world.design.event_plans)
        active_difference = (
            "event"
            if world.design.experiment_type is ExperimentType.EVENT_COUNTERFACTUAL
            else "policy"
        )
        if active_difference == "event" and (not same_policy or same_event):
            raise ValueError("event counterfactual active difference proof failed")
        if active_difference == "policy" and same_policy:
            raise ValueError("policy active difference proof failed")
        control_settled = sum(item.state is TransactionState.SETTLED for item in control.sessions)
        treatment_settled = sum(
            item.state is TransactionState.SETTLED for item in treatment.sessions
        )
        fallback_count = sum(
            item.fallback_used for branch in (control, treatment) for item in branch.decisions
        )
        direction = (
            "narrowed" if delta_gap < -1e-6 else "widened" if delta_gap > 1e-6 else "unchanged"
        )
        central_review = (
            f"年度同源比较完成：干预方案相对原始方案的区域差距变化为 {delta_gap:+.2f} 指数点；"
            "结论仅适用于本次冻结政策、事件、数据与机制版本。"
        )
        return ComparisonResultV10(
            experiment_id=world.experiment_id,
            experiment_type=world.design.experiment_type,
            control_branch_id="control",
            treatment_branch_id="treatment",
            active_difference=active_difference,
            same_policy=same_policy,
            same_event=same_event,
            baseline_checkpoint_id=world.baseline.checkpoint_id,
            control_q4_checkpoint_id=control.checkpoints[MacroTick.Q4].checkpoint_id,
            treatment_q4_checkpoint_id=treatment.checkpoints[MacroTick.Q4].checkpoint_id,
            delta_gap=delta_gap,
            gap_direction=direction,
            national_metrics=metrics,
            settled_interaction_delta=treatment_settled - control_settled,
            fallback_count=fallback_count,
            conclusion=central_review,
            central_review=central_review,
        )

    async def _emit(
        self,
        runtime: M34Runtime,
        event_type: str,
        *,
        branch_id: str | None = None,
        tick: MacroTick | None = None,
        wave: InteractionWave | None = None,
        message_id: str | None = None,
        session_id: str | None = None,
        payload: dict[str, str | int | float | bool | None] | None = None,
    ) -> None:
        runtime.event_counter += 1
        runtime.logical_sequence += 1
        runtime.events.append(
            EventV10(
                event_id=f"evt_m34_{runtime.event_counter:08d}",
                type=event_type,
                experiment_id=runtime.world.experiment_id,
                branch_id=branch_id,
                journey_step=runtime.world.journey_step,
                tick=tick,
                wave=wave,
                logical_sequence=runtime.logical_sequence,
                message_id=message_id,
                session_id=session_id,
                payload=payload or {},
            )
        )
        async with runtime.condition:
            runtime.condition.notify_all()

    def has_experiment(self, experiment_id: str) -> bool:
        if experiment_id in self.runtimes:
            return True
        if not EXPERIMENT_ID_PATTERN.fullmatch(experiment_id):
            return False
        path = self.runtime_dir / experiment_id / "runtime-snapshot.json"
        if not path.is_file():
            return False
        self.runtimes[experiment_id] = self._restore_runtime(experiment_id)
        return True

    def _runtime(self, experiment_id: str) -> M34Runtime:
        if self.has_experiment(experiment_id):
            return self.runtimes[experiment_id]
        raise KeyError(f"experiment not found: {experiment_id}")

    def _restore_runtime(self, experiment_id: str) -> M34Runtime:
        path = self.runtime_dir / experiment_id / "runtime-snapshot.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("RUNTIME_SNAPSHOT_JSON_INVALID") from exc
        if payload.get("schema_version") != RUNTIME_SNAPSHOT_SCHEMA:
            raise ValueError("RUNTIME_SNAPSHOT_SCHEMA_INVALID")
        world = WorldStateV10.model_validate(payload["world"])
        events = [EventV10.model_validate(item) for item in payload["events"]]
        comparison = (
            ComparisonResultV10.model_validate(payload["comparison"])
            if payload.get("comparison")
            else None
        )
        if world.experiment_id != experiment_id or payload.get("world_hash") != canonical_hash(
            world
        ):
            raise ValueError("RUNTIME_SNAPSHOT_WORLD_HASH_INVALID")
        if payload.get("replay_hash") != canonical_hash(events):
            raise ValueError("RUNTIME_SNAPSHOT_REPLAY_HASH_INVALID")
        if payload.get("comparison_hash") != (canonical_hash(comparison) if comparison else None):
            raise ValueError("RUNTIME_SNAPSHOT_COMPARISON_HASH_INVALID")
        event_counter = payload.get("event_counter")
        logical_sequence = payload.get("logical_sequence")
        if event_counter != len(events) or not isinstance(logical_sequence, int):
            raise ValueError("RUNTIME_SNAPSHOT_COUNTER_INVALID")
        for index, event in enumerate(events, 1):
            if event.event_id != f"evt_m34_{index:08d}" or event.experiment_id != experiment_id:
                raise ValueError("RUNTIME_REPLAY_SEQUENCE_INVALID")
        return M34Runtime(
            world=world,
            events=events,
            comparison=comparison,
            event_counter=event_counter,
            logical_sequence=logical_sequence,
        )

    async def _persist(self, runtime: M34Runtime) -> None:
        experiment_dir = self.runtime_dir / runtime.world.experiment_id
        payload = {
            "schema_version": RUNTIME_SNAPSHOT_SCHEMA,
            "world": runtime.world.model_dump(mode="json"),
            "events": [item.model_dump(mode="json") for item in runtime.events],
            "comparison": runtime.comparison.model_dump(mode="json")
            if runtime.comparison
            else None,
            "event_counter": runtime.event_counter,
            "logical_sequence": runtime.logical_sequence,
            "world_hash": canonical_hash(runtime.world),
            "replay_hash": canonical_hash(runtime.events),
            "comparison_hash": canonical_hash(runtime.comparison) if runtime.comparison else None,
        }
        await asyncio.to_thread(
            self._atomic_write,
            experiment_dir / "runtime-snapshot.json",
            json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
        )

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, path)

    async def get_state(self, experiment_id: str) -> WorldStateV10:
        return self._runtime(experiment_id).world.model_copy(deep=True)

    async def get_comparison(self, experiment_id: str) -> ComparisonResultV10:
        runtime = self._runtime(experiment_id)
        if runtime.comparison is None:
            raise ValueError("COMPARISON_NOT_AVAILABLE")
        return runtime.comparison.model_copy(deep=True)

    async def get_interactions(
        self,
        experiment_id: str,
        *,
        branch_id: str | None = None,
        tick: MacroTick | None = None,
    ) -> InteractionMarket:
        world = self._runtime(experiment_id).world
        branches = [world.branches[branch_id]] if branch_id else list(world.branches.values())
        messages = [
            item
            for branch in branches
            for item in branch.messages
            if tick is None or item.tick is tick
        ]
        sessions = [
            item
            for branch in branches
            for item in branch.sessions
            if tick is None or item.tick is tick
        ]
        counts = Counter(item.state for item in sessions)
        return InteractionMarket(
            experiment_id=experiment_id,
            branch_id=branch_id,
            tick=tick,
            messages=sorted(messages, key=lambda item: (item.logical_sequence, item.message_id)),
            sessions=sorted(sessions, key=lambda item: item.session_id),
            state_counts=dict(counts),
            settled_count=counts[TransactionState.SETTLED],
            resource_reallocation_count=sum(
                item.kind is MessageKind.RESOURCE_REALLOCATION for item in messages
            ),
            fallback_count=sum(
                item.fallback_used
                for branch in branches
                for item in branch.decisions
                if tick is None or item.tick is tick
            ),
            budget_exhausted=any(item.interaction_budget_exhausted for item in branches),
        )

    async def get_decisions(
        self,
        experiment_id: str,
        *,
        branch_id: str | None = None,
        tick: MacroTick | None = None,
        wave: InteractionWave | None = None,
        agent_id: str | None = None,
    ) -> list[AgentTickDecision]:
        world = self._runtime(experiment_id).world
        branches = [world.branches[branch_id]] if branch_id else list(world.branches.values())
        return [
            item.model_copy(deep=True)
            for branch in branches
            for item in branch.decisions
            if (tick is None or item.tick is tick)
            and (wave is None or item.wave is wave)
            and (agent_id is None or item.agent_id == agent_id)
        ]

    async def get_events(
        self, experiment_id: str, after_event_id: str | None = None
    ) -> list[EventV10]:
        runtime = self._runtime(experiment_id)
        if not after_event_id:
            return [item.model_copy(deep=True) for item in runtime.events]
        match = EVENT_ID_PATTERN.fullmatch(after_event_id)
        if not match:
            raise ValueError("LAST_EVENT_ID_INVALID")
        cursor = int(match.group(1))
        return [
            item.model_copy(deep=True)
            for item in runtime.events
            if int(item.event_id[-8:]) > cursor
        ]

    async def wait_for_events(
        self,
        experiment_id: str,
        after_event_id: str | None,
        *,
        timeout_seconds: float = 10,
    ) -> list[EventV10]:
        runtime = self._runtime(experiment_id)
        events = await self.get_events(experiment_id, after_event_id)
        if events:
            return events
        try:
            async with runtime.condition:
                await asyncio.wait_for(runtime.condition.wait(), timeout=timeout_seconds)
        except TimeoutError:
            return []
        return await self.get_events(experiment_id, after_event_id)

    async def get_replay(self, experiment_id: str) -> list[dict[str, object]]:
        return [item.model_dump(mode="json") for item in await self.get_events(experiment_id)]

    async def get_presentation_timeline(self, experiment_id: str):
        runtime = self._runtime(experiment_id)
        return M34PresentationProjection(
            runtime.world, comparison_available=runtime.comparison is not None
        ).build_timeline()

    async def get_presentation_frame(self, experiment_id: str, frame_id: str):
        runtime = self._runtime(experiment_id)
        return M34PresentationProjection(
            runtime.world, comparison_available=runtime.comparison is not None
        ).get_frame(frame_id)

    async def get_province_detail(
        self, experiment_id: str, province_code: str
    ) -> dict[str, object]:
        if province_code not in MAINLAND_PROVINCE_CODES:
            raise KeyError(f"province not found: {province_code}")
        world = self._runtime(experiment_id).world
        return {
            "schema_version": "province-quarter-detail-v1",
            "experiment_id": experiment_id,
            "province_code": province_code,
            "profile": self.m29.province_profiles[province_code].model_dump(mode="json"),
            "branches": {
                role: {
                    "latest_action": branch.latest_province_actions.get(province_code).model_dump(
                        mode="json"
                    )
                    if province_code in branch.latest_province_actions
                    else None,
                    "state": branch.province_states.get(province_code).model_dump(mode="json")
                    if province_code in branch.province_states
                    else None,
                    "decisions": [
                        item.model_dump(mode="json")
                        for item in branch.decisions
                        if item.agent_id == province_code
                    ],
                    "sessions": [
                        item.model_dump(mode="json")
                        for item in branch.sessions
                        if province_code in item.participant_ids
                    ],
                }
                for role, branch in world.branches.items()
            },
        }

    async def get_automaker_detail(
        self, experiment_id: str, automaker_id: str
    ) -> dict[str, object]:
        if automaker_id not in AUTOMAKER_IDS:
            raise KeyError(f"automaker not found: {automaker_id}")
        world = self._runtime(experiment_id).world
        return {
            "schema_version": "automaker-quarter-detail-v1",
            "experiment_id": experiment_id,
            "automaker_id": automaker_id,
            "profile": self.m29.automaker_profiles[automaker_id].model_dump(mode="json"),
            "persona": self.automaker_personas[automaker_id].model_dump(mode="json"),
            "branches": {
                role: {
                    "latest_action": branch.latest_automaker_actions.get(automaker_id).model_dump(
                        mode="json"
                    )
                    if automaker_id in branch.latest_automaker_actions
                    else None,
                    "state": branch.automaker_states.get(automaker_id).model_dump(mode="json")
                    if automaker_id in branch.automaker_states
                    else None,
                    "decisions": [
                        item.model_dump(mode="json")
                        for item in branch.decisions
                        if item.agent_id == automaker_id
                    ],
                    "sessions": [
                        item.model_dump(mode="json")
                        for item in branch.sessions
                        if automaker_id in item.participant_ids
                    ],
                }
                for role, branch in world.branches.items()
            },
        }

    async def get_audit(self, experiment_id: str, *, limit: int = 100) -> dict[str, object]:
        world = self._runtime(experiment_id).world
        records = [
            {
                "record_id": f"audit:{decision.decision_id}",
                "branch_id": decision.branch_id,
                "tick": decision.tick.value,
                "wave": decision.wave.value,
                "actor_kind": decision.agent_kind.value,
                "actor_id": decision.agent_id,
                "fallback_used": decision.fallback_used,
                "evidence_refs": decision.evidence_refs,
                "record_hash": canonical_hash(decision),
            }
            for branch in world.branches.values()
            for decision in branch.decisions
        ]
        return {
            "schema_version": "audit-page-v1",
            "experiment_id": experiment_id,
            "records": records[-limit:],
            "total": len(records),
        }

    async def get_evidence(self, experiment_id: str, evidence_id: str) -> dict[str, object]:
        world = self._runtime(experiment_id).world
        prefix, _, value = evidence_id.partition(":")
        if prefix == "inbox":
            item = next(
                (
                    inbox
                    for branch in world.branches.values()
                    for inbox in branch.inboxes
                    if inbox.inbox_id == value
                ),
                None,
            )
        elif prefix == "message":
            item = next(
                (
                    message
                    for branch in world.branches.values()
                    for message in branch.messages
                    if message.message_id == value
                ),
                None,
            )
        elif prefix == "session":
            item = next(
                (
                    session
                    for branch in world.branches.values()
                    for session in branch.sessions
                    if session.session_id == value
                ),
                None,
            )
        elif prefix == "checkpoint":
            item = next(
                (
                    checkpoint
                    for branch in world.branches.values()
                    for checkpoint in branch.checkpoints.values()
                    if checkpoint.checkpoint_id == value
                ),
                None,
            )
        else:
            item = None
        if item is None:
            raise KeyError(f"evidence not found: {evidence_id}")
        return {
            "schema_version": "evidence-v1",
            "evidence_id": evidence_id,
            "payload": item.model_dump(mode="json"),
            "source_hash": canonical_hash(item),
        }
