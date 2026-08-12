import asyncio
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from simulation.agents import AutomakerAgent, ProvinceAgent, StateCouncilAgent
from simulation.catalog import event_scenario_catalog
from simulation.data import (
    NetworkEdge,
    load_automaker_profiles,
    load_interaction_network,
    load_network,
    load_profiles,
    load_province_personas,
    load_scenario_policy,
)
from simulation.envs import ChinaPolicyEnv
from simulation.llm.base import LLMProvider
from simulation.llm.fake_provider import FakeLLMProvider, policy_diff
from simulation.models.audit import (
    AgentInvocationTrace,
    AuditActorKind,
    AuditListResponse,
    AuditOutcome,
    AuditRecord,
    DecisionGateTrace,
    MechanismExplanation,
    ProviderAttemptTrace,
)
from simulation.models.audit import (
    MechanismTerm as AuditMechanismTerm,
)
from simulation.models.automaker import AutomakerAction
from simulation.models.central import CentralIntervention
from simulation.models.common import (
    ApprovalStatus,
    BranchKind,
    ComparisonMode,
    EventIntensity,
    EventTemplateId,
    ExperimentStatus,
    Phase,
    PolicyStatus,
    RunMode,
)
from simulation.models.event import EventEnvelope
from simulation.models.experiment import Branch, Checkpoint, ExperimentConfig, ExperimentRecord
from simulation.models.policy import PolicySchema
from simulation.models.province import ProvinceAction, ProvinceDecisionPersona, ProvinceProfile
from simulation.models.scenario import (
    EventScenario,
    EventScenarioSelection,
    ProvinceEventResponse,
    ProvinceEventSignal,
)
from simulation.models.world import (
    AutomakerDetail,
    ComparisonResult,
    ProvinceAgentBranchSnapshot,
    ProvinceAgentDetail,
    ProvinceAutomakerEvidence,
    ProvinceNeighbor,
    VersionInfo,
    WorldState,
)
from simulation.services.checkpoint import CheckpointService
from simulation.services.comparison import ComparisonService
from simulation.services.replay import ReplayService, canonical_hash, sanitize_for_audit


@dataclass
class ExperimentRuntime:
    record: ExperimentRecord
    worlds: dict[str, WorldState]
    events: list[EventEnvelope] = field(default_factory=list)
    event_counter: int = 0
    checkpoint: Checkpoint | None = None
    branches: dict[str, Branch] = field(default_factory=dict)
    approved_interventions: dict[str, CentralIntervention] = field(default_factory=dict)
    comparison: ComparisonResult | None = None
    intervention_rejected: bool = False
    approved_event_scenario: EventScenario | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    condition: asyncio.Condition = field(default_factory=asyncio.Condition)


class AsyncioSimulationAdapter:
    """In-process V3 runtime with annual phases, approval gates and same-source branches."""

    def __init__(
        self,
        provider: LLMProvider,
        *,
        runtime_dir: Path | str = Path("runtime"),
        profiles: dict[str, ProvinceProfile] | None = None,
        personas: dict[str, ProvinceDecisionPersona] | None = None,
        network: dict[str, list[NetworkEdge]] | None = None,
        agent_timeout_seconds: float = 12,
    ):
        self.provider = provider
        self.fallback_provider = FakeLLMProvider()
        self.profiles = profiles or load_profiles()
        self.personas = personas or load_province_personas()
        self.network = network or load_network()
        self.interaction_network = load_interaction_network()
        self.coordination_eligible_pairs = {
            tuple(sorted((edge.source_province_code, edge.target_province_code)))
            for edge in self.interaction_network.edges
            if edge.coordinate_eligible
        }
        self.automaker_profiles = load_automaker_profiles()
        self.default_policy = load_scenario_policy()
        self.agent_timeout_seconds = agent_timeout_seconds
        self.state_council = StateCouncilAgent(provider)
        self.province_agents = {
            code: ProvinceAgent(profile, provider) for code, profile in self.profiles.items()
        }
        self.automaker_agents = {
            key: AutomakerAgent(profile, provider)
            for key, profile in self.automaker_profiles.items()
        }
        self.checkpoints = CheckpointService()
        self.comparisons = ComparisonService()
        self.replay = ReplayService(Path(runtime_dir))
        self.runtimes: dict[str, ExperimentRuntime] = {}

    def _runtime(self, experiment_id: str) -> ExperimentRuntime:
        try:
            return self.runtimes[experiment_id]
        except KeyError as exc:
            raise KeyError(f"experiment not found: {experiment_id}") from exc

    async def _emit(
        self,
        runtime: ExperimentRuntime,
        event_type: str,
        branch_id: str,
        phase: Phase,
        payload: dict[str, object] | None = None,
    ) -> EventEnvelope:
        runtime.event_counter += 1
        event = EventEnvelope(
            event_id=f"evt_{runtime.event_counter:08d}",
            type=event_type,
            experiment_id=runtime.record.experiment_id,
            branch_id=branch_id,
            phase=phase,
            payload=sanitize_for_audit(payload or {}),
        )
        runtime.events.append(event)
        self.replay.append(event)
        async with runtime.condition:
            runtime.condition.notify_all()
        return event

    def _audit_agent(
        self,
        runtime: ExperimentRuntime,
        branch_id: str,
        phase: Phase,
        actor_kind: AuditActorKind,
        actor_id: str,
        operation: str,
        input_payload: object,
        output: object,
        latency_ms: float,
    ) -> AuditRecord:
        output_json = sanitize_for_audit(output)
        output_ids = [
            str(getattr(output, field))
            for field in (
                "directive_id",
                "action_id",
                "feedback_id",
                "proposal_id",
                "review_id",
                "signal_id",
                "response_id",
                "scenario_id",
            )
            if getattr(output, field, None)
        ]
        run_mode = str(getattr(output, "run_mode", getattr(self.provider, "run_mode", "live")))
        payload = AgentInvocationTrace(
            actor_kind=actor_kind,
            actor_id=actor_id,
            operation=operation,
            run_mode=run_mode,
            model=runtime.record.config.model_version,
            prompt_version=runtime.record.config.prompt_version,
            response_schema=str(getattr(output, "schema_version", "unknown")),
            input_hash=canonical_hash(input_payload),
            input_snapshot=sanitize_for_audit(input_payload),
            attempts=[ProviderAttemptTrace(attempt=1, status="succeeded", latency_ms=latency_ms)],
            latency_ms=latency_ms,
            outcome=AuditOutcome.SUCCEEDED,
            output_ids=output_ids,
            output_hash=canonical_hash(output_json),
            output_snapshot=output_json,
        )
        return self.replay.append_audit(
            experiment_id=runtime.record.experiment_id,
            branch_id=branch_id,
            phase=phase,
            payload=payload,
        )

    def _audit_decision(
        self,
        runtime: ExperimentRuntime,
        *,
        branch_id: str,
        phase: Phase,
        operation: str,
        object_ids: list[str],
        details: dict[str, object],
        outcome: AuditOutcome = AuditOutcome.SUCCEEDED,
    ) -> AuditRecord:
        return self.replay.append_audit(
            experiment_id=runtime.record.experiment_id,
            branch_id=branch_id,
            phase=phase,
            payload=DecisionGateTrace(
                actor_kind=AuditActorKind.USER,
                actor_id="user",
                operation=operation,
                outcome=outcome,
                object_ids=object_ids,
                details=sanitize_for_audit(details),
            ),
        )

    def _audit_mechanisms(
        self,
        runtime: ExperimentRuntime,
        world: WorldState,
    ) -> None:
        items = []
        for contribution_id, contribution in sorted(world.contributions.items()):
            province_code = contribution.province_code or contribution_id
            explanation = MechanismExplanation(
                explanation_id=(
                    f"mechanism_{world.branch_id}_{world.phase.value}_{contribution_id}"
                ),
                scope="province",
                subject_id=province_code,
                metric=contribution.target_metric,
                formula_id="province-nev-development-index",
                formula_version=contribution.formula_version,
                source_refs=contribution.evidence_refs,
                terms=[
                    AuditMechanismTerm(
                        name=term.name,
                        input_value=term.input_value,
                        coefficient=term.coefficient,
                        contribution=term.contribution,
                        source_ref=term.source_ref,
                    )
                    for term in contribution.terms
                ],
                raw_value=contribution.raw_value,
                clamp_adjustment=contribution.clamp_adjustment,
                final_value=contribution.final_value,
                residual=contribution.conservation_residual,
            )
            items.append((explanation, []))
        self.replay.append_audits(
            experiment_id=runtime.record.experiment_id,
            branch_id=world.branch_id,
            phase=world.phase,
            items=items,
        )

    async def initialize(self, config: ExperimentConfig) -> WorldState:
        experiment_id = f"exp_{uuid4().hex[:14]}"
        started = perf_counter()
        directive = await self.state_council.draft_directive(config, self.default_policy)
        env = ChinaPolicyEnv(
            profiles=self.profiles,
            automaker_profiles=self.automaker_profiles,
            policy=directive.policy,
        )
        world = WorldState(
            experiment_id=experiment_id,
            policy=directive.policy.model_copy(deep=True),
            directive=directive,
            province_profiles=deepcopy(self.profiles),
            province_personas=deepcopy(self.personas),
            province_states=deepcopy(env.province_states),
            automaker_profiles=deepcopy(self.automaker_profiles),
            automaker_states=deepcopy(env.automaker_states),
            run_mode=config.run_mode,
            comparison_mode=config.comparison_mode,
            versions=VersionInfo(
                data=config.data_version,
                mechanism=config.mechanism_version,
                prompt=config.prompt_version,
                model=config.model_version,
            ),
            seed=config.seed,
        )
        record = ExperimentRecord(experiment_id=experiment_id, config=config, directive=directive)
        runtime = ExperimentRuntime(record=record, worlds={"control": world})
        self.runtimes[experiment_id] = runtime
        audit = self._audit_agent(
            runtime,
            "control",
            Phase.SETUP,
            AuditActorKind.CENTRAL_AGENT,
            "central",
            "draft_directive",
            {"config": config, "default_policy": self.default_policy},
            directive,
            round((perf_counter() - started) * 1000, 3),
        )
        await self._emit(
            runtime, "experiment.started", "control", Phase.SETUP, {"status": world.status.value}
        )
        await self._emit(
            runtime,
            "central.directive.completed",
            "control",
            Phase.SETUP,
            {"directive_id": directive.directive_id, "audit_record_id": audit.record_id},
        )
        for code, persona in sorted(self.personas.items()):
            await self._emit(
                runtime,
                "province.persona.ready",
                "control",
                Phase.SETUP,
                {"province_code": code, "primary_type": persona.primary_type.value},
            )
        self.replay.write_state(world)
        return world.model_copy(deep=True)

    async def approve_directive(
        self, experiment_id: str, policy: PolicySchema | None = None
    ) -> WorldState:
        runtime = self._runtime(experiment_id)
        async with runtime.lock:
            world = runtime.worlds["control"]
            if world.status is not ExperimentStatus.AWAITING_APPROVAL:
                raise ValueError("directive is not awaiting approval")
            approved = (policy or world.policy).model_copy(
                update={"status": PolicyStatus.APPROVED}, deep=True
            )
            world = world.model_copy(deep=True)
            world.policy = approved
            world.directive = world.directive.model_copy(
                update={"policy": approved, "approval_status": ApprovalStatus.APPROVED}, deep=True
            )
            world.status = ExperimentStatus.READY
            runtime.worlds["control"] = world
            runtime.record.status = ExperimentStatus.READY
            runtime.record.directive = world.directive
            audit = self._audit_decision(
                runtime,
                branch_id="control",
                phase=Phase.SETUP,
                operation="approve_directive",
                object_ids=[world.directive.directive_id, approved.policy_id],
                details={"policy": approved},
            )
            await self._emit(
                runtime,
                "central.directive.approved",
                "control",
                Phase.SETUP,
                {"approved_by": "user", "audit_record_id": audit.record_id},
            )
            self.replay.write_state(world)
            return world.model_copy(deep=True)

    @staticmethod
    def _expected_next(current: Phase) -> Phase | None:
        phases = list(Phase)
        index = phases.index(current)
        return phases[index + 1] if index + 1 < len(phases) else None

    async def _province_actions(
        self, runtime: ExperimentRuntime, world: WorldState, phase: Phase
    ) -> dict[str, ProvinceAction]:
        previous = {
            code: (world.province_action_lineage.get(code) or [None])[-1] for code in self.profiles
        }

        async def call(code: str) -> ProvinceAction:
            started = perf_counter()
            result = await asyncio.wait_for(
                self.province_agents[code].decide(
                    persona=world.province_personas[code],
                    state=world.province_states[code],
                    policy=world.policy,
                    phase=phase,
                    related=self.network[code],
                    neighbor_actions={},
                    previous_action=previous[code],
                    feedback=world.province_feedback.get(code),
                    seed=world.seed,
                    prompt_version=world.versions.prompt,
                    model_version=world.versions.model,
                ),
                timeout=self.agent_timeout_seconds,
            )
            audit = self._audit_agent(
                runtime,
                world.branch_id,
                phase,
                AuditActorKind.PROVINCE_AGENT,
                code,
                "decide",
                {"policy": world.policy, "previous": previous[code]},
                result,
                round((perf_counter() - started) * 1000, 3),
            )
            await self._emit(
                runtime,
                "province.decision.completed",
                world.branch_id,
                phase,
                {
                    "province_code": code,
                    "action_id": result.action_id,
                    "audit_record_id": audit.record_id,
                },
            )
            return result

        results = await asyncio.gather(*(call(code) for code in sorted(self.profiles)))
        return {action.province_code: action for action in results}

    async def _automaker_actions(
        self, runtime: ExperimentRuntime, world: WorldState, phase: Phase
    ) -> dict[str, AutomakerAction]:
        previous = {
            key: (world.automaker_action_lineage.get(key) or [None])[-1]
            for key in self.automaker_profiles
        }

        async def call(automaker_id: str) -> AutomakerAction:
            started = perf_counter()
            result = await asyncio.wait_for(
                self.automaker_agents[automaker_id].decide(
                    state=world.automaker_states[automaker_id],
                    province_profiles=world.province_profiles,
                    province_actions=world.province_actions,
                    policy=world.policy,
                    phase=phase,
                    previous_action=previous[automaker_id],
                    seed=world.seed,
                    prompt_version=world.versions.prompt,
                    model_version=world.versions.model,
                ),
                timeout=self.agent_timeout_seconds,
            )
            audit = self._audit_agent(
                runtime,
                world.branch_id,
                phase,
                AuditActorKind.AUTOMAKER_AGENT,
                automaker_id,
                "decide",
                {"policy": world.policy, "previous": previous[automaker_id]},
                result,
                round((perf_counter() - started) * 1000, 3),
            )
            await self._emit(
                runtime,
                "automaker.decision.completed",
                world.branch_id,
                phase,
                {
                    "automaker_id": automaker_id,
                    "action_id": result.action_id,
                    "audit_record_id": audit.record_id,
                },
            )
            return result

        results = await asyncio.gather(*(call(key) for key in sorted(self.automaker_profiles)))
        return {action.automaker_id: action for action in results}

    async def _province_feedback(self, runtime: ExperimentRuntime, world: WorldState) -> None:
        async def call(code: str):
            started = perf_counter()
            result = await asyncio.wait_for(
                self.province_agents[code].feedback(
                    persona=world.province_personas[code],
                    state=world.province_states[code],
                    current_action=world.province_actions[code],
                    automaker_actions=world.automaker_actions,
                    policy=world.policy,
                    seed=world.seed,
                    prompt_version=world.versions.prompt,
                    model_version=world.versions.model,
                ),
                timeout=self.agent_timeout_seconds,
            )
            audit = self._audit_agent(
                runtime,
                world.branch_id,
                Phase.Y1_Q4,
                AuditActorKind.PROVINCE_AGENT,
                code,
                "annual_feedback",
                {"state": world.province_states[code]},
                result,
                round((perf_counter() - started) * 1000, 3),
            )
            await self._emit(
                runtime,
                "province.feedback.completed",
                world.branch_id,
                Phase.Y1_Q4,
                {
                    "province_code": code,
                    "feedback_id": result.feedback_id,
                    "audit_record_id": audit.record_id,
                },
            )
            return result

        feedback = await asyncio.gather(*(call(code) for code in sorted(self.profiles)))
        world.province_feedback = {item.province_code: item for item in feedback}
        for code, item in world.province_feedback.items():
            world.province_states[code] = world.province_states[code].model_copy(
                update={"last_feedback_id": item.feedback_id}
            )

    async def _province_event_interactions(
        self,
        runtime: ExperimentRuntime,
        world: WorldState,
        scenario: EventScenario,
    ) -> None:
        env = ChinaPolicyEnv(
            profiles=self.profiles,
            automaker_profiles=self.automaker_profiles,
            policy=world.policy,
        )
        exposures = env.event_exposure(scenario)

        async def signal_call(code: str) -> ProvinceEventSignal:
            started = perf_counter()
            try:
                result = await asyncio.wait_for(
                    self.province_agents[code].publish_event_signal(
                        persona=world.province_personas[code],
                        state=world.province_states[code],
                        current_action=world.province_actions[code],
                        scenario=scenario,
                        exposure=exposures[code],
                        related=self.network[code],
                        seed=world.seed,
                        prompt_version=world.versions.prompt,
                        model_version=world.versions.model,
                    ),
                    timeout=self.agent_timeout_seconds,
                )
            except Exception as error:
                result = await self.fallback_provider.generate_province_event_signal(
                    profile=self.profiles[code],
                    persona=world.province_personas[code],
                    state=world.province_states[code],
                    current_action=world.province_actions[code],
                    scenario=scenario,
                    exposure=exposures[code],
                    related=self.network[code],
                    seed=world.seed,
                    prompt_version=world.versions.prompt,
                    model_version=world.versions.model,
                )
                result = result.model_copy(
                    update={
                        "run_mode": RunMode.FALLBACK,
                        "fallback_used": True,
                        "fallback_reason": type(error).__name__,
                    }
                )
            audit = self._audit_agent(
                runtime,
                world.branch_id,
                Phase.Y2_Q3,
                AuditActorKind.PROVINCE_AGENT,
                code,
                "publish_event_signal",
                {"scenario": scenario, "exposure": exposures[code]},
                result,
                round((perf_counter() - started) * 1000, 3),
            )
            await self._emit(
                runtime,
                "province.event_signal.fallback"
                if result.fallback_used
                else "province.event_signal.completed",
                world.branch_id,
                Phase.Y2_Q3,
                {
                    "province_code": code,
                    "signal_id": result.signal_id,
                    "audit_record_id": audit.record_id,
                },
            )
            return result

        signal_results = await asyncio.gather(
            *(signal_call(code) for code in sorted(self.profiles))
        )
        signals = {item.province_code: item for item in signal_results}

        async def response_call(code: str) -> ProvinceEventResponse:
            started = perf_counter()
            allowed_codes = [edge.target for edge in self.network[code]]
            peer_signals = {peer: signals[peer] for peer in allowed_codes}
            try:
                result = await asyncio.wait_for(
                    self.province_agents[code].respond_to_event(
                        persona=world.province_personas[code],
                        state=world.province_states[code],
                        current_action=world.province_actions[code],
                        scenario=scenario,
                        own_signal=signals[code],
                        peer_signals=peer_signals,
                        related=self.network[code],
                        seed=world.seed,
                        prompt_version=world.versions.prompt,
                        model_version=world.versions.model,
                    ),
                    timeout=self.agent_timeout_seconds,
                )
            except Exception as error:
                result = await self.fallback_provider.generate_province_event_response(
                    profile=self.profiles[code],
                    persona=world.province_personas[code],
                    state=world.province_states[code],
                    current_action=world.province_actions[code],
                    scenario=scenario,
                    own_signal=signals[code],
                    peer_signals=peer_signals,
                    related=self.network[code],
                    seed=world.seed,
                    prompt_version=world.versions.prompt,
                    model_version=world.versions.model,
                )
                result = result.model_copy(
                    update={
                        "run_mode": RunMode.FALLBACK,
                        "fallback_used": True,
                        "fallback_reason": type(error).__name__,
                    }
                )
            audit = self._audit_agent(
                runtime,
                world.branch_id,
                Phase.Y2_Q3,
                AuditActorKind.PROVINCE_AGENT,
                code,
                "respond_to_event",
                {"scenario": scenario, "signal": signals[code], "peers": peer_signals},
                result,
                round((perf_counter() - started) * 1000, 3),
            )
            await self._emit(
                runtime,
                "province.event_response.fallback"
                if result.fallback_used
                else "province.event_response.completed",
                world.branch_id,
                Phase.Y2_Q3,
                {
                    "province_code": code,
                    "response_id": result.response_id,
                    "audit_record_id": audit.record_id,
                },
            )
            return result

        response_results = await asyncio.gather(
            *(response_call(code) for code in sorted(self.profiles))
        )
        responses = {item.province_code: item for item in response_results}
        matches = env.match_coordination(
            scenario,
            responses,
            coordination_eligible_pairs=self.coordination_eligible_pairs,
        )
        world.event_exposure_by_province = exposures
        world.province_event_signals = signals
        world.province_event_responses = responses
        world.coordination_matches = matches
        world.fallback_event_provinces = sorted(
            code
            for code in self.profiles
            if signals[code].fallback_used or responses[code].fallback_used
        )
        for match in matches:
            await self._emit(
                runtime,
                f"province.coordination.{match.status.value}",
                world.branch_id,
                Phase.Y2_Q3,
                {
                    "match_id": match.match_id,
                    "left": match.left_province_code,
                    "right": match.right_province_code,
                    "contribution": match.contribution,
                },
            )

    async def run_phase(
        self, experiment_id: str, phase: Phase, branch_id: str = "control"
    ) -> WorldState:
        runtime = self._runtime(experiment_id)
        async with runtime.lock:
            try:
                current = runtime.worlds[branch_id]
            except KeyError as exc:
                raise KeyError(f"branch not found: {branch_id}") from exc
            if current.status in {
                ExperimentStatus.AWAITING_APPROVAL,
                ExperimentStatus.AWAITING_INTERVENTION,
                ExperimentStatus.AWAITING_EVENT,
            }:
                if current.status is ExperimentStatus.AWAITING_EVENT:
                    raise PermissionError("EVENT_APPROVAL_REQUIRED")
                raise PermissionError("human approval is required before running the next phase")
            if self._expected_next(current.phase) is not phase:
                raise ValueError(
                    f"illegal phase transition: {current.phase.value} -> {phase.value}"
                )
            world = current.model_copy(deep=True)
            world.status = ExperimentStatus.RUNNING
            if phase in {Phase.Y1_Q1, Phase.Y2_Q1}:
                actions = await self._province_actions(runtime, world, phase)
                world.province_actions = actions
                world.fallback_provinces = sorted(
                    code for code, action in actions.items() if action.fallback_used
                )
                for code, action in actions.items():
                    world.province_action_lineage.setdefault(code, []).append(action)
            elif phase in {Phase.Y1_Q2, Phase.Y2_Q2}:
                actions = await self._automaker_actions(runtime, world, phase)
                world.automaker_actions = actions
                world.fallback_automakers = sorted(
                    automaker_id for automaker_id, action in actions.items() if action.fallback_used
                )
                for automaker_id, action in actions.items():
                    world.automaker_action_lineage.setdefault(automaker_id, []).append(action)
            elif phase is Phase.Y2_Q3:
                if world.approved_event_scenario is None:
                    if not (runtime.intervention_rejected and len(runtime.worlds) == 1):
                        raise PermissionError("EVENT_APPROVAL_REQUIRED")
                elif world.event_applied:
                    await self._emit(
                        runtime,
                        "scenario.activated",
                        branch_id,
                        phase,
                        {"scenario_id": world.approved_event_scenario.scenario_id},
                    )
                    await self._province_event_interactions(
                        runtime, world, world.approved_event_scenario
                    )
                await self._emit(
                    runtime,
                    "environment.event_propagated",
                    branch_id,
                    phase,
                    {
                        "scenario_id": (
                            world.approved_event_scenario.scenario_id
                            if world.approved_event_scenario
                            else None
                        ),
                        "applied": world.event_applied,
                    },
                )
            elif phase in {Phase.Y1_Q4, Phase.Y2_Q4}:
                env = ChinaPolicyEnv(
                    profiles=self.profiles,
                    automaker_profiles=self.automaker_profiles,
                    policy=world.policy,
                )
                previous_states = current.province_states if phase is Phase.Y2_Q4 else None
                settlement = env.settle_year(
                    policy=world.policy,
                    province_actions=world.province_actions,
                    automaker_actions=world.automaker_actions,
                    phase=phase,
                    previous_province_states=previous_states,
                    event_scenario=(world.approved_event_scenario if world.event_applied else None),
                    event_responses=(
                        world.province_event_responses if world.event_applied else None
                    ),
                    coordination_matches=(
                        world.coordination_matches if world.event_applied else None
                    ),
                )
                world.province_states = settlement.province_states
                world.automaker_states = settlement.automaker_states
                world.national_metrics = settlement.national_metrics
                world.contributions = settlement.mechanism_contributions
                world.fixed_variable_thresholds = {
                    code: item.model_dump(mode="json")
                    for code, item in settlement.fixed_variable_thresholds.items()
                }
                if phase is Phase.Y1_Q4:
                    await self._province_feedback(runtime, world)
            elif phase is Phase.YEAR1_REVIEW:
                world.phase = phase
                world.status = ExperimentStatus.RUNNING
                runtime.worlds[branch_id] = world
                runtime.checkpoint = self.checkpoints.create(world)
                started = perf_counter()
                proposals = await self.state_council.analyze_and_propose(
                    policy=world.policy,
                    metrics=world.national_metrics,
                    states=world.province_states,
                    feedback=world.province_feedback,
                    automaker_actions=world.automaker_actions,
                )
                world.intervention_proposals = proposals
                world.status = ExperimentStatus.AWAITING_INTERVENTION
                for proposal in proposals:
                    audit = self._audit_agent(
                        runtime,
                        branch_id,
                        phase,
                        AuditActorKind.CENTRAL_AGENT,
                        "central",
                        "propose_intervention",
                        {"metrics": world.national_metrics},
                        proposal,
                        round((perf_counter() - started) * 1000, 3),
                    )
                    await self._emit(
                        runtime,
                        "central.intervention.proposed",
                        branch_id,
                        phase,
                        {"proposal_id": proposal.proposal_id, "audit_record_id": audit.record_id},
                    )
                runtime.record.status = ExperimentStatus.AWAITING_INTERVENTION
                runtime.record.current_phase = phase
                runtime.worlds[branch_id] = world
                self.replay.write_state(world)
                return world.model_copy(deep=True)
            elif phase is Phase.COMPLETE:
                if runtime.intervention_rejected:
                    world.central_review = await self.state_council.review(world)
                    world.status = ExperimentStatus.COMPLETED
                else:
                    if not runtime.comparison:
                        await self.compare(experiment_id)
                    world.central_review = runtime.comparison.central_review
                    world.status = ExperimentStatus.COMPLETED
            world.phase = phase
            if phase in {Phase.Y1_Q4, Phase.Y2_Q4}:
                self._audit_mechanisms(runtime, world)
            if phase not in {Phase.COMPLETE}:
                world.status = ExperimentStatus.READY
            runtime.worlds[branch_id] = world
            if (
                phase is Phase.Y2_Q2
                and len(runtime.worlds) == 2
                and all(item.phase.order >= Phase.Y2_Q2.order for item in runtime.worlds.values())
            ):
                for candidate in runtime.worlds.values():
                    candidate.status = ExperimentStatus.AWAITING_EVENT
                world = runtime.worlds[branch_id]
                runtime.record.status = ExperimentStatus.AWAITING_EVENT
                await self._emit(
                    runtime,
                    "scenario.awaiting_approval",
                    branch_id,
                    phase,
                    {"comparison_mode": world.comparison_mode.value},
                )
            runtime.record.current_phase = max(
                (item.phase for item in runtime.worlds.values()), key=lambda item: item.order
            )
            runtime.record.status = world.status
            await self._emit(
                runtime, "phase.completed", branch_id, phase, {"status": world.status.value}
            )
            self.replay.write_state(world)
            return world.model_copy(deep=True)

    async def run_to_phase(
        self, experiment_id: str, phase: Phase, branch_id: str = "control"
    ) -> WorldState:
        world = await self.get_state(experiment_id, branch_id)
        while world.phase.order < phase.order:
            next_phase = self._expected_next(world.phase)
            if next_phase is None:
                break
            world = await self.run_phase(experiment_id, next_phase, branch_id)
        return world

    async def create_checkpoint(self, experiment_id: str, phase: Phase) -> Checkpoint:
        runtime = self._runtime(experiment_id)
        if phase is not Phase.YEAR1_REVIEW or runtime.checkpoint is None:
            raise ValueError("only the immutable year-one review checkpoint is available")
        return runtime.checkpoint.model_copy(deep=True)

    async def approve_intervention(
        self,
        experiment_id: str,
        proposal_id: str,
        policy: PolicySchema | None = None,
    ) -> CentralIntervention:
        runtime = self._runtime(experiment_id)
        world = runtime.worlds["control"]
        if world.status is not ExperimentStatus.AWAITING_INTERVENTION or runtime.checkpoint is None:
            raise PermissionError("intervention approval is not available")
        proposal = next(
            (item for item in world.intervention_proposals if item.proposal_id == proposal_id), None
        )
        if proposal is None:
            raise KeyError(f"intervention proposal not found: {proposal_id}")
        approved_policy = (policy or proposal.proposed_policy).model_copy(
            update={"status": PolicyStatus.APPROVED}, deep=True
        )
        changes = policy_diff(world.policy, approved_policy)
        if not changes:
            raise ValueError("approved intervention must change at least one regional share")
        intervention = CentralIntervention(
            intervention_id=f"int_{uuid4().hex[:12]}",
            approved_policy=approved_policy,
            approved_changes=changes,
            approved_at=datetime.now(UTC),
        )
        runtime.approved_interventions[intervention.intervention_id] = intervention
        world.approved_intervention = intervention
        world.intervention_decision = "approved"
        audit = self._audit_decision(
            runtime,
            branch_id="control",
            phase=Phase.YEAR1_REVIEW,
            operation="approve_intervention",
            object_ids=[proposal_id, intervention.intervention_id],
            details={"approved_changes": changes},
        )
        await self._emit(
            runtime,
            "central.intervention.approved",
            "control",
            Phase.YEAR1_REVIEW,
            {
                "intervention_id": intervention.intervention_id,
                "audit_record_id": audit.record_id,
            },
        )
        return intervention.model_copy(deep=True)

    async def reject_intervention(self, experiment_id: str, proposal_id: str) -> WorldState:
        runtime = self._runtime(experiment_id)
        world = runtime.worlds["control"]
        if not any(item.proposal_id == proposal_id for item in world.intervention_proposals):
            raise KeyError(f"intervention proposal not found: {proposal_id}")
        if runtime.checkpoint is None:
            raise ValueError("year-one checkpoint not found")
        control = self.checkpoints.restore(runtime.checkpoint)
        control.parent_checkpoint_id = runtime.checkpoint.checkpoint_id
        control.status = ExperimentStatus.READY
        control.intervention_decision = "rejected"
        runtime.worlds["control"] = control
        runtime.intervention_rejected = True
        audit = self._audit_decision(
            runtime,
            branch_id="control",
            phase=Phase.YEAR1_REVIEW,
            operation="reject_intervention",
            object_ids=[proposal_id],
            details={"decision": "rejected"},
            outcome=AuditOutcome.REJECTED,
        )
        await self._emit(
            runtime,
            "central.intervention.rejected",
            "control",
            Phase.YEAR1_REVIEW,
            {"proposal_id": proposal_id, "audit_record_id": audit.record_id},
        )
        return control.model_copy(deep=True)

    async def create_approved_branch(self, experiment_id: str, intervention_id: str) -> Branch:
        runtime = self._runtime(experiment_id)
        if runtime.record.config.comparison_mode is not ComparisonMode.POLICY_INTERVENTION:
            raise ValueError("event counterfactual experiments do not accept policy interventions")
        if runtime.checkpoint is None:
            raise ValueError("year-one checkpoint not found")
        try:
            intervention = runtime.approved_interventions[intervention_id]
        except KeyError as exc:
            raise PermissionError("intervention must be approved before branch creation") from exc
        control = self.checkpoints.restore(runtime.checkpoint)
        control.parent_checkpoint_id = runtime.checkpoint.checkpoint_id
        control.status = ExperimentStatus.READY
        control.branch_id = "control"
        control.branch_kind = BranchKind.CONTROL
        control.approved_intervention = intervention.model_copy(deep=True)
        control.intervention_decision = "approved"
        treatment_id = f"br_treatment_{uuid4().hex[:12]}"
        treatment = self.checkpoints.restore(runtime.checkpoint)
        treatment.parent_checkpoint_id = runtime.checkpoint.checkpoint_id
        treatment.branch_id = treatment_id
        treatment.branch_kind = BranchKind.TREATMENT
        treatment.policy = intervention.approved_policy.model_copy(deep=True)
        treatment.approved_intervention = intervention
        treatment.intervention_decision = "approved"
        treatment.status = ExperimentStatus.READY
        branch = Branch(
            branch_id=treatment_id,
            experiment_id=experiment_id,
            kind=BranchKind.TREATMENT,
            comparison_mode=ComparisonMode.POLICY_INTERVENTION,
            parent_checkpoint_id=runtime.checkpoint.checkpoint_id,
            intervention=intervention,
        )
        runtime.worlds = {"control": control, treatment_id: treatment}
        runtime.branches["control"] = Branch(
            branch_id="control",
            experiment_id=experiment_id,
            kind=BranchKind.CONTROL,
            comparison_mode=ComparisonMode.POLICY_INTERVENTION,
            parent_checkpoint_id=runtime.checkpoint.checkpoint_id,
        )
        runtime.branches[treatment_id] = branch
        await self._emit(
            runtime,
            "branch.created",
            treatment_id,
            Phase.YEAR1_REVIEW,
            {"parent_checkpoint_id": runtime.checkpoint.checkpoint_id},
        )
        return branch.model_copy(deep=True)

    async def create_event_counterfactual_branches(self, experiment_id: str) -> Branch:
        runtime = self._runtime(experiment_id)
        if runtime.record.config.comparison_mode is not ComparisonMode.EVENT_COUNTERFACTUAL:
            raise ValueError("only event counterfactual experiments use same-policy branches")
        if runtime.checkpoint is None:
            raise ValueError("year-one checkpoint not found")
        if runtime.branches:
            raise ValueError("branches already created")
        control = self.checkpoints.restore(runtime.checkpoint)
        control.parent_checkpoint_id = runtime.checkpoint.checkpoint_id
        control.status = ExperimentStatus.READY
        control.branch_id = "control"
        control.branch_kind = BranchKind.CONTROL
        control.comparison_mode = ComparisonMode.EVENT_COUNTERFACTUAL
        control.intervention_decision = "event_counterfactual"
        treatment_id = f"br_event_{uuid4().hex[:12]}"
        treatment = self.checkpoints.restore(runtime.checkpoint)
        treatment.parent_checkpoint_id = runtime.checkpoint.checkpoint_id
        treatment.branch_id = treatment_id
        treatment.branch_kind = BranchKind.TREATMENT
        treatment.comparison_mode = ComparisonMode.EVENT_COUNTERFACTUAL
        treatment.intervention_decision = "event_counterfactual"
        treatment.status = ExperimentStatus.READY
        control_branch = Branch(
            branch_id="control",
            experiment_id=experiment_id,
            kind=BranchKind.CONTROL,
            comparison_mode=ComparisonMode.EVENT_COUNTERFACTUAL,
            parent_checkpoint_id=runtime.checkpoint.checkpoint_id,
        )
        branch = Branch(
            branch_id=treatment_id,
            experiment_id=experiment_id,
            kind=BranchKind.TREATMENT,
            comparison_mode=ComparisonMode.EVENT_COUNTERFACTUAL,
            parent_checkpoint_id=runtime.checkpoint.checkpoint_id,
        )
        runtime.worlds = {"control": control, treatment_id: treatment}
        runtime.branches = {"control": control_branch, treatment_id: branch}
        await self._emit(
            runtime,
            "branch.created",
            treatment_id,
            Phase.YEAR1_REVIEW,
            {
                "parent_checkpoint_id": runtime.checkpoint.checkpoint_id,
                "comparison_mode": ComparisonMode.EVENT_COUNTERFACTUAL.value,
            },
        )
        return branch.model_copy(deep=True)

    async def approve_event_scenario(
        self,
        experiment_id: str,
        selection: EventScenarioSelection,
    ) -> EventScenario:
        runtime = self._runtime(experiment_id)
        async with runtime.lock:
            if runtime.approved_event_scenario is not None:
                raise ValueError("event scenario already approved")
            if len(runtime.worlds) != 2 or not all(
                world.phase is Phase.Y2_Q2 and world.status is ExperimentStatus.AWAITING_EVENT
                for world in runtime.worlds.values()
            ):
                raise PermissionError("event approval requires both branches at Y2_Q2")
            template = event_scenario_catalog()[selection.template_id]
            scenario = EventScenario(
                scenario_id=(f"scenario_{selection.template_id.value}_{selection.intensity.value}"),
                template_id=template.template_id,
                family=template.family,
                title=template.title,
                intensity=selection.intensity,
                magnitude=selection.intensity.magnitude,
                target_province_codes=template.target_province_codes,
                provenance_refs=template.provenance_refs,
            )
            if runtime.record.config.comparison_mode is ComparisonMode.POLICY_INTERVENTION:
                application_ids = sorted(runtime.worlds)
            else:
                application_ids = sorted(
                    world.branch_id
                    for world in runtime.worlds.values()
                    if world.branch_kind is BranchKind.TREATMENT
                )
            for world in runtime.worlds.values():
                world.approved_event_scenario = scenario.model_copy(deep=True)
                world.scenario_application_branch_ids = application_ids
                world.event_applied = world.branch_id in application_ids
                world.status = ExperimentStatus.READY
                self.replay.write_state(world)
            runtime.approved_event_scenario = scenario
            runtime.record.status = ExperimentStatus.READY
            audit = self._audit_decision(
                runtime,
                branch_id="control",
                phase=Phase.Y2_Q2,
                operation="approve_event_scenario",
                object_ids=[scenario.scenario_id],
                details={
                    "template_id": scenario.template_id.value,
                    "intensity": scenario.intensity.value,
                    "application_branch_ids": application_ids,
                },
            )
            await self._emit(
                runtime,
                "scenario.approved",
                "control",
                Phase.Y2_Q2,
                {
                    "scenario_id": scenario.scenario_id,
                    "template_id": scenario.template_id.value,
                    "application_branch_ids": application_ids,
                    "approved_by": "user",
                    "audit_record_id": audit.record_id,
                },
            )
            return scenario.model_copy(deep=True)

    async def get_event_scenario(self, experiment_id: str) -> EventScenario | None:
        scenario = self._runtime(experiment_id).approved_event_scenario
        return scenario.model_copy(deep=True) if scenario else None

    async def list_branches(self, experiment_id: str) -> list[Branch]:
        """Return the branch directory needed to restore a refreshed client."""

        runtime = self._runtime(experiment_id)
        return [
            branch.model_copy(deep=True)
            for branch in sorted(runtime.branches.values(), key=lambda item: item.branch_id)
        ]

    async def create_branch(self, checkpoint_id: str, intervention: CentralIntervention) -> Branch:
        for experiment_id, runtime in self.runtimes.items():
            if runtime.checkpoint and runtime.checkpoint.checkpoint_id == checkpoint_id:
                runtime.approved_interventions[intervention.intervention_id] = intervention
                return await self.create_approved_branch(
                    experiment_id, intervention.intervention_id
                )
        raise KeyError(f"checkpoint not found: {checkpoint_id}")

    async def compare(self, experiment_id: str) -> ComparisonResult:
        runtime = self._runtime(experiment_id)
        if runtime.intervention_rejected:
            raise ValueError("COMPARISON_NOT_AVAILABLE: intervention was rejected")
        control = runtime.worlds.get("control")
        treatment = next(
            (
                world
                for world in runtime.worlds.values()
                if world.branch_kind is BranchKind.TREATMENT
            ),
            None,
        )
        if (
            not control
            or not treatment
            or control.phase.order < Phase.Y2_Q4.order
            or treatment.phase.order < Phase.Y2_Q4.order
        ):
            raise ValueError("both branches must complete Y2_Q4 before comparison")
        if runtime.checkpoint is None:
            raise ValueError("year-one checkpoint not found")
        result = self.comparisons.compare(
            checkpoint_id=runtime.checkpoint.checkpoint_id,
            control=control,
            treatment=treatment,
            profiles=self.profiles,
        )
        review = await self.state_council.review(result)
        result.central_review = review
        runtime.comparison = result
        for branch_id in (control.branch_id, treatment.branch_id):
            runtime.worlds[branch_id].central_review = review
        await self._emit(
            runtime,
            "comparison.completed",
            treatment.branch_id,
            Phase.Y2_Q4,
            {"delta_gap": result.delta_gap},
        )
        return result.model_copy(deep=True)

    async def get_state(self, experiment_id: str, branch_id: str = "control") -> WorldState:
        runtime = self._runtime(experiment_id)
        try:
            return runtime.worlds[branch_id].model_copy(deep=True)
        except KeyError as exc:
            raise KeyError(f"branch not found: {branch_id}") from exc

    async def get_record(self, experiment_id: str) -> ExperimentRecord:
        return self._runtime(experiment_id).record.model_copy(deep=True)

    async def get_events(
        self, experiment_id: str, last_event_id: str | None = None
    ) -> list[EventEnvelope]:
        events = self._runtime(experiment_id).events
        if last_event_id is None:
            return [item.model_copy(deep=True) for item in events]
        index = next(
            (index for index, item in enumerate(events) if item.event_id == last_event_id), -1
        )
        return [item.model_copy(deep=True) for item in events[index + 1 :]]

    async def wait_for_events(
        self, experiment_id: str, last_event_id: str | None, timeout_seconds: float = 10
    ) -> list[EventEnvelope]:
        runtime = self._runtime(experiment_id)
        existing = await self.get_events(experiment_id, last_event_id)
        if existing:
            return existing
        try:
            async with runtime.condition:
                await asyncio.wait_for(runtime.condition.wait(), timeout_seconds)
        except TimeoutError:
            return []
        return await self.get_events(experiment_id, last_event_id)

    async def get_replay(self, experiment_id: str) -> list[dict[str, object]]:
        self._runtime(experiment_id)
        return self.replay.read_raw(experiment_id)

    async def get_audit(self, experiment_id: str, **filters: object) -> AuditListResponse:
        self._runtime(experiment_id)
        return self.replay.read_audit(experiment_id, **filters)

    async def get_audit_record(self, experiment_id: str, record_id: str) -> AuditRecord:
        self._runtime(experiment_id)
        return self.replay.get_audit_record(experiment_id, record_id)

    async def get_comparison(self, experiment_id: str) -> ComparisonResult:
        runtime = self._runtime(experiment_id)
        if runtime.comparison is None:
            control = runtime.worlds.get("control")
            treatment = next(
                (
                    world
                    for world in runtime.worlds.values()
                    if world.branch_kind is BranchKind.TREATMENT
                ),
                None,
            )
            if (
                control
                and treatment
                and control.phase.order >= Phase.Y2_Q4.order
                and treatment.phase.order >= Phase.Y2_Q4.order
            ):
                return await self.compare(experiment_id)
            raise ValueError("COMPARISON_NOT_AVAILABLE")
        return runtime.comparison.model_copy(deep=True)

    async def get_province_detail(
        self, experiment_id: str, province_code: str
    ) -> ProvinceAgentDetail:
        if province_code not in self.profiles:
            raise KeyError(f"province not found: {province_code}")
        runtime = self._runtime(experiment_id)
        branches = {}
        for branch_id, world in runtime.worlds.items():
            automakers = []
            for automaker_id, profile in world.automaker_profiles.items():
                action = world.automaker_actions.get(automaker_id)
                if action and any(
                    item.province_code == province_code for item in action.province_market_actions
                ):
                    automakers.append(
                        ProvinceAutomakerEvidence(
                            profile=profile,
                            state=world.automaker_states.get(automaker_id),
                            action=action,
                        )
                    )
            signal = world.province_event_signals.get(province_code)
            response = world.province_event_responses.get(province_code)
            matches = [
                item
                for item in world.coordination_matches
                if province_code in {item.left_province_code, item.right_province_code}
            ]
            contributions = [
                item for item in world.contributions.values() if item.province_code == province_code
            ]
            evidence_refs = [f"profile:{province_code}", f"persona:{province_code}"]
            if world.approved_event_scenario:
                evidence_refs.append(f"scenario:{world.approved_event_scenario.scenario_id}")
            if signal:
                evidence_refs.append(f"interaction:{signal.signal_id}")
            if response:
                evidence_refs.append(f"interaction:{response.response_id}")
            evidence_refs.extend(f"interaction:{item.match_id}" for item in matches)
            branches[world.branch_kind] = ProvinceAgentBranchSnapshot(
                branch_id=branch_id,
                branch_kind=world.branch_kind,
                phase=world.phase,
                state=world.province_states[province_code],
                current_action=world.province_actions.get(province_code),
                action_lineage=world.province_action_lineage.get(province_code, []),
                feedback=world.province_feedback.get(province_code),
                automakers=automakers,
                mechanism_summary={
                    term.name: term.contribution
                    for contribution in contributions
                    for term in contribution.terms
                    if term.name.startswith(
                        (
                            "event_",
                            "peer_",
                            "coordination_",
                            "oil_",
                            "intelligent_",
                            "technology_",
                            "battery_",
                            "l3_",
                            "province_coordination_",
                        )
                    )
                },
                event_exposure=world.event_exposure_by_province.get(province_code),
                event_signal=signal,
                event_response=response,
                coordination_matches=matches,
                evidence_refs=evidence_refs,
            )
        return ProvinceAgentDetail(
            experiment_id=experiment_id,
            province_code=province_code,
            profile=self.profiles[province_code],
            persona=self.personas[province_code],
            top_k_neighbors=[
                ProvinceNeighbor(
                    province_code=edge.target,
                    province_name=self.profiles[edge.target].short_name,
                    weight=edge.weight,
                )
                for edge in self.network[province_code]
            ],
            branches=branches,
        )

    async def get_automaker_detail(self, experiment_id: str, automaker_id: str) -> AutomakerDetail:
        runtime = self._runtime(experiment_id)
        if automaker_id not in self.automaker_profiles:
            raise KeyError(f"automaker not found: {automaker_id}")
        return AutomakerDetail(
            experiment_id=experiment_id,
            automaker_id=automaker_id,
            profile=self.automaker_profiles[automaker_id],
            branches={
                world.branch_kind: world.automaker_states[automaker_id]
                for world in runtime.worlds.values()
            },
            actions={
                world.branch_kind: world.automaker_actions.get(automaker_id)
                for world in runtime.worlds.values()
            },
        )

    async def find_branch(self, branch_id: str) -> tuple[str, Branch]:
        for experiment_id, runtime in self.runtimes.items():
            if branch_id in runtime.branches:
                return experiment_id, runtime.branches[branch_id].model_copy(deep=True)
        raise KeyError(f"branch not found: {branch_id}")

    async def get_evidence(self, experiment_id: str, evidence_id: str) -> dict[str, object]:
        runtime = self._runtime(experiment_id)
        prefix, _, target = evidence_id.partition(":")
        if prefix == "audit":
            return (await self.get_audit_record(experiment_id, target)).model_dump(mode="json")
        if (
            prefix == "checkpoint"
            and runtime.checkpoint
            and target == runtime.checkpoint.checkpoint_id
        ):
            return runtime.checkpoint.model_dump(mode="json")
        if prefix == "comparison" and runtime.comparison:
            return runtime.comparison.model_dump(mode="json")
        if prefix == "action":
            for world in runtime.worlds.values():
                for action in [*world.province_actions.values(), *world.automaker_actions.values()]:
                    if action.action_id == target:
                        return action.model_dump(mode="json")
        if prefix == "scenario" and runtime.approved_event_scenario:
            if runtime.approved_event_scenario.scenario_id == target:
                return runtime.approved_event_scenario.model_dump(mode="json")
        if prefix == "interaction":
            for world in runtime.worlds.values():
                for interaction in [
                    *world.province_event_signals.values(),
                    *world.province_event_responses.values(),
                    *world.coordination_matches,
                ]:
                    interaction_id = next(
                        (
                            getattr(interaction, name)
                            for name in ("signal_id", "response_id", "match_id")
                            if getattr(interaction, name, None)
                        ),
                        None,
                    )
                    if interaction_id == target:
                        return interaction.model_dump(mode="json")
        if prefix in {"metric", "mechanism", "profile", "persona"}:
            return {
                "evidence_id": evidence_id,
                "type": prefix,
                "status": "available",
                "method_version": "nev-policy-env-v2",
            }
        raise KeyError(f"evidence not found: {evidence_id}")

    async def run_full_demo(
        self,
        config: ExperimentConfig,
        event_selection: EventScenarioSelection | None = None,
    ) -> ComparisonResult:
        state = await self.initialize(config)
        await self.approve_directive(state.experiment_id)
        review = await self.run_to_phase(state.experiment_id, Phase.YEAR1_REVIEW)
        if config.comparison_mode is ComparisonMode.POLICY_INTERVENTION:
            proposal = review.intervention_proposals[0]
            intervention = await self.approve_intervention(
                state.experiment_id, proposal.proposal_id
            )
            branch = await self.create_approved_branch(
                state.experiment_id, intervention.intervention_id
            )
        else:
            branch = await self.create_event_counterfactual_branches(state.experiment_id)
        await asyncio.gather(
            self.run_to_phase(state.experiment_id, Phase.Y2_Q2, "control"),
            self.run_to_phase(state.experiment_id, Phase.Y2_Q2, branch.branch_id),
        )
        await self.approve_event_scenario(
            state.experiment_id,
            event_selection
            or EventScenarioSelection(
                template_id=EventTemplateId.OIL_PRICE_RISE,
                intensity=EventIntensity.MEDIUM,
            ),
        )
        await asyncio.gather(
            self.run_to_phase(state.experiment_id, Phase.Y2_Q4, "control"),
            self.run_to_phase(state.experiment_id, Phase.Y2_Q4, branch.branch_id),
        )
        return await self.compare(state.experiment_id)

    async def close(self) -> None:
        return None
