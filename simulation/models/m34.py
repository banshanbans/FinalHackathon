from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from simulation.models.automaker import (
    AutomakerState,
    FacilityAction,
    ProvinceMarketAction,
)
from simulation.models.base import DomainModel, FrozenDomainModel
from simulation.models.common import BranchKind
from simulation.models.province import ProvinceState, SubsidyMix
from simulation.models.v32 import (
    AgentInvocationRecord,
    AutomakerResourceEnvelope,
    AutomakerSimulationPersona,
    ExperimentType,
    JourneyStep,
    PolicyInterpretation,
    PolicyV4,
    ProvinceRelationNetwork,
    ProvinceResourceEnvelope,
    V32DataQuality,
    V32ExperimentStatus,
)
from simulation.models.world import NationalMetrics


class MacroTick(StrEnum):
    Q1 = "Q1"
    Q2 = "Q2"
    Q3 = "Q3"
    Q4 = "Q4"

    @property
    def order(self) -> int:
        return list(type(self)).index(self)


class InteractionWave(StrEnum):
    WAVE_0 = "wave_0"
    WAVE_1 = "wave_1"
    WAVE_2 = "wave_2"

    @property
    def order(self) -> int:
        return list(type(self)).index(self)


class AgentKindM34(StrEnum):
    PROVINCE = "province"
    AUTOMAKER = "automaker"
    CENTRAL = "central"


class EngagementMode(StrEnum):
    IGNORE = "ignore"
    MONITOR = "monitor"
    INITIATE = "initiate"
    RESPOND = "respond"
    REVISE = "revise"


class MessageKind(StrEnum):
    PUBLIC_POLICY = "public_policy"
    PUBLIC_EVENT = "public_event"
    PUBLIC_ACTION_SIGNAL = "public_action_signal"
    INTERPROVINCIAL_PROPOSAL = "interprovincial_proposal"
    PROVINCE_AUTOMAKER_PACKAGE = "province_automaker_package"
    AUTOMAKER_PROVINCE_INTENT = "automaker_province_intent"
    AUTOMAKER_COUNTEROFFER = "automaker_counteroffer"
    RESOURCE_REALLOCATION = "resource_reallocation"
    TRANSACTION_RESPONSE = "transaction_response"


class MessageVisibility(StrEnum):
    PUBLIC = "public"
    OBSERVATION_NETWORK = "observation_network"
    PRIVATE = "private"


class TransactionState(StrEnum):
    PROPOSED = "proposed"
    COUNTERED = "countered"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DEFERRED = "deferred"
    SETTLED = "settled"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"
    RESOURCE_INVALID = "resource_invalid"


TERMINAL_TRANSACTION_STATES = frozenset(
    {
        TransactionState.SETTLED,
        TransactionState.REJECTED,
        TransactionState.WITHDRAWN,
        TransactionState.EXPIRED,
        TransactionState.RESOURCE_INVALID,
    }
)


class EventPlanV2(DomainModel):
    schema_version: Literal["event-plan-v2"] = "event-plan-v2"
    event_plan_id: str = Field(min_length=1, max_length=160)
    template_id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=500)
    conflict_group: str | None = Field(default=None, max_length=80)
    scheduled_tick: MacroTick
    release_wave: InteractionWave
    branch_scope: Literal["both", "treatment_only"]
    advance_notice: bool = False
    informed_agent_types: list[Literal["province", "automaker"]] = Field(
        default_factory=list, max_length=2
    )
    affected_subjects: list[Literal["province", "automaker", "consumer", "supply_chain"]] = Field(
        min_length=1, max_length=4
    )
    mechanism_channels: list[str] = Field(min_length=1, max_length=8)
    intensity: Literal["low", "medium", "high"] = "medium"
    data_quality: Literal[V32DataQuality.SCENARIO_ASSUMPTION] = V32DataQuality.SCENARIO_ASSUMPTION
    evidence_refs: list[str] = Field(min_length=1, max_length=8)


class ExperimentDesignV2(DomainModel):
    schema_version: Literal["experiment-design-v2"] = "experiment-design-v2"
    experiment_type: ExperimentType
    control_policy: PolicyV4
    treatment_policy: PolicyV4
    event_plans: list[EventPlanV2] = Field(default_factory=list, max_length=3)
    status: Literal["confirmed"] = "confirmed"

    @model_validator(mode="after")
    def valid_active_difference_and_events(self) -> ExperimentDesignV2:
        template_ids = [item.template_id for item in self.event_plans]
        if len(template_ids) != len(set(template_ids)):
            raise ValueError("event templates must be unique within one experiment")
        conflict_groups = [item.conflict_group for item in self.event_plans if item.conflict_group]
        if len(conflict_groups) != len(set(conflict_groups)):
            raise ValueError("event plans in the same conflict group are mutually exclusive")
        policy_fields = ("west_central_share", "central_central_share", "east_central_share")
        same_policy = all(
            getattr(self.control_policy, field) == getattr(self.treatment_policy, field)
            for field in policy_fields
        )
        if self.experiment_type is ExperimentType.POLICY_COMPARISON:
            if same_policy or self.event_plans:
                raise ValueError("policy comparison requires different policies and no event")
        elif self.experiment_type is ExperimentType.POLICY_STRESS_TEST:
            if same_policy or any(item.branch_scope != "both" for item in self.event_plans):
                raise ValueError("policy stress test requires different policies and shared events")
        else:
            if (
                not same_policy
                or not self.event_plans
                or any(item.branch_scope != "treatment_only" for item in self.event_plans)
            ):
                raise ValueError(
                    "event counterfactual requires identical policies and treatment-only events"
                )
        return self


class QualityCountM34(DomainModel):
    quality: V32DataQuality
    field_count: int = Field(ge=0)
    explanation: str


class BaselineSnapshotV3(FrozenDomainModel):
    schema_version: Literal["baseline-snapshot-v3"] = "baseline-snapshot-v3"
    checkpoint_schema_version: Literal["tick-checkpoint-v1"] = "tick-checkpoint-v1"
    checkpoint_id: str
    state_hash: str
    province_count: Literal[31] = 31
    automaker_count: Literal[10] = 10
    baseline_year: Literal[2025] = 2025
    quality_counts: list[QualityCountM34]
    missing_value_policy: str
    uncovered_content: list[str] = Field(default_factory=list)
    data_version: str = "nev-m29-2025-v2"
    relation_network_version: str = "province-relation-network-v3"
    resource_version: Literal["annual-resource-envelope-v1"] = "annual-resource-envelope-v1"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class LogicalTime(FrozenDomainModel):
    tick: MacroTick
    wave: InteractionWave | None = None
    sequence: int = Field(ge=0)


class AuthorizedInbox(FrozenDomainModel):
    schema_version: Literal["authorized-inbox-v1"] = "authorized-inbox-v1"
    inbox_id: str
    branch_id: str
    tick: MacroTick
    wave: InteractionWave
    agent_kind: AgentKindM34
    agent_id: str
    message_ids: list[str] = Field(default_factory=list, max_length=500)
    public_policy_summary: str
    public_national_summary: str | None = None
    own_result_summary: str | None = None
    pending_session_ids: list[str] = Field(default_factory=list, max_length=80)
    visible_event_ids: list[str] = Field(default_factory=list, max_length=3)
    previous_decision_id: str | None = None
    context_hash: str


class ProvinceQuarterAction(DomainModel):
    schema_version: Literal["province-quarter-action-v1"] = "province-quarter-action-v1"
    action_id: str
    branch_id: str
    tick: MacroTick
    province_code: str = Field(pattern=r"^\d{2}$")
    overall_support_intensity: float = Field(ge=0, le=1)
    subsidy_mix: SubsidyMix
    public_summary: str = Field(min_length=1, max_length=180)


class AutomakerQuarterAction(DomainModel):
    schema_version: Literal["automaker-quarter-action-v1"] = "automaker-quarter-action-v1"
    action_id: str
    branch_id: str
    tick: MacroTick
    automaker_id: str
    province_market_actions: list[ProvinceMarketAction]
    facility_actions: list[FacilityAction] = Field(default_factory=list, max_length=3)
    public_summary: str = Field(min_length=1, max_length=180)

    @model_validator(mode="after")
    def complete_national_action(self) -> AutomakerQuarterAction:
        codes = [item.province_code for item in self.province_market_actions]
        if len(codes) != 31 or len(set(codes)) != 31:
            raise ValueError("automaker quarter action must cover 31 unique provinces")
        facilities = [item.province_code for item in self.facility_actions]
        if len(facilities) != len(set(facilities)):
            raise ValueError("facility actions must use unique provinces")
        return self


class InteractionMessage(DomainModel):
    schema_version: Literal["interaction-message-v1"] = "interaction-message-v1"
    message_id: str
    branch_id: str
    tick: MacroTick
    wave: InteractionWave
    logical_sequence: int = Field(ge=0)
    kind: MessageKind
    visibility: MessageVisibility
    sender_kind: AgentKindM34
    sender_id: str
    recipient_ids: list[str] = Field(default_factory=list, max_length=40)
    session_id: str | None = None
    transaction_state: TransactionState | None = None
    reply_to_message_id: str | None = None
    resource_amount: float = Field(default=0, ge=0, le=1)
    public_summary: str = Field(min_length=1, max_length=240)
    private_terms: str | None = Field(default=None, max_length=500)
    evidence_refs: list[str] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def valid_visibility_and_transaction(self) -> InteractionMessage:
        if self.visibility is MessageVisibility.PRIVATE and not self.recipient_ids:
            raise ValueError("private interaction message requires recipients")
        transactional = self.kind in {
            MessageKind.INTERPROVINCIAL_PROPOSAL,
            MessageKind.PROVINCE_AUTOMAKER_PACKAGE,
            MessageKind.AUTOMAKER_PROVINCE_INTENT,
            MessageKind.AUTOMAKER_COUNTEROFFER,
            MessageKind.RESOURCE_REALLOCATION,
            MessageKind.TRANSACTION_RESPONSE,
        }
        if transactional != bool(self.session_id and self.transaction_state):
            raise ValueError("transaction messages require session and state")
        return self


class ReconsiderationCondition(DomainModel):
    condition_id: str
    source: Literal["message", "event", "environment", "time", "transaction"]
    field: str
    operator: Literal["exists", "gt", "gte", "lt", "lte", "eq"]
    threshold: float | int | str | bool | None = None
    action_if_met: str
    evidence_refs: list[str] = Field(default_factory=list, max_length=6)


class AgentTickDecision(DomainModel):
    schema_version: Literal["agent-tick-decision-v1"] = "agent-tick-decision-v1"
    decision_id: str
    branch_id: str
    tick: MacroTick
    wave: InteractionWave
    agent_kind: AgentKindM34
    agent_id: str
    inbox_id: str
    engagement: EngagementMode
    attended_message_ids: list[str] = Field(default_factory=list, max_length=100)
    noticed_facts: list[str] = Field(default_factory=list, max_length=12)
    province_action: ProvinceQuarterAction | None = None
    automaker_action: AutomakerQuarterAction | None = None
    outgoing_messages: list[InteractionMessage] = Field(default_factory=list, max_length=10)
    deferred_until_tick: MacroTick | None = None
    no_action_reason: str | None = Field(default=None, max_length=240)
    alternatives: list[str] = Field(default_factory=list, max_length=6)
    opportunity_costs: list[str] = Field(default_factory=list, max_length=6)
    reconsideration_conditions: list[ReconsiderationCondition] = Field(
        default_factory=list, max_length=8
    )
    evidence_refs: list[str] = Field(default_factory=list, max_length=12)
    fallback_used: bool = False
    fallback_reason: str | None = Field(default=None, max_length=240)

    @model_validator(mode="after")
    def valid_identity_and_output(self) -> AgentTickDecision:
        if self.agent_kind is AgentKindM34.PROVINCE:
            if self.province_action and self.province_action.province_code != self.agent_id:
                raise ValueError("province action must match decision agent")
            if self.automaker_action:
                raise ValueError("province decision cannot contain automaker action")
            province_messages = sum(
                item.kind is MessageKind.INTERPROVINCIAL_PROPOSAL for item in self.outgoing_messages
            )
            enterprise_messages = sum(
                item.kind is MessageKind.PROVINCE_AUTOMAKER_PACKAGE
                for item in self.outgoing_messages
            )
            if province_messages > 2 or enterprise_messages > 2:
                raise ValueError("province per-tick initiation budget exceeded")
        elif self.agent_kind is AgentKindM34.AUTOMAKER:
            if self.automaker_action and self.automaker_action.automaker_id != self.agent_id:
                raise ValueError("automaker action must match decision agent")
            if self.province_action:
                raise ValueError("automaker decision cannot contain province action")
            if len(self.outgoing_messages) > 5:
                raise ValueError("automaker per-tick interaction budget exceeded")
        if self.fallback_used != bool(self.fallback_reason):
            raise ValueError("fallback reason must agree with fallback flag")
        return self


class InteractionSession(DomainModel):
    schema_version: Literal["interaction-session-v1"] = "interaction-session-v1"
    session_id: str
    branch_id: str
    tick: MacroTick
    participant_ids: list[str] = Field(min_length=2, max_length=2)
    initiator_id: str
    state: TransactionState
    message_ids: list[str] = Field(min_length=1, max_length=20)
    condition_rounds: int = Field(default=0, ge=0, le=2)
    reserved_resource: float = Field(default=0, ge=0, le=1)
    settled_contribution: float = Field(default=0, ge=0, le=1)
    evidence_refs: list[str] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def valid_participants(self) -> InteractionSession:
        if len(set(self.participant_ids)) != 2 or self.initiator_id not in self.participant_ids:
            raise ValueError("interaction session requires two distinct participants")
        if self.state is not TransactionState.SETTLED and self.settled_contribution != 0:
            raise ValueError("only settled sessions contribute to the environment")
        return self


class InteractionMarket(DomainModel):
    schema_version: Literal["interaction-market-v1"] = "interaction-market-v1"
    experiment_id: str
    branch_id: str | None = None
    tick: MacroTick | None = None
    messages: list[InteractionMessage] = Field(default_factory=list)
    sessions: list[InteractionSession] = Field(default_factory=list)
    state_counts: dict[TransactionState, int] = Field(default_factory=dict)
    settled_count: int = Field(default=0, ge=0)
    resource_reallocation_count: int = Field(default=0, ge=0)
    fallback_count: int = Field(default=0, ge=0)
    budget_exhausted: bool = False


class QuarterSettlement(DomainModel):
    schema_version: Literal["quarter-settlement-v1"] = "quarter-settlement-v1"
    branch_id: str
    tick: MacroTick
    province_states: dict[str, ProvinceState]
    automaker_states: dict[str, AutomakerState]
    national_metrics: NationalMetrics
    mechanism_totals: dict[str, float] = Field(default_factory=dict)
    active_event_ids: list[str] = Field(default_factory=list, max_length=3)
    settled_session_ids: list[str] = Field(default_factory=list, max_length=500)
    state_hash: str


class TickCheckpoint(FrozenDomainModel):
    schema_version: Literal["tick-checkpoint-v1"] = "tick-checkpoint-v1"
    checkpoint_id: str
    experiment_id: str
    branch_id: str
    tick: MacroTick
    parent_checkpoint_id: str
    settlement: QuarterSettlement
    decision_ids: list[str]
    message_ids: list[str]
    session_ids: list[str]
    resource_hash: str
    state_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BranchRuntimeStateV9(DomainModel):
    schema_version: Literal["branch-v9"] = "branch-v9"
    branch_id: str
    kind: BranchKind
    label: str
    parent_checkpoint_id: str
    policy: PolicyV4
    completed_ticks: list[MacroTick] = Field(default_factory=list)
    current_tick: MacroTick | None = None
    current_wave: InteractionWave | None = None
    checkpoints: dict[MacroTick, TickCheckpoint] = Field(default_factory=dict)
    province_resource_envelopes: dict[str, ProvinceResourceEnvelope] = Field(default_factory=dict)
    automaker_resource_envelopes: dict[str, AutomakerResourceEnvelope] = Field(default_factory=dict)
    remaining_province_budget: dict[str, float] = Field(default_factory=dict)
    remaining_automaker_budget: dict[str, float] = Field(default_factory=dict)
    inboxes: list[AuthorizedInbox] = Field(default_factory=list)
    decisions: list[AgentTickDecision] = Field(default_factory=list)
    messages: list[InteractionMessage] = Field(default_factory=list)
    sessions: list[InteractionSession] = Field(default_factory=list)
    latest_province_actions: dict[str, ProvinceQuarterAction] = Field(default_factory=dict)
    latest_automaker_actions: dict[str, AutomakerQuarterAction] = Field(default_factory=dict)
    province_states: dict[str, ProvinceState] = Field(default_factory=dict)
    automaker_states: dict[str, AutomakerState] = Field(default_factory=dict)
    national_metrics: NationalMetrics = Field(default_factory=NationalMetrics)
    mechanism_totals: dict[str, float] = Field(default_factory=dict)
    agent_invocations: list[AgentInvocationRecord] = Field(default_factory=list)
    interaction_budget_exhausted: bool = False

    @model_validator(mode="after")
    def completed_ticks_are_prefix(self) -> BranchRuntimeStateV9:
        if self.completed_ticks != list(MacroTick)[: len(self.completed_ticks)]:
            raise ValueError("completed ticks must be a unique MacroTick prefix")
        if set(self.checkpoints) != set(self.completed_ticks):
            raise ValueError("every completed tick requires exactly one checkpoint")
        return self


class MetricComparisonV10(DomainModel):
    control: float
    treatment: float
    delta: float


class ComparisonResultV10(DomainModel):
    schema_version: Literal["comparison-v10"] = "comparison-v10"
    experiment_id: str
    experiment_type: ExperimentType
    control_branch_id: str
    treatment_branch_id: str
    active_difference: Literal["policy", "event"]
    same_policy: bool
    same_event: bool
    baseline_checkpoint_id: str
    control_q4_checkpoint_id: str
    treatment_q4_checkpoint_id: str
    delta_gap: float
    gap_direction: Literal["narrowed", "widened", "unchanged"]
    national_metrics: dict[str, MetricComparisonV10]
    settled_interaction_delta: int
    fallback_count: int = Field(ge=0)
    conclusion: str
    central_review: str


class EventV10(DomainModel):
    schema_version: Literal["event-v10"] = "event-v10"
    event_id: str
    type: str
    experiment_id: str
    branch_id: str | None = None
    journey_step: JourneyStep
    tick: MacroTick | None = None
    wave: InteractionWave | None = None
    logical_sequence: int = Field(ge=0)
    message_id: str | None = None
    session_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class WorldStateV10(DomainModel):
    schema_version: Literal["world-state-v10"] = "world-state-v10"
    product_version: Literal["v3_2_m34"] = "v3_2_m34"
    experiment_id: str
    journey_step: JourneyStep
    status: V32ExperimentStatus
    interpretation: PolicyInterpretation
    design: ExperimentDesignV2 | None = None
    baseline: BaselineSnapshotV3 | None = None
    branches: dict[str, BranchRuntimeStateV9] = Field(default_factory=dict)
    relation_network: ProvinceRelationNetwork | None = None
    automaker_personas: dict[str, AutomakerSimulationPersona] = Field(default_factory=dict)
    seed: int = 20260812
    central_call_count: int = Field(default=1, ge=0, le=2)
    central_review: str | None = None
    versions: dict[str, str] = Field(
        default_factory=lambda: {
            "app": "1.0.0-m34",
            "mechanism": "nev-policy-env-v7",
            "event": "event-v10",
            "data": "nev-m29-2025-v2",
            "province_profile": "province-profile-v6",
            "automaker_profile": "automaker-profile-v2",
            "relation_network": "province-relation-network-v3",
            "agent_contract": "agent-tick-decision-v1",
            "product_version": "v3_2_m34",
        }
    )


class PresentationTimelineNodeV3(FrozenDomainModel):
    node_id: str
    sequence: int = Field(ge=0)
    kind: Literal["policy", "event", "wave", "settlement", "comparison"]
    tick: MacroTick | None = None
    wave: InteractionWave | None = None
    title: str
    timeline_position: float = Field(ge=0, le=1)
    interaction_count: int = Field(default=0, ge=0)
    fallback_count: int = Field(default=0, ge=0)
    source_event_ids: list[str] = Field(default_factory=list)
    source_hash: str


class PresentationTimelineV3(FrozenDomainModel):
    schema_version: Literal["presentation-timeline-v3"] = "presentation-timeline-v3"
    experiment_id: str
    product_version: Literal["v3_2_m34"] = "v3_2_m34"
    status: V32ExperimentStatus
    current_node_id: str
    nodes: list[PresentationTimelineNodeV3]
    completed_ticks: list[MacroTick]
    disclaimer: Literal["模拟季度与互动顺序，不代表现实响应日期"] = (
        "模拟季度与互动顺序，不代表现实响应日期"
    )
    source_world_hash: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PresentationProvinceValueV3(FrozenDomainModel):
    province_code: str = Field(pattern=r"^\d{2}$")
    control: float | None = Field(default=None, ge=0, le=100)
    treatment: float | None = Field(default=None, ge=0, le=100)
    delta: float | None = None


class PresentationInteractionSummaryV3(FrozenDomainModel):
    session_id: str
    branch_id: str
    tick: MacroTick
    participants: list[str] = Field(min_length=2, max_length=2)
    state: TransactionState
    message_count: int = Field(ge=1)
    summary: str
    fallback: bool = False


class PresentationBranchSnapshotV3(FrozenDomainModel):
    branch_id: str
    tick: MacroTick | None = None
    national_metrics: NationalMetrics
    checkpoint_id: str | None = None


class PresentationFrameV3(FrozenDomainModel):
    schema_version: Literal["presentation-frame-v3"] = "presentation-frame-v3"
    frame_id: str
    experiment_id: str
    sequence: int = Field(ge=0)
    kind: Literal["policy", "event", "wave", "settlement", "comparison"]
    tick: MacroTick | None = None
    wave: InteractionWave | None = None
    title: str
    summary: str
    disclaimer: Literal["模拟季度与互动顺序，不代表现实响应日期"] = (
        "模拟季度与互动顺序，不代表现实响应日期"
    )
    branches: dict[Literal["control", "treatment"], PresentationBranchSnapshotV3]
    province_values: list[PresentationProvinceValueV3]
    interactions: list[PresentationInteractionSummaryV3]
    spotlight_session_ids: list[str] = Field(default_factory=list, max_length=3)
    event_plan_ids: list[str] = Field(default_factory=list, max_length=3)
    evidence_refs: list[str] = Field(default_factory=list)
    source_hash: str
