import asyncio
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from simulation.agents.enterprise_agent import EnterpriseBatchAgent
from simulation.agents.province_agent import ProvinceAgent
from simulation.agents.state_council_agent import StateCouncilAgent
from simulation.data import (
    NetworkEdge,
    enterprise_profiles_by_province,
    load_enterprise_profiles,
    load_network,
    load_profiles,
    load_province_personas,
    load_scenario_policy,
)
from simulation.envs.china_policy_env import ChinaPolicyEnv
from simulation.llm.base import LLMProvider
from simulation.llm.fake_provider import FakeLLMProvider, policy_diff
from simulation.models.action import ProvinceAction
from simulation.models.central import CentralIntervention, CentralPolicyDirective
from simulation.models.common import ApprovalStatus, BranchKind, ExperimentStatus, Phase
from simulation.models.enterprise import EnterpriseAction, EnterpriseActionBatch
from simulation.models.event import EventEnvelope
from simulation.models.experiment import Branch, Checkpoint, ExperimentConfig, ExperimentRecord
from simulation.models.policy import PolicySchema
from simulation.models.province import (
    ProvinceDecisionPersona,
    ProvinceFeedback,
    ProvinceProfile,
)
from simulation.models.world import (
    ComparisonResult,
    ProvinceAgentBranchSnapshot,
    ProvinceAgentDetail,
    ProvinceEnterpriseEvidence,
    ProvinceNeighbor,
    VersionInfo,
    WorldState,
)
from simulation.services.checkpoint import CheckpointService
from simulation.services.comparison import ComparisonService
from simulation.services.persona import validate_interprovincial_targets
from simulation.services.replay import ReplayService


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
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    condition: asyncio.Condition = field(default_factory=asyncio.Condition)


class AsyncioSimulationAdapter:
    """In-process V2.1 runtime with atomic phases, approvals and branch isolation."""

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
        self.network = network or load_network()
        self.personas = personas or (
            load_province_personas() if profiles is None and network is None else None
        )
        if self.personas is None:
            from simulation.data import build_province_personas

            self.personas = build_province_personas(self.profiles, self.network)
        self.enterprise_profiles = load_enterprise_profiles()
        self.enterprise_by_province = enterprise_profiles_by_province(self.enterprise_profiles)
        self.agent_timeout_seconds = agent_timeout_seconds
        self.default_policy = load_scenario_policy()
        self.state_council = StateCouncilAgent(provider)
        self.province_agents = {
            code: ProvinceAgent(profile, provider) for code, profile in self.profiles.items()
        }
        self.enterprise_agents = {
            code: EnterpriseBatchAgent(profile, self.enterprise_by_province[code], provider)
            for code, profile in self.profiles.items()
        }
        self.checkpoints = CheckpointService()
        self.comparisons = ComparisonService()
        self.replay = ReplayService(Path(runtime_dir))
        self.runtimes: dict[str, ExperimentRuntime] = {}

    def _runtime(self, experiment_id: str) -> ExperimentRuntime:
        try:
            return self.runtimes[experiment_id]
        except KeyError as error:
            raise KeyError(f"experiment not found: {experiment_id}") from error

    async def _emit(
        self,
        runtime: ExperimentRuntime,
        *,
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
            payload=payload or {},
        )
        runtime.events.append(event)
        self.replay.append(event)
        async with runtime.condition:
            runtime.condition.notify_all()
        return event

    async def initialize(self, config: ExperimentConfig) -> WorldState:
        experiment_id = f"exp_{uuid4().hex[:14]}"
        directive = await self.state_council.draft_directive(config, self.default_policy)
        env = ChinaPolicyEnv(
            profiles=self.profiles,
            network=self.network,
            enterprise_profiles=self.enterprise_profiles,
            policy=directive.policy,
        )
        world = WorldState(
            experiment_id=experiment_id,
            branch_id="control",
            phase=Phase.T0,
            status=ExperimentStatus.AWAITING_APPROVAL,
            run_mode=config.run_mode,
            policy=directive.policy.model_copy(deep=True),
            directive=directive,
            national_metrics=env.calculate_national_metrics(),
            province_profiles=deepcopy(self.profiles),
            province_personas=deepcopy(self.personas),
            province_states=deepcopy(env.province_states),
            enterprise_profiles=deepcopy(self.enterprise_profiles),
            enterprise_states=deepcopy(env.enterprise_states),
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
        await self._emit(
            runtime,
            event_type="experiment.started",
            branch_id="control",
            phase=Phase.T0,
            payload={"status": world.status.value, "run_mode": config.run_mode.value},
        )
        await self._emit(
            runtime,
            event_type="central.directive.completed",
            branch_id="control",
            phase=Phase.T0,
            payload={"directive_id": directive.directive_id},
        )
        for code, persona in sorted(self.personas.items()):
            await self._emit(
                runtime,
                event_type="province.persona.ready",
                branch_id="control",
                phase=Phase.T0,
                payload={
                    "province_code": code,
                    "primary_type": persona.primary_type.value,
                    "secondary_type": (
                        persona.secondary_type.value if persona.secondary_type else None
                    ),
                    "method_version": persona.method_version,
                },
            )
        self.replay.write_state(world)
        return world.model_copy(deep=True)

    async def approve_directive(
        self, experiment_id: str, policy: PolicySchema | None = None
    ) -> WorldState:
        runtime = self._runtime(experiment_id)
        async with runtime.lock:
            world = runtime.worlds["control"]
            if world.status != ExperimentStatus.AWAITING_APPROVAL:
                raise ValueError("directive is not awaiting approval")
            approved_policy = (policy or world.policy).model_copy(deep=True)
            directive: CentralPolicyDirective = world.directive.model_copy(
                update={
                    "policy": approved_policy,
                    "approval_status": ApprovalStatus.APPROVED,
                },
                deep=True,
            )
            next_world = world.model_copy(deep=True)
            next_world.directive = directive
            next_world.policy = approved_policy
            next_world.status = ExperimentStatus.READY
            runtime.worlds["control"] = next_world
            runtime.record.directive = directive
            runtime.record.status = ExperimentStatus.READY
            runtime.record.updated_at = datetime.now(UTC)
            await self._emit(
                runtime,
                event_type="central.directive.approved",
                branch_id="control",
                phase=Phase.T0,
                payload={
                    "directive_id": directive.directive_id,
                    "policy_schema": approved_policy.schema_version,
                },
            )
            self.replay.write_state(next_world)
            return next_world.model_copy(deep=True)

    @staticmethod
    def _expected_next(current: Phase) -> Phase | None:
        order = [Phase.T0, Phase.T1, Phase.T2, Phase.T3, Phase.T4, Phase.T5]
        index = order.index(current)
        return order[index + 1] if index < len(order) - 1 else None

    def _call_context(self, world: WorldState) -> dict[str, object]:
        return {
            "seed": world.seed,
            "prompt_version": world.versions.prompt,
            "model_version": world.versions.model,
        }

    async def _generate_province_actions(
        self, runtime: ExperimentRuntime, world: WorldState, phase: Phase
    ) -> dict[str, ProvinceAction]:
        previous = world.province_actions

        async def decide(code: str) -> tuple[str, ProvinceAction]:
            await self._emit(
                runtime,
                event_type="province.decision.started",
                branch_id=world.branch_id,
                phase=phase,
                payload={"province_code": code},
            )
            related = self.network[code]
            neighbors = {
                edge.target: previous[edge.target] for edge in related if edge.target in previous
            }
            previous_action = previous.get(code)
            feedback = world.province_feedback.get(code) if phase == Phase.T4 else None
            try:
                action = await asyncio.wait_for(
                    self.province_agents[code].decide(
                        state=world.province_states[code],
                        persona=world.province_personas[code],
                        policy=world.policy,
                        phase=phase,
                        related=related,
                        neighbor_actions=neighbors,
                        previous_action=previous_action,
                        feedback=feedback,
                        **self._call_context(world),
                    ),
                    timeout=self.agent_timeout_seconds,
                )
            except Exception:
                action = await self.fallback_provider.generate_province_action(
                    profile=self.profiles[code],
                    persona=world.province_personas[code],
                    state=world.province_states[code],
                    policy=world.policy,
                    phase=phase,
                    related=related,
                    neighbor_actions=neighbors,
                    previous_action=previous_action,
                    feedback=feedback,
                    **self._call_context(world),
                )
                action = action.model_copy(update={"run_mode": "fallback", "fallback_used": True})
            try:
                validate_interprovincial_targets(action, {edge.target for edge in related})
            except ValueError:
                action = await self.fallback_provider.generate_province_action(
                    profile=self.profiles[code],
                    persona=world.province_personas[code],
                    state=world.province_states[code],
                    policy=world.policy,
                    phase=phase,
                    related=related,
                    neighbor_actions=neighbors,
                    previous_action=previous_action,
                    feedback=feedback,
                    **self._call_context(world),
                )
                action = action.model_copy(update={"run_mode": "fallback", "fallback_used": True})
            await self._emit(
                runtime,
                event_type=(
                    "province.decision.fallback"
                    if action.fallback_used
                    else "province.decision.completed"
                ),
                branch_id=world.branch_id,
                phase=phase,
                payload={
                    "province_code": code,
                    "action_id": action.action_id,
                    "summary": action.public_summary,
                    "run_mode": action.run_mode,
                    "fallback_used": action.fallback_used,
                    "primary_goal": action.primary_goal.value,
                    "decision_posture": action.decision_posture.value,
                    "interprovincial_strategy": action.interprovincial_strategy.value,
                },
            )
            return code, action

        pairs = await asyncio.gather(*(decide(code) for code in sorted(self.profiles)))
        return dict(pairs)

    async def _generate_enterprise_batches(
        self, runtime: ExperimentRuntime, world: WorldState, phase: Phase
    ) -> tuple[dict[str, EnterpriseAction], list[str]]:
        if set(world.province_actions) != set(self.profiles):
            raise ValueError("enterprise decisions require 31 province actions")

        async def decide(code: str) -> EnterpriseActionBatch:
            await self._emit(
                runtime,
                event_type="enterprise.batch.started",
                branch_id=world.branch_id,
                phase=phase,
                payload={"province_code": code, "expected_actions": 6},
            )
            enterprise_ids = {
                profile.enterprise_id for profile in self.enterprise_by_province[code]
            }
            states = {key: world.enterprise_states[key] for key in sorted(enterprise_ids)}
            try:
                batch = await asyncio.wait_for(
                    self.enterprise_agents[code].decide(
                        province_action=world.province_actions[code],
                        enterprise_states=states,
                        policy=world.policy,
                        phase=phase,
                        **self._call_context(world),
                    ),
                    timeout=self.agent_timeout_seconds,
                )
            except Exception as error:
                batch = await self.fallback_provider.generate_enterprise_actions_batch(
                    province_profile=self.profiles[code],
                    province_action=world.province_actions[code],
                    enterprise_profiles=self.enterprise_by_province[code],
                    enterprise_states=states,
                    policy=world.policy,
                    phase=phase,
                    **self._call_context(world),
                )
                batch = batch.model_copy(
                    update={
                        "run_mode": "fallback",
                        "fallback_used": True,
                        "fallback_reason": type(error).__name__,
                    }
                )
            await self._emit(
                runtime,
                event_type=(
                    "enterprise.batch.fallback"
                    if batch.fallback_used
                    else "enterprise.batch.completed"
                ),
                branch_id=world.branch_id,
                phase=phase,
                payload={
                    "province_code": code,
                    "batch_id": batch.batch_id,
                    "action_count": len(batch.actions),
                    "run_mode": batch.run_mode,
                    "fallback_used": batch.fallback_used,
                    "fallback_reason": batch.fallback_reason,
                },
            )
            return batch

        batches = await asyncio.gather(*(decide(code) for code in sorted(self.profiles)))
        actions = {item.enterprise_id: item for batch in batches for item in batch.actions}
        fallback_provinces = [batch.province_code for batch in batches if batch.fallback_used]
        if len(actions) != 186:
            raise ValueError(f"expected 186 enterprise actions, got {len(actions)}")
        return actions, fallback_provinces

    async def _generate_feedback(
        self, runtime: ExperimentRuntime, world: WorldState
    ) -> dict[str, ProvinceFeedback]:
        if set(world.enterprise_aggregates) != set(self.profiles):
            raise ValueError("T3 feedback requires enterprise aggregates from T2")

        async def decide(code: str) -> tuple[str, ProvinceFeedback]:
            actions = [
                action
                for action in world.enterprise_actions.values()
                if action.province_code == code
            ]
            try:
                feedback = await asyncio.wait_for(
                    self.province_agents[code].feedback(
                        persona=world.province_personas[code],
                        state=world.province_states[code],
                        current_action=world.province_actions[code],
                        aggregate=world.enterprise_aggregates[code],
                        enterprise_actions=actions,
                        policy=world.policy,
                        **self._call_context(world),
                    ),
                    timeout=self.agent_timeout_seconds,
                )
            except Exception:
                feedback = await self.fallback_provider.generate_province_feedback(
                    profile=self.profiles[code],
                    persona=world.province_personas[code],
                    state=world.province_states[code],
                    current_action=world.province_actions[code],
                    aggregate=world.enterprise_aggregates[code],
                    enterprise_actions=actions,
                    policy=world.policy,
                    **self._call_context(world),
                )
                feedback = feedback.model_copy(
                    update={"run_mode": "fallback", "fallback_used": True}
                )
            await self._emit(
                runtime,
                event_type="province.adjustment_intent.completed",
                branch_id=world.branch_id,
                phase=Phase.T3,
                payload={
                    "province_code": code,
                    "feedback_id": feedback.feedback_id,
                    "summary": feedback.public_summary,
                    "run_mode": feedback.run_mode,
                    "fallback_used": feedback.fallback_used,
                    "intent_count": len(feedback.adjustment_intents),
                },
            )
            await self._emit(
                runtime,
                event_type="province.feedback.completed",
                branch_id=world.branch_id,
                phase=Phase.T3,
                payload={
                    "province_code": code,
                    "feedback_id": feedback.feedback_id,
                    "strategy_assessment": feedback.strategy_assessment.value,
                },
            )
            return code, feedback

        pairs = await asyncio.gather(*(decide(code) for code in sorted(self.profiles)))
        return dict(pairs)

    def _environment(self, world: WorldState) -> ChinaPolicyEnv:
        return ChinaPolicyEnv(
            profiles=world.province_profiles,
            network=self.network,
            enterprise_profiles=world.enterprise_profiles,
            policy=world.policy,
            province_states=deepcopy(world.province_states),
            enterprise_states=deepcopy(world.enterprise_states),
        )

    async def _settle_environment(
        self, runtime: ExperimentRuntime, world: WorldState, phase: Phase
    ) -> None:
        env = self._environment(world)
        province_states, enterprise_states, aggregates, contributions = env.process_actions(
            world.province_actions, world.enterprise_actions, phase
        )
        world.province_states = province_states
        world.enterprise_states = enterprise_states
        world.enterprise_aggregates = aggregates
        world.contributions = contributions
        world.national_metrics = env.calculate_national_metrics()
        await self._emit(
            runtime,
            event_type="enterprise.aggregate.updated",
            branch_id=world.branch_id,
            phase=phase,
            payload={
                "province_count": len(aggregates),
                "enterprise_count": len(enterprise_states),
            },
        )
        await self._emit(
            runtime,
            event_type="environment.updated",
            branch_id=world.branch_id,
            phase=phase,
            payload=world.national_metrics.model_dump(mode="json"),
        )

    async def run_phase(
        self, experiment_id: str, phase: Phase, branch_id: str = "control"
    ) -> WorldState:
        runtime = self._runtime(experiment_id)
        async with runtime.lock:
            if branch_id not in runtime.worlds:
                raise KeyError(f"branch not found: {branch_id}")
            current = runtime.worlds[branch_id]
            if current.status == ExperimentStatus.AWAITING_APPROVAL:
                raise PermissionError("central directive must be approved before running")
            if current.status == ExperimentStatus.AWAITING_INTERVENTION:
                raise PermissionError("T3 intervention decision is required before continuing")
            expected = self._expected_next(current.phase)
            if phase != expected:
                raise ValueError(
                    f"invalid phase transition: {current.phase.value} -> {phase.value}"
                )
            if phase == Phase.T4 and runtime.checkpoint is None:
                raise ValueError("T4 requires a T3 checkpoint")

            world = current.model_copy(deep=True)
            world.status = ExperimentStatus.RUNNING
            await self._emit(
                runtime,
                event_type="phase.started",
                branch_id=branch_id,
                phase=phase,
                payload={"phase": phase.value},
            )

            pending_checkpoint: Checkpoint | None = None
            world.phase = phase
            if phase == Phase.T1:
                actions = await self._generate_province_actions(runtime, world, phase)
                world.province_actions = actions
                world.province_action_lineage = {code: [action] for code, action in actions.items()}
            elif phase == Phase.T2:
                (
                    world.enterprise_actions,
                    world.fallback_provinces,
                ) = await self._generate_enterprise_batches(runtime, world, phase)
                await self._settle_environment(runtime, world, phase)
            elif phase == Phase.T3:
                world.province_feedback = await self._generate_feedback(runtime, world)
                world.intervention_proposals = await self.state_council.analyze_and_propose(
                    policy=world.policy,
                    metrics=world.national_metrics,
                    states=world.province_states,
                    feedback=world.province_feedback,
                    enterprise_actions=world.enterprise_actions,
                )
                if not world.intervention_proposals:
                    raise ValueError("central agent returned no intervention proposal")
                world.status = ExperimentStatus.AWAITING_INTERVENTION
                checkpoint_id = f"cp_{uuid4().hex[:14]}"
                world.parent_checkpoint_id = checkpoint_id
                pending_checkpoint = self.checkpoints.create(world, checkpoint_id)
            elif phase == Phase.T4:
                actions = await self._generate_province_actions(runtime, world, phase)
                for code, action in actions.items():
                    world.province_action_lineage.setdefault(code, []).append(action)
                world.province_actions = actions
                (
                    world.enterprise_actions,
                    branch_fallbacks,
                ) = await self._generate_enterprise_batches(runtime, world, phase)
                world.fallback_provinces = sorted(
                    set(world.fallback_provinces) | set(branch_fallbacks)
                )
                await self._settle_environment(runtime, world, phase)
            elif phase == Phase.T5:
                if len(world.enterprise_actions) != 186:
                    raise ValueError("T5 requires 186 enterprise actions from T4")
                await self._settle_environment(runtime, world, phase)
                world.status = ExperimentStatus.COMPLETED
                if branch_id == "control" and runtime.intervention_rejected:
                    world.central_review = await self.state_council.review(world)

            if phase not in {Phase.T3, Phase.T5}:
                world.status = ExperimentStatus.READY
            runtime.worlds[branch_id] = world
            if pending_checkpoint:
                runtime.checkpoint = pending_checkpoint
                runtime.branches["control"] = Branch(
                    branch_id="control",
                    experiment_id=experiment_id,
                    kind=BranchKind.CONTROL,
                    parent_checkpoint_id=pending_checkpoint.checkpoint_id,
                )
                await self._emit(
                    runtime,
                    event_type="checkpoint.created",
                    branch_id=branch_id,
                    phase=phase,
                    payload={"checkpoint_id": pending_checkpoint.checkpoint_id},
                )
                await self._emit(
                    runtime,
                    event_type="central.intervention.proposed",
                    branch_id=branch_id,
                    phase=phase,
                    payload={
                        "proposal_ids": [item.proposal_id for item in world.intervention_proposals],
                        "summary": world.intervention_proposals[0].public_summary,
                    },
                )
            runtime.record.current_phase = phase
            runtime.record.status = world.status
            runtime.record.updated_at = datetime.now(UTC)
            self.replay.write_state(world)
            await self._emit(
                runtime,
                event_type="world_state.updated",
                branch_id=branch_id,
                phase=phase,
                payload={
                    "status": world.status.value,
                    "province_count": len(world.province_states),
                    "enterprise_count": len(world.enterprise_states),
                },
            )
            await self._emit(
                runtime,
                event_type="phase.completed",
                branch_id=branch_id,
                phase=phase,
                payload={"phase": phase.value},
            )
            return world.model_copy(deep=True)

    async def run_to_phase(
        self, experiment_id: str, target: Phase, branch_id: str = "control"
    ) -> WorldState:
        world = await self.get_state(experiment_id, branch_id)
        if target.order <= world.phase.order:
            raise ValueError(
                f"target phase {target.value} must be later than current phase {world.phase.value}"
            )
        while world.phase.order < target.order:
            next_phase = self._expected_next(world.phase)
            if next_phase is None:
                break
            world = await self.run_phase(experiment_id, next_phase, branch_id)
        return world

    async def create_checkpoint(self, experiment_id: str, phase: Phase) -> Checkpoint:
        runtime = self._runtime(experiment_id)
        world = runtime.worlds["control"]
        if world.phase != phase:
            raise ValueError("checkpoint phase does not match current world phase")
        checkpoint = self.checkpoints.create(world)
        runtime.checkpoint = checkpoint
        return checkpoint.model_copy(deep=True)

    async def approve_intervention(
        self,
        experiment_id: str,
        proposal_id: str,
        approved_policy: PolicySchema | None = None,
    ) -> CentralIntervention:
        runtime = self._runtime(experiment_id)
        async with runtime.lock:
            world = runtime.worlds["control"]
            if world.phase != Phase.T3 or world.status != ExperimentStatus.AWAITING_INTERVENTION:
                raise ValueError("intervention can only be approved at the T3 checkpoint")
            proposal = next(
                (item for item in world.intervention_proposals if item.proposal_id == proposal_id),
                None,
            )
            if proposal is None:
                raise KeyError(f"intervention proposal not found: {proposal_id}")
            selected = (approved_policy or proposal.proposed_policy).model_copy(deep=True)
            changes = policy_diff(world.policy, selected)
            if not changes:
                raise ValueError("approved intervention must change at least one policy field")
            intervention = CentralIntervention(
                intervention_id=f"intervention_{uuid4().hex[:12]}",
                proposal_id=proposal_id,
                approved_policy=selected,
                parameter_changes=changes,
                approved_at=datetime.now(UTC),
            )
            runtime.approved_interventions[intervention.intervention_id] = intervention
            await self._emit(
                runtime,
                event_type="central.intervention.approved",
                branch_id="control",
                phase=Phase.T3,
                payload={
                    "intervention_id": intervention.intervention_id,
                    "proposal_id": proposal_id,
                    "change_count": len(changes),
                },
            )
            return intervention.model_copy(deep=True)

    async def reject_intervention(self, experiment_id: str, proposal_id: str) -> WorldState:
        runtime = self._runtime(experiment_id)
        async with runtime.lock:
            world = runtime.worlds["control"]
            if world.phase != Phase.T3 or world.status != ExperimentStatus.AWAITING_INTERVENTION:
                raise ValueError("intervention can only be rejected at the T3 checkpoint")
            proposal = next(
                (item for item in world.intervention_proposals if item.proposal_id == proposal_id),
                None,
            )
            if proposal is None:
                raise KeyError(f"intervention proposal not found: {proposal_id}")
            next_world = world.model_copy(deep=True)
            next_world.intervention_decision = "rejected"
            next_world.intervention_proposals = [
                item.model_copy(
                    update={
                        "approval_status": (
                            ApprovalStatus.REJECTED
                            if item.proposal_id == proposal_id
                            else item.approval_status
                        )
                    }
                )
                for item in next_world.intervention_proposals
            ]
            next_world.status = ExperimentStatus.READY
            runtime.intervention_rejected = True
            runtime.worlds["control"] = next_world
            runtime.record.status = ExperimentStatus.READY
            await self._emit(
                runtime,
                event_type="central.intervention.rejected",
                branch_id="control",
                phase=Phase.T3,
                payload={"proposal_id": proposal_id, "treatment_created": False},
            )
            self.replay.write_state(next_world)
            return next_world.model_copy(deep=True)

    async def create_branch(self, checkpoint_id: str, intervention: CentralIntervention) -> Branch:
        runtime = next(
            (
                candidate
                for candidate in self.runtimes.values()
                if candidate.checkpoint and candidate.checkpoint.checkpoint_id == checkpoint_id
            ),
            None,
        )
        if runtime is None or runtime.checkpoint is None:
            raise KeyError(f"checkpoint not found: {checkpoint_id}")
        if intervention.intervention_id not in runtime.approved_interventions:
            raise PermissionError("intervention has not been approved by the user")
        async with runtime.lock:
            if runtime.intervention_rejected:
                raise PermissionError("rejected intervention cannot create a treatment branch")
            if any(branch.kind == BranchKind.TREATMENT for branch in runtime.branches.values()):
                raise ValueError("treatment branch already exists")
            treatment_id = f"treatment_{uuid4().hex[:8]}"
            treatment = self.checkpoints.restore(runtime.checkpoint)
            treatment.branch_id = treatment_id
            treatment.parent_checkpoint_id = checkpoint_id
            treatment.status = ExperimentStatus.READY
            treatment.intervention_decision = "approved"
            treatment.approved_intervention = intervention.model_copy(deep=True)
            treatment.policy = intervention.approved_policy.model_copy(deep=True)
            control = runtime.worlds["control"].model_copy(deep=True)
            control.parent_checkpoint_id = checkpoint_id
            control.status = ExperimentStatus.READY
            control.intervention_decision = "approved_control_unchanged"
            branch = Branch(
                branch_id=treatment_id,
                experiment_id=treatment.experiment_id,
                kind=BranchKind.TREATMENT,
                parent_checkpoint_id=checkpoint_id,
                intervention=intervention,
            )
            runtime.worlds["control"] = control
            runtime.worlds[treatment_id] = treatment
            runtime.branches[treatment_id] = branch
            await self._emit(
                runtime,
                event_type="branch.created",
                branch_id=treatment_id,
                phase=Phase.T3,
                payload={"checkpoint_id": checkpoint_id, "kind": "treatment"},
            )
            self.replay.write_state(control)
            self.replay.write_state(treatment)
            return branch.model_copy(deep=True)

    async def compare(self, experiment_id: str) -> ComparisonResult:
        runtime = self._runtime(experiment_id)
        if runtime.comparison is not None:
            return runtime.comparison.model_copy(deep=True)
        treatment_branch = next(
            (branch for branch in runtime.branches.values() if branch.kind == BranchKind.TREATMENT),
            None,
        )
        if runtime.intervention_rejected or treatment_branch is None:
            raise ValueError("COMPARISON_NOT_AVAILABLE")
        if runtime.checkpoint is None:
            raise ValueError("comparison requires a T3 checkpoint")
        control = runtime.worlds["control"]
        treatment = runtime.worlds[treatment_branch.branch_id]
        if control.phase != Phase.T5 or treatment.phase != Phase.T5:
            raise ValueError("both branches must complete T5 before comparison")
        comparison = self.comparisons.compare(
            checkpoint_id=runtime.checkpoint.checkpoint_id,
            control=control,
            treatment=treatment,
            profiles=self.profiles,
        )
        review = await self.state_council.review(comparison)
        self.comparisons.validate_review(review, comparison)
        comparison.central_review = review
        control.central_review = review
        treatment.central_review = review
        runtime.comparison = comparison
        for transition in comparison.province_strategy_transitions:
            if not transition.changed:
                continue
            await self._emit(
                runtime,
                event_type="province.strategy.changed",
                branch_id=treatment.branch_id,
                phase=Phase.T5,
                payload={
                    "province_code": transition.province_code,
                    "control_action_id": transition.control_action_id,
                    "treatment_action_id": transition.treatment_action_id,
                    "changed_paths": [item.path for item in transition.changes],
                },
            )
        await self._emit(
            runtime,
            event_type="experiment.completed",
            branch_id=treatment.branch_id,
            phase=Phase.T5,
            payload={"review_id": review.review_id, "review_mode": review.review_mode.value},
        )
        self.replay.write_state(control)
        self.replay.write_state(treatment)
        return comparison.model_copy(deep=True)

    async def get_state(self, experiment_id: str, branch_id: str = "control") -> WorldState:
        runtime = self._runtime(experiment_id)
        if branch_id not in runtime.worlds:
            raise KeyError(f"branch not found: {branch_id}")
        return runtime.worlds[branch_id].model_copy(deep=True)

    async def get_province_detail(
        self, experiment_id: str, province_code: str
    ) -> ProvinceAgentDetail:
        runtime = self._runtime(experiment_id)
        if province_code not in self.profiles:
            raise KeyError(f"province not found: {province_code}")
        contribution_fields = (
            "policy_match",
            "direct_subsidy",
            "interest_subsidy",
            "financing_guarantee",
            "sme_preference",
            "regional_support",
            "financing_constraint",
            "fiscal_cost",
        )
        branches: dict[BranchKind, ProvinceAgentBranchSnapshot] = {}
        for branch_id, world in sorted(
            runtime.worlds.items(), key=lambda item: (item[0] != "control", item[0])
        ):
            kind = BranchKind.CONTROL if branch_id == "control" else BranchKind.TREATMENT
            enterprise_items = [
                ProvinceEnterpriseEvidence(
                    profile=profile,
                    state=world.enterprise_states.get(profile.enterprise_id),
                    action=world.enterprise_actions.get(profile.enterprise_id),
                    contribution=world.contributions.get(profile.enterprise_id),
                )
                for profile in self.enterprise_by_province[province_code]
            ]
            mechanism_summary = {
                field: round(
                    sum(
                        getattr(item.contribution, field)
                        for item in enterprise_items
                        if item.contribution is not None
                    ),
                    4,
                )
                for field in contribution_fields
            }
            feedback = world.province_feedback.get(province_code)
            refs = [f"persona:{province_code}:province-persona-method-v1"]
            if feedback:
                refs.extend(feedback.evidence_refs)
            branches[kind] = ProvinceAgentBranchSnapshot(
                branch_id=branch_id,
                branch_kind=kind,
                phase=world.phase,
                state=world.province_states[province_code],
                current_action=world.province_actions.get(province_code),
                action_lineage=world.province_action_lineage.get(province_code, []),
                feedback=feedback,
                enterprise_groups=enterprise_items,
                mechanism_summary=mechanism_summary,
                evidence_refs=list(dict.fromkeys(refs)),
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

    async def get_record(self, experiment_id: str) -> ExperimentRecord:
        return self._runtime(experiment_id).record.model_copy(deep=True)

    async def get_events(
        self, experiment_id: str, after_event_id: str | None = None
    ) -> list[EventEnvelope]:
        runtime = self._runtime(experiment_id)
        if not after_event_id:
            return [item.model_copy(deep=True) for item in runtime.events]
        try:
            index = next(
                idx for idx, event in enumerate(runtime.events) if event.event_id == after_event_id
            )
        except StopIteration:
            index = -1
        return [item.model_copy(deep=True) for item in runtime.events[index + 1 :]]

    async def wait_for_events(
        self,
        experiment_id: str,
        after_event_id: str | None,
        timeout_seconds: float = 15,
    ) -> list[EventEnvelope]:
        runtime = self._runtime(experiment_id)
        available = await self.get_events(experiment_id, after_event_id)
        if available:
            return available
        try:
            async with runtime.condition:
                await asyncio.wait_for(runtime.condition.wait(), timeout=timeout_seconds)
        except TimeoutError:
            return []
        return await self.get_events(experiment_id, after_event_id)

    async def get_replay(self, experiment_id: str) -> list[dict[str, object]]:
        self._runtime(experiment_id)
        return self.replay.read_raw(experiment_id)

    async def get_comparison(self, experiment_id: str) -> ComparisonResult:
        runtime = self._runtime(experiment_id)
        if runtime.comparison is None:
            return await self.compare(experiment_id)
        return runtime.comparison.model_copy(deep=True)

    async def create_approved_branch(self, experiment_id: str, intervention_id: str) -> Branch:
        runtime = self._runtime(experiment_id)
        if runtime.checkpoint is None:
            raise ValueError("T3 checkpoint is not available")
        try:
            intervention = runtime.approved_interventions[intervention_id]
        except KeyError as error:
            raise PermissionError("intervention has not been approved by the user") from error
        return await self.create_branch(runtime.checkpoint.checkpoint_id, intervention)

    async def find_branch(self, branch_id: str) -> tuple[str, Branch]:
        matches = [
            (experiment_id, runtime.branches[branch_id])
            for experiment_id, runtime in self.runtimes.items()
            if branch_id in runtime.branches
        ]
        if len(matches) != 1:
            raise KeyError(f"branch not found or ambiguous: {branch_id}")
        return matches[0]

    async def get_evidence(self, experiment_id: str, evidence_id: str) -> dict[str, object]:
        world = await self.get_state(experiment_id)
        is_method = evidence_id == "method"
        return {
            "evidence_id": evidence_id,
            "experiment_id": experiment_id,
            "kind": "method_and_versions" if is_method else "simulation_evidence",
            "quality": "demo" if evidence_id.startswith("enterprise:") else "proxy",
            "source": (
                "PolicyScope 实验方法、版本与父检查点记录"
                if is_method
                else "当前推演快照中的结构化字段与审计事件"
            ),
            "source_url": None,
            "source_year": 2024,
            "unit": "指数/100 或指数点变化",
            "transformation": "指标与机制贡献由版本化环境统一测算",
            "missing_value_handling": ("缺失或校验失败时按整省规则接管处理并标记"),
            "data_version": world.versions.data,
            "mechanism_version": world.versions.mechanism,
            "prompt_version": world.versions.prompt,
            "model_version": world.versions.model,
            "app_version": world.versions.app,
            "seed": world.seed,
            "parent_checkpoint_id": world.parent_checkpoint_id,
            "description": "该证据来自当前推演快照与版本记录。",
            "disclaimer": "结果为当前数据与机制参数下的模拟指数，用于方案比较。",
        }

    async def run_full_demo(self, config: ExperimentConfig) -> ComparisonResult:
        world = await self.initialize(config)
        await self.approve_directive(world.experiment_id, world.policy)
        await self.run_to_phase(world.experiment_id, Phase.T3)
        control = await self.get_state(world.experiment_id)
        proposal = control.intervention_proposals[0]
        intervention = await self.approve_intervention(
            world.experiment_id, proposal.proposal_id, proposal.proposed_policy
        )
        branch = await self.create_approved_branch(
            world.experiment_id, intervention.intervention_id
        )
        await self.run_to_phase(world.experiment_id, Phase.T5, "control")
        await self.run_to_phase(world.experiment_id, Phase.T5, branch.branch_id)
        return await self.compare(world.experiment_id)

    async def close(self) -> None:
        self.runtimes.clear()
