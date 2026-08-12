import asyncio
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from pydantic import BaseModel

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
from simulation.llm.trace import ProviderCallCapture, capture_provider_call
from simulation.models.action import ProvinceAction
from simulation.models.audit import (
    AgentInvocationTrace,
    AuditActorKind,
    AuditListResponse,
    AuditOutcome,
    AuditRecord,
    AuditRecordType,
    DecisionGateTrace,
    MechanismExplanation,
    ProviderAttemptTrace,
)
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
from simulation.services.evidence import comparison_review_evidence_refs
from simulation.services.persona import validate_interprovincial_targets
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
    object_audit_refs: dict[str, str] = field(default_factory=dict)
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

    @staticmethod
    def _model_dump(value: object) -> object:
        if isinstance(value, BaseModel):
            return value.model_dump(mode="json")
        if isinstance(value, list):
            return [AsyncioSimulationAdapter._model_dump(item) for item in value]
        if isinstance(value, dict):
            return {
                str(key): AsyncioSimulationAdapter._model_dump(item) for key, item in value.items()
            }
        return value

    @staticmethod
    def _output_ids(value: object) -> list[str]:
        candidates: list[object]
        if isinstance(value, list):
            candidates = list(value)
        elif hasattr(value, "actions"):
            candidates = [value, *value.actions]
        else:
            candidates = [value]
        ids: list[str] = []
        for candidate in candidates:
            if isinstance(candidate, dict):
                fields = candidate
            else:
                fields = vars(candidate) if hasattr(candidate, "__dict__") else {}
            for name in (
                "directive_id",
                "action_id",
                "batch_id",
                "feedback_id",
                "proposal_id",
                "review_id",
            ):
                item = fields.get(name)
                if isinstance(item, str) and item not in ids:
                    ids.append(item)
        return ids

    def _record_agent_trace(
        self,
        *,
        runtime: ExperimentRuntime | None,
        experiment_id: str,
        branch_id: str,
        phase: Phase,
        actor_kind: AuditActorKind,
        actor_id: str,
        operation: str,
        run_mode: str,
        requested_model: str,
        prompt_version: str,
        response_schema: str,
        input_snapshot: object,
        output: object,
        capture: ProviderCallCapture,
        latency_ms: float,
        parent_record_ids: list[str] | None = None,
        fallback_reason: str | None = None,
    ) -> AuditRecord:
        output_ids = self._output_ids(output)
        reason = fallback_reason or capture.fallback_reason
        if reason or run_mode == "fallback":
            outcome = AuditOutcome.FALLBACK
        elif capture.cache_hit is True:
            outcome = AuditOutcome.CACHE_HIT
        elif capture.cache_hit is False:
            outcome = AuditOutcome.CACHE_MISS
        elif len(capture.attempts) == 2 and capture.attempts[-1].status == "succeeded":
            outcome = AuditOutcome.REPAIRED
        else:
            outcome = AuditOutcome.SUCCEEDED
        safe_input = sanitize_for_audit(self._model_dump(input_snapshot))
        safe_output = sanitize_for_audit(self._model_dump(output))
        payload = AgentInvocationTrace(
            actor_kind=actor_kind,
            actor_id=actor_id,
            operation=operation,
            run_mode=run_mode,
            model=capture.actual_model or requested_model,
            prompt_version=prompt_version,
            response_schema=response_schema,
            input_hash=canonical_hash(safe_input),
            input_snapshot=safe_input,
            attempts=capture.attempts,
            usage=capture.usage,
            latency_ms=round(latency_ms, 3),
            outcome=outcome,
            output_ids=output_ids,
            output_hash=canonical_hash(safe_output),
            output_snapshot=safe_output,
            cache_key_hash=capture.cache_key_hash,
            fallback_reason=reason,
        )
        record = self.replay.append_audit(
            experiment_id=experiment_id,
            branch_id=branch_id,
            phase=phase,
            payload=payload,
            parent_record_ids=parent_record_ids or [],
        )
        if runtime is not None:
            for object_id in output_ids:
                runtime.object_audit_refs[object_id] = record.record_id
        return record

    def _record_gate(
        self,
        runtime: ExperimentRuntime,
        *,
        branch_id: str,
        phase: Phase,
        actor_kind: AuditActorKind,
        actor_id: str,
        operation: str,
        outcome: AuditOutcome,
        object_ids: list[str],
        details: dict[str, object],
        parent_record_ids: list[str] | None = None,
    ) -> AuditRecord:
        payload = DecisionGateTrace(
            actor_kind=actor_kind,
            actor_id=actor_id,
            operation=operation,
            outcome=outcome,
            object_ids=object_ids,
            details=sanitize_for_audit(details),
        )
        record = self.replay.append_audit(
            experiment_id=runtime.record.experiment_id,
            branch_id=branch_id,
            phase=phase,
            payload=payload,
            parent_record_ids=parent_record_ids or [],
        )
        for object_id in object_ids:
            runtime.object_audit_refs[object_id] = record.record_id
        return record

    def _record_mechanisms(
        self,
        runtime: ExperimentRuntime,
        *,
        branch_id: str,
        phase: Phase,
        explanations: list[MechanismExplanation],
    ) -> list[AuditRecord]:
        items: list[tuple[MechanismExplanation, list[str]]] = []
        for explanation in explanations:
            parents = [
                runtime.object_audit_refs[ref]
                for ref in explanation.source_refs
                if ref in runtime.object_audit_refs
            ]
            items.append((explanation, list(dict.fromkeys(parents))))
        records = self.replay.append_audits(
            experiment_id=runtime.record.experiment_id,
            branch_id=branch_id,
            phase=phase,
            items=items,
        )
        for explanation, record in zip(explanations, records, strict=True):
            runtime.object_audit_refs[explanation.explanation_id] = record.record_id
        return records

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
        started = perf_counter()
        with capture_provider_call() as provider_capture:
            directive = await self.state_council.draft_directive(config, self.default_policy)
        directive_latency = (perf_counter() - started) * 1000
        env = ChinaPolicyEnv(
            profiles=self.profiles,
            network=self.network,
            enterprise_profiles=self.enterprise_profiles,
            policy=directive.policy,
        )
        national_metrics = env.calculate_national_metrics()
        world = WorldState(
            experiment_id=experiment_id,
            branch_id="control",
            phase=Phase.T0,
            status=ExperimentStatus.AWAITING_APPROVAL,
            run_mode=config.run_mode,
            policy=directive.policy.model_copy(deep=True),
            directive=directive,
            national_metrics=national_metrics,
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
        directive_audit = self._record_agent_trace(
            runtime=runtime,
            experiment_id=experiment_id,
            branch_id="control",
            phase=Phase.T0,
            actor_kind=AuditActorKind.CENTRAL_AGENT,
            actor_id="central",
            operation="draft_directive",
            run_mode=config.run_mode.value,
            requested_model=config.model_version,
            prompt_version=config.prompt_version,
            response_schema=directive.schema_version,
            input_snapshot={"config": config, "default_policy": self.default_policy},
            output=directive,
            capture=provider_capture,
            latency_ms=directive_latency,
        )
        self._record_mechanisms(
            runtime,
            branch_id="control",
            phase=Phase.T0,
            explanations=env.explanations,
        )
        persona_audits: dict[str, AuditRecord] = {}
        for code, persona in sorted(self.personas.items()):
            capture = ProviderCallCapture(actual_model="deterministic-persona-rule-v1")
            persona_audits[code] = self._record_agent_trace(
                runtime=runtime,
                experiment_id=experiment_id,
                branch_id="control",
                phase=Phase.T0,
                actor_kind=AuditActorKind.PERSONA_RULE,
                actor_id=code,
                operation="derive_persona",
                run_mode="deterministic",
                requested_model="deterministic-persona-rule-v1",
                prompt_version=persona.method_version,
                response_schema=persona.schema_version,
                input_snapshot={
                    "profile": self.profiles[code],
                    "top_k": self.network[code],
                    "seed": config.seed,
                },
                output=persona,
                capture=capture,
                latency_ms=0,
            )
            runtime.object_audit_refs[f"persona:{code}"] = persona_audits[code].record_id
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
            payload={
                "directive_id": directive.directive_id,
                "audit_record_id": directive_audit.record_id,
            },
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
                    "audit_record_id": persona_audits[code].record_id,
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
            approval_audit = self._record_gate(
                runtime,
                branch_id="control",
                phase=Phase.T0,
                actor_kind=AuditActorKind.USER,
                actor_id="policy_operator",
                operation="approve_central_directive",
                outcome=AuditOutcome.SUCCEEDED,
                object_ids=[directive.directive_id],
                details={
                    "approval_status": ApprovalStatus.APPROVED.value,
                    "policy": approved_policy,
                },
                parent_record_ids=[runtime.object_audit_refs[directive.directive_id]]
                if directive.directive_id in runtime.object_audit_refs
                else [],
            )
            await self._emit(
                runtime,
                event_type="central.directive.approved",
                branch_id="control",
                phase=Phase.T0,
                payload={
                    "directive_id": directive.directive_id,
                    "policy_schema": approved_policy.schema_version,
                    "audit_record_id": approval_audit.record_id,
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
            input_snapshot = {
                "profile": self.profiles[code],
                "persona": world.province_personas[code],
                "state": world.province_states[code],
                "policy": world.policy,
                "phase": phase.value,
                "related": related,
                "neighbor_actions": neighbors,
                "previous_action": previous_action,
                "feedback": feedback,
                **self._call_context(world),
            }
            started = perf_counter()
            failure_reason: str | None = None
            with capture_provider_call() as provider_capture:
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
                except Exception as error:
                    failure_reason = type(error).__name__
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
                    action = action.model_copy(
                        update={"run_mode": "fallback", "fallback_used": True}
                    )
                try:
                    validate_interprovincial_targets(action, {edge.target for edge in related})
                except ValueError:
                    failure_reason = "topology_validation_failed"
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
                    action = action.model_copy(
                        update={"run_mode": "fallback", "fallback_used": True}
                    )
            parents = [runtime.object_audit_refs[f"persona:{code}"]]
            for parent in (previous_action, feedback):
                if parent is None:
                    continue
                for object_id in self._output_ids(parent):
                    if object_id in runtime.object_audit_refs:
                        parents.append(runtime.object_audit_refs[object_id])
            audit = self._record_agent_trace(
                runtime=runtime,
                experiment_id=runtime.record.experiment_id,
                branch_id=world.branch_id,
                phase=phase,
                actor_kind=AuditActorKind.PROVINCE_AGENT,
                actor_id=code,
                operation="decide_province_action",
                run_mode=action.run_mode,
                requested_model=world.versions.model,
                prompt_version=world.versions.prompt,
                response_schema=action.schema_version,
                input_snapshot=input_snapshot,
                output=action,
                capture=provider_capture,
                latency_ms=(perf_counter() - started) * 1000,
                parent_record_ids=list(dict.fromkeys(parents)),
                fallback_reason=failure_reason,
            )
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
                    "audit_record_id": audit.record_id,
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
            input_snapshot = {
                "province_profile": self.profiles[code],
                "province_action": world.province_actions[code],
                "enterprise_profiles": self.enterprise_by_province[code],
                "enterprise_states": states,
                "policy": world.policy,
                "phase": phase.value,
                **self._call_context(world),
            }
            started = perf_counter()
            failure_reason: str | None = None
            with capture_provider_call() as provider_capture:
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
                    failure_reason = type(error).__name__
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
                            "fallback_reason": failure_reason,
                        }
                    )
            parent_id = runtime.object_audit_refs.get(world.province_actions[code].action_id)
            audit = self._record_agent_trace(
                runtime=runtime,
                experiment_id=runtime.record.experiment_id,
                branch_id=world.branch_id,
                phase=phase,
                actor_kind=AuditActorKind.ENTERPRISE_AGENT,
                actor_id=code,
                operation="decide_enterprise_batch",
                run_mode=batch.run_mode,
                requested_model=world.versions.model,
                prompt_version=world.versions.prompt,
                response_schema=batch.schema_version,
                input_snapshot=input_snapshot,
                output=batch,
                capture=provider_capture,
                latency_ms=(perf_counter() - started) * 1000,
                parent_record_ids=[parent_id] if parent_id else [],
                fallback_reason=batch.fallback_reason or failure_reason,
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
                    "audit_record_id": audit.record_id,
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
            input_snapshot = {
                "profile": self.profiles[code],
                "persona": world.province_personas[code],
                "state": world.province_states[code],
                "current_action": world.province_actions[code],
                "aggregate": world.enterprise_aggregates[code],
                "enterprise_actions": actions,
                "policy": world.policy,
                **self._call_context(world),
            }
            started = perf_counter()
            failure_reason: str | None = None
            with capture_provider_call() as provider_capture:
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
                except Exception as error:
                    failure_reason = type(error).__name__
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
            parent_ids = [
                runtime.object_audit_refs[item.action_id]
                for item in actions
                if item.action_id in runtime.object_audit_refs
            ]
            current_action_ref = runtime.object_audit_refs.get(
                world.province_actions[code].action_id
            )
            if current_action_ref:
                parent_ids.append(current_action_ref)
            audit = self._record_agent_trace(
                runtime=runtime,
                experiment_id=runtime.record.experiment_id,
                branch_id=world.branch_id,
                phase=Phase.T3,
                actor_kind=AuditActorKind.PROVINCE_AGENT,
                actor_id=code,
                operation="review_enterprise_feedback",
                run_mode=feedback.run_mode,
                requested_model=world.versions.model,
                prompt_version=world.versions.prompt,
                response_schema=feedback.schema_version,
                input_snapshot=input_snapshot,
                output=feedback,
                capture=provider_capture,
                latency_ms=(perf_counter() - started) * 1000,
                parent_record_ids=list(dict.fromkeys(parent_ids)),
                fallback_reason=failure_reason,
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
                    "audit_record_id": audit.record_id,
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
                    "audit_record_id": audit.record_id,
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
        mechanism_audits = self._record_mechanisms(
            runtime,
            branch_id=world.branch_id,
            phase=phase,
            explanations=env.explanations,
        )
        national_audits = [
            record
            for explanation, record in zip(env.explanations, mechanism_audits, strict=True)
            if explanation.scope == "national"
        ]
        await self._emit(
            runtime,
            event_type="enterprise.aggregate.updated",
            branch_id=world.branch_id,
            phase=phase,
            payload={
                "province_count": len(aggregates),
                "enterprise_count": len(enterprise_states),
                "audit_record_id": mechanism_audits[0].record_id if mechanism_audits else None,
            },
        )
        await self._emit(
            runtime,
            event_type="environment.updated",
            branch_id=world.branch_id,
            phase=phase,
            payload={
                **world.national_metrics.model_dump(mode="json"),
                "audit_record_id": national_audits[0].record_id if national_audits else None,
                "audit_record_ids": [record.record_id for record in national_audits],
            },
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
            proposal_audit: AuditRecord | None = None
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
                proposal_input = {
                    "policy": world.policy,
                    "metrics": world.national_metrics,
                    "states": world.province_states,
                    "feedback": world.province_feedback,
                    "enterprise_actions": world.enterprise_actions,
                }
                started = perf_counter()
                with capture_provider_call() as provider_capture:
                    world.intervention_proposals = await self.state_council.analyze_and_propose(
                        **proposal_input
                    )
                proposal_audit = self._record_agent_trace(
                    runtime=runtime,
                    experiment_id=runtime.record.experiment_id,
                    branch_id=world.branch_id,
                    phase=Phase.T3,
                    actor_kind=AuditActorKind.CENTRAL_AGENT,
                    actor_id="central",
                    operation="propose_intervention",
                    run_mode=world.run_mode.value,
                    requested_model=world.versions.model,
                    prompt_version=world.versions.prompt,
                    response_schema="central-intervention-proposal-list-v1",
                    input_snapshot=proposal_input,
                    output=world.intervention_proposals,
                    capture=provider_capture,
                    latency_ms=(perf_counter() - started) * 1000,
                    parent_record_ids=list(
                        dict.fromkeys(
                            runtime.object_audit_refs[item.feedback_id]
                            for item in world.province_feedback.values()
                            if item.feedback_id in runtime.object_audit_refs
                        )
                    ),
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
                    started = perf_counter()
                    with capture_provider_call() as provider_capture:
                        world.central_review = await self.state_council.review(world)
                    self._record_agent_trace(
                        runtime=runtime,
                        experiment_id=runtime.record.experiment_id,
                        branch_id=world.branch_id,
                        phase=Phase.T5,
                        actor_kind=AuditActorKind.CENTRAL_AGENT,
                        actor_id="central",
                        operation="review_single_branch",
                        run_mode=world.run_mode.value,
                        requested_model=world.versions.model,
                        prompt_version=world.versions.prompt,
                        response_schema=world.central_review.schema_version,
                        input_snapshot=world.model_dump(mode="json", exclude={"central_review"}),
                        output=world.central_review,
                        capture=provider_capture,
                        latency_ms=(perf_counter() - started) * 1000,
                    )

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
                checkpoint_audit = self._record_gate(
                    runtime,
                    branch_id=branch_id,
                    phase=phase,
                    actor_kind=AuditActorKind.ORCHESTRATOR,
                    actor_id="orchestrator",
                    operation="freeze_checkpoint",
                    outcome=AuditOutcome.SUCCEEDED,
                    object_ids=[pending_checkpoint.checkpoint_id],
                    details={
                        "state_hash": pending_checkpoint.state_hash,
                        "branch_id": pending_checkpoint.branch_id,
                        "phase": pending_checkpoint.phase.value,
                    },
                    parent_record_ids=[proposal_audit.record_id] if proposal_audit else [],
                )
                await self._emit(
                    runtime,
                    event_type="checkpoint.created",
                    branch_id=branch_id,
                    phase=phase,
                    payload={
                        "checkpoint_id": pending_checkpoint.checkpoint_id,
                        "audit_record_id": checkpoint_audit.record_id,
                    },
                )
                await self._emit(
                    runtime,
                    event_type="central.intervention.proposed",
                    branch_id=branch_id,
                    phase=phase,
                    payload={
                        "proposal_ids": [item.proposal_id for item in world.intervention_proposals],
                        "summary": world.intervention_proposals[0].public_summary,
                        "audit_record_id": proposal_audit.record_id if proposal_audit else None,
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
            approval_audit = self._record_gate(
                runtime,
                branch_id="control",
                phase=Phase.T3,
                actor_kind=AuditActorKind.USER,
                actor_id="policy_operator",
                operation="approve_intervention",
                outcome=AuditOutcome.SUCCEEDED,
                object_ids=[intervention.intervention_id, proposal_id],
                details={
                    "change_count": len(changes),
                    "parameter_changes": changes,
                    "approved_policy": selected,
                },
                parent_record_ids=[runtime.object_audit_refs[proposal_id]]
                if proposal_id in runtime.object_audit_refs
                else [],
            )
            await self._emit(
                runtime,
                event_type="central.intervention.approved",
                branch_id="control",
                phase=Phase.T3,
                payload={
                    "intervention_id": intervention.intervention_id,
                    "proposal_id": proposal_id,
                    "change_count": len(changes),
                    "audit_record_id": approval_audit.record_id,
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
            rejection_audit = self._record_gate(
                runtime,
                branch_id="control",
                phase=Phase.T3,
                actor_kind=AuditActorKind.USER,
                actor_id="policy_operator",
                operation="reject_intervention",
                outcome=AuditOutcome.REJECTED,
                object_ids=[proposal_id],
                details={"treatment_created": False},
                parent_record_ids=[runtime.object_audit_refs[proposal_id]]
                if proposal_id in runtime.object_audit_refs
                else [],
            )
            await self._emit(
                runtime,
                event_type="central.intervention.rejected",
                branch_id="control",
                phase=Phase.T3,
                payload={
                    "proposal_id": proposal_id,
                    "treatment_created": False,
                    "audit_record_id": rejection_audit.record_id,
                },
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
            branch_audit = self._record_gate(
                runtime,
                branch_id=treatment_id,
                phase=Phase.T3,
                actor_kind=AuditActorKind.ORCHESTRATOR,
                actor_id="orchestrator",
                operation="derive_treatment_branch",
                outcome=AuditOutcome.SUCCEEDED,
                object_ids=[treatment_id, checkpoint_id, intervention.intervention_id],
                details={
                    "checkpoint_state_hash": runtime.checkpoint.state_hash,
                    "control_unchanged": True,
                    "active_difference_paths": [
                        change.path for change in intervention.parameter_changes
                    ],
                },
                parent_record_ids=[
                    runtime.object_audit_refs[item]
                    for item in (checkpoint_id, intervention.intervention_id)
                    if item in runtime.object_audit_refs
                ],
            )
            await self._emit(
                runtime,
                event_type="branch.created",
                branch_id=treatment_id,
                phase=Phase.T3,
                payload={
                    "checkpoint_id": checkpoint_id,
                    "kind": "treatment",
                    "audit_record_id": branch_audit.record_id,
                },
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
        started = perf_counter()
        with capture_provider_call() as provider_capture:
            review = await self.state_council.review(comparison)
        try:
            self.comparisons.validate_review(review, comparison)
        except ValueError as error:
            invalid_hash = canonical_hash(review)
            allowed_refs = set(comparison_review_evidence_refs(comparison))
            invalid_refs = [
                ref
                for finding in review.findings
                for ref in finding.evidence_refs
                if ref not in allowed_refs
            ]
            semantic_attempt = ProviderAttemptTrace(
                attempt=max(1, len(provider_capture.attempts)),
                status="validation_error",
                latency_ms=round((perf_counter() - started) * 1000, 3),
                error_code="central_review_evidence_validation_failed",
                validation_paths=[f"findings.evidence_refs:{ref}" for ref in invalid_refs[:12]],
                invalid_response_hash=invalid_hash,
            )
            if provider_capture.attempts:
                provider_capture.attempts[-1] = semantic_attempt
            else:
                provider_capture.attempts.append(semantic_attempt)
            provider_capture.fallback_reason = str(error)[:240]
            review = await self.fallback_provider.generate_central_review(comparison)
            self.comparisons.validate_review(review, comparison)
        review_audit = self._record_agent_trace(
            runtime=runtime,
            experiment_id=runtime.record.experiment_id,
            branch_id=treatment_branch.branch_id,
            phase=Phase.T5,
            actor_kind=AuditActorKind.CENTRAL_AGENT,
            actor_id="central",
            operation="review_comparison",
            run_mode=treatment.run_mode.value,
            requested_model=treatment.versions.model,
            prompt_version=treatment.versions.prompt,
            response_schema=review.schema_version,
            input_snapshot=comparison.model_dump(mode="json", exclude={"central_review"}),
            output=review,
            capture=provider_capture,
            latency_ms=(perf_counter() - started) * 1000,
            parent_record_ids=[runtime.object_audit_refs[runtime.checkpoint.checkpoint_id]]
            if runtime.checkpoint.checkpoint_id in runtime.object_audit_refs
            else [],
        )
        comparison.central_review = review
        control.central_review = review
        treatment.central_review = review
        runtime.comparison = comparison
        comparison_audit = self._record_gate(
            runtime,
            branch_id=treatment_branch.branch_id,
            phase=Phase.T5,
            actor_kind=AuditActorKind.ORCHESTRATOR,
            actor_id="comparison_service",
            operation="compare_control_and_treatment",
            outcome=AuditOutcome.SUCCEEDED,
            object_ids=["comparison", comparison.checkpoint_id],
            details={
                "control_branch_id": comparison.control_branch_id,
                "treatment_branch_id": comparison.treatment_branch_id,
                "policy_diff": comparison.policy_diff,
                "mechanism_totals": comparison.mechanism_totals,
                "province_transition_count": len(comparison.province_strategy_transitions),
            },
            parent_record_ids=[review_audit.record_id],
        )
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
            payload={
                "review_id": review.review_id,
                "review_mode": review.review_mode.value,
                "audit_record_id": comparison_audit.record_id,
            },
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

    async def get_audit(
        self,
        experiment_id: str,
        *,
        branch_id: str | None = None,
        phase: Phase | None = None,
        actor_kind: str | None = None,
        actor_id: str | None = None,
        record_type: AuditRecordType | None = None,
        outcome: str | None = None,
        after_sequence: int = 0,
        limit: int = 100,
    ) -> AuditListResponse:
        self._runtime(experiment_id)
        return self.replay.read_audit(
            experiment_id,
            branch_id=branch_id,
            phase=phase,
            actor_kind=actor_kind,
            actor_id=actor_id,
            record_type=record_type,
            outcome=outcome,
            after_sequence=after_sequence,
            limit=limit,
        )

    async def get_audit_record(self, experiment_id: str, record_id: str) -> AuditRecord:
        self._runtime(experiment_id)
        return self.replay.get_audit_record(experiment_id, record_id)

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
        runtime = self._runtime(experiment_id)
        world = await self.get_state(experiment_id)
        common: dict[str, object] = {
            "evidence_id": evidence_id,
            "experiment_id": experiment_id,
            "data_version": world.versions.data,
            "mechanism_version": world.versions.mechanism,
            "prompt_version": world.versions.prompt,
            "model_version": world.versions.model,
            "app_version": world.versions.app,
            "seed": world.seed,
            "parent_checkpoint_id": world.parent_checkpoint_id,
            "disclaimer": "结果为当前数据与机制参数下的模拟指数，用于方案比较。",
        }
        if evidence_id == "method":
            listing = self.replay.read_audit(experiment_id, limit=1)
            return {
                **common,
                "kind": "method_and_versions",
                "quality": "proxy",
                "source": "PolicyScope 版本化模型、环境与哈希链审计记录",
                "unit": "指数/100 或指数点变化",
                "transformation": "Agent 只选择结构化策略，结果由确定性环境统一测算",
                "missing_value_handling": "校验失败时按整省规则接管并显式标记",
                "audit_chain_valid": self.replay.verify_audit_chain(experiment_id),
                "first_audit_sequence": (listing.records[0].sequence if listing.records else None),
            }

        record: AuditRecord | None = None
        if evidence_id.startswith("audit:"):
            record = self.replay.get_audit_record(experiment_id, evidence_id[6:])
        elif evidence_id.startswith("action:"):
            record = self.replay.find_audit_by_object(experiment_id, evidence_id[7:])
        elif evidence_id.startswith("mechanism:"):
            object_id = evidence_id[10:]
            try:
                record = self.replay.find_audit_by_object(experiment_id, object_id)
            except KeyError:
                records = self.replay.read_audit(
                    experiment_id,
                    record_type=AuditRecordType.MECHANISM_EXPLANATION,
                    limit=5000,
                ).records
                record = next(
                    (
                        item
                        for item in reversed(records)
                        if isinstance(item.payload, MechanismExplanation)
                        and (
                            item.payload.subject_id == object_id
                            or item.payload.explanation_id == object_id
                        )
                    ),
                    None,
                )
        elif evidence_id.startswith("checkpoint:"):
            record = self.replay.find_audit_by_object(experiment_id, evidence_id[11:])
        elif evidence_id.startswith("comparison:"):
            record = self.replay.find_audit_by_object(experiment_id, "comparison")
        elif evidence_id.startswith("persona:"):
            code = evidence_id.split(":", 2)[1]
            record_id = runtime.object_audit_refs.get(f"persona:{code}")
            if record_id:
                record = self.replay.get_audit_record(experiment_id, record_id)
        elif evidence_id.startswith("enterprise:"):
            parts = evidence_id.split(":")
            if len(parts) >= 3:
                province_code = parts[1]
                records = self.replay.read_audit(
                    experiment_id,
                    actor_kind=AuditActorKind.ENTERPRISE_AGENT.value,
                    actor_id=province_code,
                    limit=500,
                ).records
                record = records[-1] if records else None
        elif evidence_id.startswith(("metric:national:", "world:")):
            parts = evidence_id.split(":")
            phase_value = next(
                (item for item in reversed(parts) if item in {phase.value for phase in Phase}),
                world.phase.value,
            )
            metric = (
                parts[2]
                if evidence_id.startswith("metric:national:")
                and len(parts) > 3
                and not parts[2].startswith("T")
                else None
            )
            records = self.replay.read_audit(
                experiment_id,
                phase=Phase(phase_value),
                record_type=AuditRecordType.MECHANISM_EXPLANATION,
                limit=5000,
            ).records
            matches = [
                item
                for item in records
                if isinstance(item.payload, MechanismExplanation)
                and item.payload.scope == "national"
                and (metric is None or item.payload.metric == metric)
            ]
            if matches:
                return {
                    **common,
                    "kind": "mechanism_evidence",
                    "quality": "proxy",
                    "source": "确定性环境的全国聚合解释",
                    "audit_records": [item.model_dump(mode="json") for item in matches],
                    "audit_chain_valid": self.replay.verify_audit_chain(experiment_id),
                }
        if record is None:
            raise KeyError(f"evidence not found: {evidence_id}")
        kind = (
            "agent_behavior"
            if isinstance(record.payload, AgentInvocationTrace)
            else "mechanism_evidence"
            if isinstance(record.payload, MechanismExplanation)
            else "decision_gate"
        )
        return {
            **common,
            "kind": kind,
            "quality": "demo" if evidence_id.startswith("enterprise:") else "proxy",
            "source": "PolicyScope 追加式审计记录",
            "audit_record": record.model_dump(mode="json"),
            "audit_chain_valid": self.replay.verify_audit_chain(experiment_id),
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
