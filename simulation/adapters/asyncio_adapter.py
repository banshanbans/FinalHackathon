import asyncio
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from simulation.agents.province_agent import ProvinceAgent
from simulation.agents.state_council_agent import StateCouncilAgent
from simulation.data import NetworkEdge, load_network, load_profiles, load_scenario_policy
from simulation.envs.china_policy_env import ChinaPolicyEnv
from simulation.llm.base import LLMProvider
from simulation.llm.fake_provider import FakeLLMProvider
from simulation.models.action import ProvinceAction
from simulation.models.central import (
    CentralIntervention,
    CentralPolicyDirective,
    ParameterChange,
)
from simulation.models.common import (
    ApprovalStatus,
    BranchKind,
    ExperimentStatus,
    Phase,
)
from simulation.models.event import EventEnvelope
from simulation.models.experiment import Branch, Checkpoint, ExperimentConfig, ExperimentRecord
from simulation.models.policy import PolicySchema
from simulation.models.province import ProvinceProfile
from simulation.models.world import ComparisonResult, VersionInfo, WorldState
from simulation.services.checkpoint import CheckpointService
from simulation.services.comparison import ComparisonService
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
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    condition: asyncio.Condition = field(default_factory=asyncio.Condition)


class AsyncioSimulationAdapter:
    """In-process simulation runtime with strong contracts and branch isolation."""

    def __init__(
        self,
        provider: LLMProvider,
        *,
        runtime_dir: Path | str = Path("runtime"),
        profiles: dict[str, ProvinceProfile] | None = None,
        network: dict[str, list[NetworkEdge]] | None = None,
        agent_timeout_seconds: float = 12,
    ):
        self.provider = provider
        self.fallback_provider = FakeLLMProvider()
        self.profiles = profiles or load_profiles()
        self.network = network or load_network()
        self.agent_timeout_seconds = agent_timeout_seconds
        self.default_policy = load_scenario_policy()
        self.state_council = StateCouncilAgent(provider)
        self.province_agents = {
            code: ProvinceAgent(profile, provider) for code, profile in self.profiles.items()
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
        initial_env = ChinaPolicyEnv(
            profiles=self.profiles, network=self.network, policy=directive.policy
        )
        world = WorldState(
            experiment_id=experiment_id,
            branch_id="control",
            phase=Phase.T0,
            status=ExperimentStatus.AWAITING_APPROVAL,
            run_mode=config.run_mode,
            policy=directive.policy.model_copy(deep=True),
            directive=directive,
            national_metrics=initial_env.calculate_national_metrics(),
            provinces=deepcopy(initial_env.states),
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
            world.directive = directive
            world.policy = approved_policy
            world.status = ExperimentStatus.READY
            runtime.record.directive = directive
            runtime.record.status = ExperimentStatus.READY
            runtime.record.updated_at = datetime.now(UTC)
            await self._emit(
                runtime,
                event_type="central.directive.approved",
                branch_id="control",
                phase=Phase.T0,
                payload={"directive_id": directive.directive_id},
            )
            self.replay.write_state(world)
            return world.model_copy(deep=True)

    @staticmethod
    def _expected_next(current: Phase) -> Phase | None:
        order = [Phase.T0, Phase.T1, Phase.T2, Phase.T3, Phase.T4, Phase.T5]
        index = order.index(current)
        return order[index + 1] if index < len(order) - 1 else None

    async def _generate_actions(
        self,
        *,
        runtime: ExperimentRuntime,
        world: WorldState,
        phase: Phase,
    ) -> dict[str, ProvinceAction]:
        previous = world.actions

        async def decide(code: str) -> tuple[str, ProvinceAction]:
            await self._emit(
                runtime,
                event_type="agent.decision.started",
                branch_id=world.branch_id,
                phase=phase,
                payload={"agent_type": "province", "province_code": code},
            )
            related = self.network[code]
            neighbors = {
                edge.target: previous[edge.target] for edge in related if edge.target in previous
            }
            try:
                action = await asyncio.wait_for(
                    self.province_agents[code].decide(
                        state=world.provinces[code],
                        policy=world.policy,
                        phase=phase,
                        related=related,
                        neighbor_actions=neighbors,
                    ),
                    timeout=self.agent_timeout_seconds,
                )
            except Exception:
                action = await self.fallback_provider.generate_province_action(
                    profile=self.profiles[code],
                    state=world.provinces[code],
                    policy=world.policy,
                    phase=phase,
                    related=related,
                    neighbor_actions=neighbors,
                )
                action = action.model_copy(update={"run_mode": "fallback", "fallback_used": True})
            await self._emit(
                runtime,
                event_type=(
                    "agent.decision.fallback"
                    if action.fallback_used
                    else "agent.decision.completed"
                ),
                branch_id=world.branch_id,
                phase=phase,
                payload={
                    "agent_type": "province",
                    "province_code": code,
                    "action_id": action.action_id,
                    "summary": action.public_summary,
                    "run_mode": action.run_mode,
                    "fallback_used": action.fallback_used,
                },
            )
            return code, action

        pairs = await asyncio.gather(*(decide(code) for code in sorted(self.profiles)))
        return dict(pairs)

    async def run_phase(
        self, experiment_id: str, phase: Phase, branch_id: str = "control"
    ) -> WorldState:
        runtime = self._runtime(experiment_id)
        async with runtime.lock:
            if branch_id not in runtime.worlds:
                raise KeyError(f"branch not found: {branch_id}")
            current_world = runtime.worlds[branch_id]
            if current_world.status == ExperimentStatus.AWAITING_APPROVAL:
                raise PermissionError("central directive must be approved before running")
            if current_world.status == ExperimentStatus.AWAITING_INTERVENTION:
                raise PermissionError("T3 intervention decision is required before continuing")
            expected = self._expected_next(current_world.phase)
            if phase != expected:
                raise ValueError(
                    f"invalid phase transition: {current_world.phase.value} -> {phase.value}"
                )
            if phase == Phase.T4 and branch_id == "control" and runtime.checkpoint is None:
                raise ValueError("T4 requires a T3 checkpoint")

            # A phase computes against a private copy and only replaces the
            # authoritative branch state after every calculation validates.
            world = current_world.model_copy(deep=True)
            world.status = ExperimentStatus.RUNNING
            await self._emit(
                runtime,
                event_type="phase.started",
                branch_id=branch_id,
                phase=phase,
                payload={"phase": phase.value},
            )
            env = ChinaPolicyEnv(
                profiles=self.profiles,
                network=self.network,
                policy=world.policy,
                states=deepcopy(world.provinces),
            )

            if phase in {Phase.T1, Phase.T3, Phase.T4}:
                actions = await self._generate_actions(runtime=runtime, world=world, phase=phase)
                world.actions = actions
                if phase in {Phase.T3, Phase.T4}:
                    states, contributions = env.process_actions(actions, phase)
                    world.provinces = states
                    world.contributions = contributions
                    world.network_effects = deepcopy(env.network_effects)
                    world.national_metrics = env.calculate_national_metrics()
            elif phase in {Phase.T2, Phase.T5}:
                if not world.actions:
                    raise ValueError(
                        f"{phase.value} requires actions from the previous decision phase"
                    )
                states, contributions = env.process_actions(world.actions, phase)
                world.provinces = states
                world.contributions = contributions
                world.network_effects = deepcopy(env.network_effects)
                world.national_metrics = env.calculate_national_metrics()

            world.phase = phase
            pending_checkpoint: Checkpoint | None = None
            pending_control_branch: Branch | None = None
            if phase == Phase.T3:
                proposals = await self.state_council.analyze_and_propose(
                    policy=world.policy,
                    metrics=world.national_metrics,
                    states=world.provinces,
                    actions=world.actions,
                )
                world.intervention_proposals = proposals
                world.status = ExperimentStatus.AWAITING_INTERVENTION
                checkpoint_id = f"cp_{uuid4().hex[:14]}"
                world.parent_checkpoint_id = checkpoint_id
                pending_checkpoint = self.checkpoints.create(world, checkpoint_id)
                pending_control_branch = Branch(
                    branch_id="control",
                    experiment_id=experiment_id,
                    kind=BranchKind.CONTROL,
                    parent_checkpoint_id=pending_checkpoint.checkpoint_id,
                )
            elif phase == Phase.T5:
                world.status = ExperimentStatus.COMPLETED
            else:
                world.status = ExperimentStatus.READY

            self.replay.write_state(world)
            runtime.worlds[branch_id] = world
            if pending_checkpoint and pending_control_branch:
                runtime.checkpoint = pending_checkpoint
                runtime.branches["control"] = pending_control_branch
            runtime.record.current_phase = phase
            runtime.record.status = world.status
            runtime.record.updated_at = datetime.now(UTC)
            if phase == Phase.T3:
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
                await self._emit(
                    runtime,
                    event_type="checkpoint.created",
                    branch_id=branch_id,
                    phase=phase,
                    payload={"checkpoint_id": pending_checkpoint.checkpoint_id},
                )
            await self._emit(
                runtime,
                event_type="environment.updated",
                branch_id=branch_id,
                phase=phase,
                payload={
                    "overall_policy_benefit": world.national_metrics.overall_policy_benefit,
                    "regional_gap": world.national_metrics.regional_gap,
                },
            )
            await self._emit(
                runtime,
                event_type="world_state.updated",
                branch_id=branch_id,
                phase=phase,
                payload={"status": world.status.value, "province_count": len(world.provinces)},
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
        overrides: dict[str, float] | None = None,
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
            changes = {
                field: change.model_copy(deep=True)
                for field, change in proposal.parameter_changes.items()
            }
            for field, to_value in (overrides or {}).items():
                if field not in changes:
                    raise ValueError(f"cannot override field outside proposal: {field}")
                changes[field] = ParameterChange(
                    from_value=float(getattr(world.policy, field)), to_value=to_value
                )
            intervention = CentralIntervention(
                intervention_id=f"intervention_{uuid4().hex[:12]}",
                proposal_id=proposal_id,
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
                },
            )
            return intervention.model_copy(deep=True)

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
            if any(branch.kind == BranchKind.TREATMENT for branch in runtime.branches.values()):
                raise ValueError("treatment branch already exists")
            treatment_id = f"treatment_{uuid4().hex[:8]}"
            treatment = self.checkpoints.restore(runtime.checkpoint)
            treatment.branch_id = treatment_id
            treatment.parent_checkpoint_id = checkpoint_id
            treatment.status = ExperimentStatus.READY
            treatment.approved_intervention = intervention.model_copy(deep=True)
            env = ChinaPolicyEnv(
                profiles=self.profiles,
                network=self.network,
                policy=treatment.policy,
                states=deepcopy(treatment.provinces),
            )
            treatment.policy = env.apply_approved_intervention(intervention)
            control = runtime.worlds["control"]
            control.parent_checkpoint_id = checkpoint_id
            control.status = ExperimentStatus.READY
            branch = Branch(
                branch_id=treatment_id,
                experiment_id=treatment.experiment_id,
                kind=BranchKind.TREATMENT,
                parent_checkpoint_id=checkpoint_id,
                intervention=intervention,
            )
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
        treatment_branch = next(
            (branch for branch in runtime.branches.values() if branch.kind == BranchKind.TREATMENT),
            None,
        )
        if runtime.checkpoint is None or treatment_branch is None:
            raise ValueError("comparison requires a T3 checkpoint and treatment branch")
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
        await self._emit(
            runtime,
            event_type="experiment.completed",
            branch_id="treatment",
            phase=Phase.T5,
            payload={"review_id": review.review_id},
        )
        self.replay.write_state(control)
        self.replay.write_state(treatment)
        return comparison.model_copy(deep=True)

    async def get_state(self, experiment_id: str, branch_id: str = "control") -> WorldState:
        runtime = self._runtime(experiment_id)
        if branch_id not in runtime.worlds:
            raise KeyError(f"branch not found: {branch_id}")
        return runtime.worlds[branch_id].model_copy(deep=True)

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

    async def run_full_demo(self, config: ExperimentConfig) -> ComparisonResult:
        world = await self.initialize(config)
        await self.approve_directive(world.experiment_id)
        await self.run_to_phase(world.experiment_id, Phase.T3)
        control = await self.get_state(world.experiment_id)
        proposal = control.intervention_proposals[0]
        intervention = await self.approve_intervention(world.experiment_id, proposal.proposal_id)
        if self._runtime(world.experiment_id).checkpoint is None:
            raise RuntimeError("T3 checkpoint missing")
        branch = await self.create_branch(
            self._runtime(world.experiment_id).checkpoint.checkpoint_id, intervention
        )
        await self.run_to_phase(world.experiment_id, Phase.T5, "control")
        await self.run_to_phase(world.experiment_id, Phase.T5, branch.branch_id)
        return await self.compare(world.experiment_id)

    async def close(self) -> None:
        self.runtimes.clear()
