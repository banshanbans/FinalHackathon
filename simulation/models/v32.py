from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, model_validator

from simulation.models.automaker import FacilityAction, ProvinceMarketAction
from simulation.models.base import DomainModel, FrozenDomainModel
from simulation.models.common import BranchKind
from simulation.models.province import ProvinceState, SubsidyMix
from simulation.models.scenario import SubsidyMixDelta
from simulation.models.world import NationalMetrics


class V32DataQuality(StrEnum):
    VERIFIED = "verified"
    PROXY = "proxy"
    SCENARIO_ASSUMPTION = "scenario_assumption"


class JourneyStep(StrEnum):
    POLICY_INPUT = "policy_input"
    CENTRAL_INTERPRETATION = "central_interpretation"
    EXPERIMENT_DESIGN = "experiment_design"
    BASELINE_CONFIRMATION = "baseline_confirmation"
    SIMULATION_RUN = "simulation_run"
    RESULT_REVIEW = "result_review"


class V32ExperimentStatus(StrEnum):
    AWAITING_INTERPRETATION_CONFIRMATION = "awaiting_interpretation_confirmation"
    AWAITING_DESIGN_CONFIRMATION = "awaiting_design_confirmation"
    AWAITING_BASELINE_CONFIRMATION = "awaiting_baseline_confirmation"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ExperimentType(StrEnum):
    POLICY_COMPARISON = "policy_comparison"
    POLICY_STRESS_TEST = "policy_stress_test"
    EVENT_COUNTERFACTUAL = "event_counterfactual"


class SimulationRound(StrEnum):
    PROVINCE_INITIAL = "province_initial"
    AUTOMAKER_INITIAL = "automaker_initial"
    PROVINCE_REVISION = "province_revision"
    AUTOMAKER_NEGOTIATION = "automaker_negotiation"
    PROVINCE_COUNTER_RESPONSE = "province_counter_response"
    AUTOMAKER_FINAL = "automaker_final"
    ENVIRONMENT_SETTLEMENT = "environment_settlement"

    @property
    def order(self) -> int:
        return list(type(self)).index(self)


class EventTriggerPoint(StrEnum):
    BEFORE_PROVINCE_INITIAL = "before_province_initial"
    AFTER_PROVINCE_INITIAL = "after_province_initial"
    AFTER_AUTOMAKER_INITIAL = "after_automaker_initial"


class EventIntensityV32(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @property
    def magnitude(self) -> float:
        return {self.LOW: 0.25, self.MEDIUM: 0.50, self.HIGH: 0.75}[self]


class TraceConfidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PolicyV4(FrozenDomainModel):
    schema_version: Literal["policy-v4"] = "policy-v4"
    policy_id: str
    reference_policy_year: Literal[2025] = 2025
    west_central_share: float = Field(ge=0, le=1)
    central_central_share: float = Field(ge=0, le=1)
    east_central_share: float = Field(ge=0, le=1)
    data_quality: Literal[V32DataQuality.SCENARIO_ASSUMPTION] = V32DataQuality.SCENARIO_ASSUMPTION

    def share_for_region(self, region: str) -> float:
        return {
            "west": self.west_central_share,
            "central": self.central_central_share,
            "east": self.east_central_share,
        }[region]


class PolicyInterpretation(DomainModel):
    schema_version: Literal["policy-interpretation-v1"] = "policy-interpretation-v1"
    interpretation_id: str
    source_text: str = Field(min_length=3, max_length=4000)
    policy_goals: list[str] = Field(min_length=1, max_length=8)
    target_subjects: list[str] = Field(min_length=1, max_length=8)
    policy_tools: list[str] = Field(min_length=1, max_length=10)
    executable_policy: PolicyV4
    execution_period: str
    core_constraints: list[str] = Field(default_factory=list, max_length=8)
    ambiguities: list[str] = Field(default_factory=list, max_length=8)
    unmodeled_clauses: list[str] = Field(default_factory=list, max_length=8)
    event_design_hints: list[str] = Field(default_factory=list, max_length=8)
    recommended_metrics: list[str] = Field(min_length=1, max_length=8)
    public_summary: str = Field(min_length=1, max_length=240)
    status: Literal["awaiting_confirmation", "confirmed"] = "awaiting_confirmation"


class EventPlan(DomainModel):
    schema_version: Literal["event-plan-v1"] = "event-plan-v1"
    event_plan_id: str
    template_id: str
    name: str
    description: str
    trigger_point: EventTriggerPoint
    advance_notice: bool = False
    informed_agent_types: list[Literal["province", "automaker"]] = Field(default_factory=list)
    affected_subjects: list[Literal["province", "automaker", "consumer", "supply_chain"]] = Field(
        min_length=1
    )
    mechanism_channels: list[str] = Field(min_length=1)
    branch_scope: Literal["both", "treatment_only"]
    intensity: EventIntensityV32 = EventIntensityV32.MEDIUM
    data_quality: Literal[V32DataQuality.SCENARIO_ASSUMPTION] = V32DataQuality.SCENARIO_ASSUMPTION
    evidence_refs: list[str] = Field(min_length=1, max_length=8)


class ExperimentDesign(DomainModel):
    schema_version: Literal["experiment-design-v1"] = "experiment-design-v1"
    experiment_type: ExperimentType
    control_policy: PolicyV4
    treatment_policy: PolicyV4
    event_plan: EventPlan | None = None
    status: Literal["confirmed"] = "confirmed"

    @model_validator(mode="after")
    def valid_active_difference(self) -> ExperimentDesign:
        same_policy = (
            self.control_policy.west_central_share,
            self.control_policy.central_central_share,
            self.control_policy.east_central_share,
        ) == (
            self.treatment_policy.west_central_share,
            self.treatment_policy.central_central_share,
            self.treatment_policy.east_central_share,
        )
        if self.experiment_type is ExperimentType.POLICY_COMPARISON:
            if same_policy or self.event_plan is not None:
                raise ValueError("policy comparison requires different policies and no event")
        elif self.experiment_type is ExperimentType.POLICY_STRESS_TEST:
            if same_policy or self.event_plan is None or self.event_plan.branch_scope != "both":
                raise ValueError(
                    "policy stress test requires different policies and one shared event"
                )
        elif (
            not same_policy
            or self.event_plan is None
            or self.event_plan.branch_scope != "treatment_only"
        ):
            raise ValueError(
                "event counterfactual requires identical policies and a treatment-only event"
            )
        return self


class QualityCount(DomainModel):
    quality: V32DataQuality
    field_count: int = Field(ge=0)
    explanation: str


class BaselineSnapshot(FrozenDomainModel):
    schema_version: Literal["baseline-snapshot-v2"] = "baseline-snapshot-v2"
    checkpoint_schema_version: Literal["checkpoint-v6"] = "checkpoint-v6"
    checkpoint_id: str
    state_hash: str
    province_count: Literal[31] = 31
    automaker_count: Literal[10] = 10
    baseline_year: Literal[2025] = 2025
    quality_counts: list[QualityCount]
    missing_value_policy: str
    uncovered_content: list[str] = Field(default_factory=list)
    data_version: str = "nev-m29-2025-v2"
    relation_network_version: str = "province-relation-network-v3"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ProvinceRelation(FrozenDomainModel):
    source_code: str = Field(pattern=r"^\d{2}$")
    target_code: str = Field(pattern=r"^\d{2}$")
    relation_type: Literal["observation", "competition", "coordination"]
    weight: float = Field(ge=0, le=1)
    data_quality: V32DataQuality = V32DataQuality.PROXY
    evidence_refs: list[str] = Field(min_length=1, max_length=4)


class ProvinceRelationNetwork(FrozenDomainModel):
    schema_version: Literal["province-relation-network-v3"] = "province-relation-network-v3"
    relations: list[ProvinceRelation]


class AutomakerSimulationPersona(FrozenDomainModel):
    schema_version: Literal["automaker-simulation-persona-v1"] = "automaker-simulation-persona-v1"
    automaker_id: str
    primary_price_band: Literal["mass_market", "mainstream", "premium"]
    technology_focus: str
    growth_goal: float = Field(ge=0, le=1)
    cashflow_constraint: float = Field(ge=0, le=1)
    capacity_pressure: float = Field(ge=0, le=1)
    channel_expansion_tendency: float = Field(ge=0, le=1)
    rd_investment_tendency: float = Field(ge=0, le=1)
    intelligent_driving_stage: float = Field(ge=0, le=1)
    new_capacity_willingness: float = Field(ge=0, le=1)
    subsidy_sensitivity: float = Field(ge=0, le=1)
    market_sensitivity: float = Field(ge=0, le=1)
    supply_chain_sensitivity: float = Field(ge=0, le=1)
    regulation_sensitivity: float = Field(ge=0, le=1)
    data_quality: Literal[V32DataQuality.PROXY] = V32DataQuality.PROXY
    summary: str


class ProvinceResourceEnvelope(FrozenDomainModel):
    schema_version: Literal["province-resource-envelope-v2"] = "province-resource-envelope-v2"
    envelope_id: str
    branch_id: str
    province_code: str = Field(pattern=r"^\d{2}$")
    available_policy_budget: float = Field(ge=0, le=1)
    consumer_cap: float = Field(ge=0, le=1)
    fixed_cost_cap: float = Field(ge=0, le=1)
    variable_cost_cap: float = Field(ge=0, le=1)
    fiscal_risk_limit: float = Field(ge=0, le=1)
    max_coordination_proposals: Literal[2] = 2
    max_active_matches: Literal[1] = 1
    max_enterprise_offers: Literal[2] = 2
    evidence_refs: list[str] = Field(min_length=1, max_length=8)


class AutomakerResourceEnvelope(FrozenDomainModel):
    schema_version: Literal["automaker-resource-envelope-v2"] = "automaker-resource-envelope-v2"
    envelope_id: str
    branch_id: str
    automaker_id: str
    national_market_budget: float = Field(gt=0, le=31)
    max_expand_provinces: int = Field(ge=1, le=31)
    facility_budget: float = Field(ge=0, le=3)
    max_facility_targets: int = Field(ge=0, le=3)
    cashflow_constraint: float = Field(ge=0, le=1)
    capacity_pressure: float = Field(ge=0, le=1)
    management_capacity: float = Field(ge=0, le=1)
    evidence_refs: list[str] = Field(min_length=1, max_length=8)


class ProvinceActionV5(DomainModel):
    schema_version: Literal["province-action-v7"] = "province-action-v7"
    action_id: str
    previous_action_id: str | None = None
    branch_id: str
    province_code: str = Field(pattern=r"^\d{2}$")
    round: Literal[SimulationRound.PROVINCE_INITIAL, SimulationRound.PROVINCE_REVISION]
    overall_support_intensity: float = Field(ge=0, le=1)
    subsidy_mix: SubsidyMix
    response_mode: Literal["maintain", "follow", "differentiate", "coordinate"]
    observed_peer_codes: list[str] = Field(default_factory=list, max_length=8)
    competition_peer_codes: list[str] = Field(default_factory=list, max_length=3)
    coordination_target_codes: list[str] = Field(default_factory=list, max_length=2)
    primary_policy_focus: Literal["consumer", "fixed_cost", "variable_cost", "balanced"] = (
        "balanced"
    )
    reason_codes: list[str] = Field(min_length=1, max_length=8)
    summary: str = Field(min_length=1, max_length=180)
    fallback_used: bool = False


class AutomakerProvinceSignal(DomainModel):
    schema_version: Literal["automaker-province-decision-v1"] = "automaker-province-decision-v1"
    signal_id: str
    action_id: str
    automaker_id: str
    province_code: str = Field(pattern=r"^\d{2}$")
    decision: Literal["expand", "maintain", "reduce"]
    investment_direction: Literal["increase", "maintain", "decrease"]
    investment_inclination: float = Field(ge=0, le=1)
    attraction_factors: list[str] = Field(min_length=1, max_length=4)
    primary_constraints: list[str] = Field(min_length=1, max_length=4)
    reconsideration_condition: str = Field(min_length=1, max_length=180)
    evidence_refs: list[str] = Field(min_length=1, max_length=8)


class AutomakerActionV2(DomainModel):
    schema_version: Literal["automaker-action-v5"] = "automaker-action-v5"
    action_id: str
    previous_action_id: str | None = None
    branch_id: str
    automaker_id: str
    round: Literal[
        SimulationRound.AUTOMAKER_INITIAL,
        SimulationRound.AUTOMAKER_NEGOTIATION,
        SimulationRound.AUTOMAKER_FINAL,
    ]
    province_market_actions: list[ProvinceMarketAction]
    province_signals: list[AutomakerProvinceSignal]
    facility_actions: list[FacilityAction] = Field(default_factory=list, max_length=3)
    enterprise_offer_responses: list[ProvinceEnterpriseOfferResponse] = Field(
        default_factory=list, max_length=80
    )
    primary_commitment: str = Field(min_length=1, max_length=180)
    simulated_roi_band: Literal["low", "medium", "high"]
    reason_codes: list[str] = Field(min_length=1, max_length=8)
    summary: str = Field(min_length=1, max_length=180)
    resource_envelope_id: str
    opportunity_costs: list[str] = Field(min_length=1, max_length=8)
    fallback_used: bool = False

    @model_validator(mode="after")
    def complete_national_action(self) -> AutomakerActionV2:
        province_codes = [item.province_code for item in self.province_market_actions]
        if len(province_codes) != 31 or len(set(province_codes)) != 31:
            raise ValueError("automaker action must cover 31 unique provinces")
        signal_codes = [item.province_code for item in self.province_signals]
        if len(signal_codes) != 31 or set(signal_codes) != set(province_codes):
            raise ValueError("automaker signals must cover the same 31 provinces")
        if any(item.action_id != self.action_id for item in self.province_signals):
            raise ValueError("automaker signals must reference their action")
        response_offer_ids = [item.offer_id for item in self.enterprise_offer_responses]
        if len(response_offer_ids) != len(set(response_offer_ids)):
            raise ValueError("automaker offer responses must be unique per offer")
        if any(item.automaker_id != self.automaker_id for item in self.enterprise_offer_responses):
            raise ValueError("automaker offer response must match action automaker")
        facility_codes = [item.province_code for item in self.facility_actions]
        if len(facility_codes) != len(set(facility_codes)):
            raise ValueError("facility actions must use unique provinces")
        return self


class DecisionObservation(DomainModel):
    source_type: Literal["policy", "province", "automaker", "event", "environment"]
    source_id: str
    observation_type: str
    summary: str
    data_quality: V32DataQuality
    evidence_refs: list[str] = Field(default_factory=list, max_length=6)


class ActionDelta(DomainModel):
    field: str
    before: str | float | int | None
    after: str | float | int | None
    display_summary: str
    trigger_refs: list[str] = Field(min_length=1, max_length=8)


class DecisionReason(DomainModel):
    decision: str
    trigger_ref: str
    affected_fields: list[str] = Field(min_length=1, max_length=8)
    summary: str


class RejectedAlternative(DomainModel):
    alternative: str
    rejection_basis: str
    evidence_refs: list[str] = Field(min_length=1, max_length=6)


class ChangeCondition(DomainModel):
    field: str
    operator: Literal["gt", "gte", "lt", "lte", "eq"]
    threshold: float | int | str
    action_if_met: str
    evidence_refs: list[str] = Field(min_length=1, max_length=6)


class OpportunityCost(DomainModel):
    chosen_action: str
    forgone_or_delayed_action: str
    resource_source: str
    summary: str


class DecisionTraceBase(DomainModel):
    schema_version: Literal["decision-trace-v4"] = "decision-trace-v4"
    trace_id: str
    branch_id: str
    agent_id: str
    round: SimulationRound
    primary_goal: str
    primary_choice: str = Field(min_length=1, max_length=180)
    constraints: list[str] = Field(default_factory=list, max_length=8)
    observations: list[DecisionObservation] = Field(default_factory=list, max_length=20)
    initial_action_id: str | None = None
    alternatives_considered: list[str] = Field(default_factory=list, max_length=5)
    final_action_id: str
    action_delta: list[ActionDelta] = Field(default_factory=list, max_length=20)
    decision_reasons: list[DecisionReason] = Field(default_factory=list, max_length=12)
    rejected_alternatives: list[RejectedAlternative] = Field(default_factory=list, max_length=8)
    change_conditions: list[ChangeCondition] = Field(default_factory=list, max_length=8)
    opportunity_costs: list[OpportunityCost] = Field(default_factory=list, max_length=8)
    coordination_proposal_refs: list[str] = Field(default_factory=list, max_length=4)
    received_proposal_refs: list[str] = Field(default_factory=list, max_length=30)
    coordination_response_refs: list[str] = Field(default_factory=list, max_length=30)
    coordination_match_refs: list[str] = Field(default_factory=list, max_length=30)
    fallback_reason: str | None = None
    fallback_scope: str | None = None
    reasoning_summary: str = Field(min_length=1, max_length=320)
    evidence_refs: list[str] = Field(default_factory=list, max_length=12)
    data_quality: V32DataQuality
    confidence: TraceConfidence
    confidence_basis: str
    affected_agents: list[str] = Field(default_factory=list, max_length=40)


class ProvinceDecisionTrace(DecisionTraceBase):
    trace_type: Literal["province"] = "province"
    peer_signals: list[str] = Field(default_factory=list, max_length=8)
    enterprise_signals: list[str] = Field(default_factory=list, max_length=12)


class AutomakerDecisionTrace(DecisionTraceBase):
    trace_type: Literal["automaker"] = "automaker"
    received_enterprise_offer_refs: list[str] = Field(default_factory=list, max_length=80)
    enterprise_offer_response_refs: list[str] = Field(default_factory=list, max_length=80)


class ProvinceEnterpriseOffer(DomainModel):
    schema_version: Literal["province-enterprise-offer-v1"] = "province-enterprise-offer-v1"
    offer_id: str
    branch_id: str
    source_province_code: str = Field(pattern=r"^\d{2}$")
    target_automaker_id: str
    priority: int = Field(ge=1, le=2)
    channel_commitment_share: float = Field(ge=0, le=1)
    industry_coordination_share: float = Field(ge=0, le=1)
    offered_support_scope: Literal["consumer", "fixed_cost", "variable_cost", "balanced"]
    activation_condition: str = Field(min_length=1, max_length=180)
    opportunity_cost: str = Field(min_length=1, max_length=240)
    public_reason: str = Field(min_length=1, max_length=240)
    evidence_refs: list[str] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def has_real_commitment(self) -> ProvinceEnterpriseOffer:
        if self.channel_commitment_share + self.industry_coordination_share <= 0:
            raise ValueError("enterprise offer must commit channel or industry capacity")
        return self


class ProvinceEnterpriseOfferResponse(DomainModel):
    schema_version: Literal["automaker-enterprise-offer-response-v2"] = (
        "automaker-enterprise-offer-response-v2"
    )
    response_id: str
    branch_id: str
    offer_id: str
    automaker_id: str
    decision: Literal["accept", "reject", "counteroffer"]
    rejection_reason: str | None = None
    counter_offer_id: str | None = None
    opportunity_cost: str = Field(min_length=1, max_length=240)
    evidence_refs: list[str] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def explains_rejection(self) -> ProvinceEnterpriseOfferResponse:
        if self.decision == "reject" and not self.rejection_reason:
            raise ValueError("rejected enterprise offer requires a reason")
        if self.decision == "accept" and self.rejection_reason:
            raise ValueError("accepted enterprise offer cannot contain a rejection reason")
        if self.decision == "counteroffer" and not self.counter_offer_id:
            raise ValueError("counteroffer response requires a counter offer")
        if self.decision != "counteroffer" and self.counter_offer_id:
            raise ValueError("only counteroffer responses may reference a counter offer")
        return self


class AutomakerCounterOffer(DomainModel):
    """A non-monetary condition that reallocates an existing provincial resource package."""

    schema_version: Literal["automaker-counter-offer-v1"] = "automaker-counter-offer-v1"
    counter_offer_id: str
    branch_id: str
    offer_id: str
    automaker_id: str
    province_code: str = Field(pattern=r"^\d{2}$")
    required_channel_share: float = Field(ge=0, le=1)
    required_industry_share: float = Field(ge=0, le=1)
    required_policy_focus: Literal["consumer", "fixed_cost", "variable_cost", "balanced"]
    validity_condition: str = Field(min_length=1, max_length=180)
    opportunity_cost: str = Field(min_length=1, max_length=240)
    evidence_refs: list[str] = Field(min_length=1, max_length=8)


class ProvinceCounterOfferResponse(DomainModel):
    schema_version: Literal["province-counter-offer-response-v1"] = (
        "province-counter-offer-response-v1"
    )
    response_id: str
    branch_id: str
    counter_offer_id: str
    province_code: str = Field(pattern=r"^\d{2}$")
    decision: Literal["accept", "reject"]
    rejection_reason: str | None = None
    opportunity_cost: str = Field(min_length=1, max_length=240)
    change_condition: str = Field(min_length=1, max_length=180)
    evidence_refs: list[str] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def rejection_is_explained(self) -> ProvinceCounterOfferResponse:
        if self.decision == "reject" and not self.rejection_reason:
            raise ValueError("rejected counter offer requires a reason")
        if self.decision == "accept" and self.rejection_reason:
            raise ValueError("accepted counter offer cannot contain a rejection reason")
        return self


class ProvinceCounterOfferResponseBatch(DomainModel):
    schema_version: Literal["province-counter-offer-response-batch-v1"] = (
        "province-counter-offer-response-batch-v1"
    )
    province_code: str = Field(pattern=r"^\d{2}$")
    responses: list[ProvinceCounterOfferResponse] = Field(default_factory=list, max_length=30)
    decision_reasons: list[DecisionReason] = Field(min_length=1, max_length=6)
    opportunity_costs: list[OpportunityCost] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def accepts_one_counter_offer(self) -> ProvinceCounterOfferResponseBatch:
        if sum(item.decision == "accept" for item in self.responses) > 1:
            raise ValueError("a province can accept at most one counter offer")
        if any(item.province_code != self.province_code for item in self.responses):
            raise ValueError("counter offer response province must match the batch")
        return self


class CompetitionOutcome(DomainModel):
    schema_version: Literal["competition-outcome-v1"] = "competition-outcome-v1"
    outcome_id: str
    branch_id: str
    automaker_id: str
    resource_type: Literal["channel_slot", "facility_slot"]
    winner_province_code: str = Field(pattern=r"^\d{2}$")
    loser_province_code: str = Field(pattern=r"^\d{2}$")
    winner_rank: int = Field(ge=1)
    loser_rank: int = Field(ge=1)
    relation_weight: float = Field(gt=0, le=1)
    loss_index: float = Field(ge=0, le=100)
    trigger_condition: str = Field(min_length=1, max_length=180)
    evidence_refs: list[str] = Field(min_length=1, max_length=8)


class TopKReallocation(DomainModel):
    schema_version: Literal["top-k-reallocation-v1"] = "top-k-reallocation-v1"
    reallocation_id: str
    branch_id: str
    automaker_id: str
    resource_type: Literal["channel_slot", "facility_slot"]
    released_province_code: str = Field(pattern=r"^\d{2}$")
    recipient_province_code: str = Field(pattern=r"^\d{2}$")
    reason: str = Field(min_length=1, max_length=180)
    evidence_refs: list[str] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def moves_between_distinct_provinces(self) -> TopKReallocation:
        if self.released_province_code == self.recipient_province_code:
            raise ValueError("Top-K reallocation requires distinct provinces")
        return self


class ProvinceUtility(DomainModel):
    schema_version: Literal["province-utility-v1"] = "province-utility-v1"
    utility_id: str
    branch_id: str
    province_code: str = Field(pattern=r"^\d{2}$")
    demand_index: float = Field(ge=0, le=100)
    industry_index: float = Field(ge=0, le=100)
    enterprise_gain: float = Field(ge=0, le=100)
    coordination_gain: float = Field(ge=0, le=100)
    fiscal_pressure: float = Field(ge=0, le=100)
    competition_loss: float = Field(ge=0, le=100)
    weights: dict[
        Literal["demand", "industry", "enterprise", "coordination", "fiscal", "competition"],
        float,
    ]
    utility_index: float = Field(ge=-100, le=100)
    evidence_refs: list[str] = Field(min_length=1, max_length=12)


class ProvinceEnterpriseMatch(DomainModel):
    schema_version: Literal["province-enterprise-match-v1", "province-enterprise-match-v2"] = (
        "province-enterprise-match-v2"
    )
    match_id: str
    branch_id: str
    offer_id: str
    response_id: str | None = None
    province_code: str = Field(pattern=r"^\d{2}$")
    automaker_id: str
    status: Literal["matched", "rejected", "resource_invalid"]
    channel_contribution: float = Field(ge=0)
    industry_contribution: float = Field(ge=0)
    cooperation_actions: list[
        Literal[
            "channel_expansion",
            "channel_maintenance",
            "facility_new_plant",
            "facility_expansion",
            "facility_delay",
            "industry_coordination",
            "policy_support",
        ]
    ] = Field(default_factory=list, max_length=6)
    action_summary: str = ""
    province_action_ref: str | None = None
    automaker_action_ref: str | None = None
    evidence_refs: list[str] = Field(min_length=1, max_length=8)
    summary: str

    @model_validator(mode="after")
    def concrete_actions_only_for_matches(self) -> ProvinceEnterpriseMatch:
        if self.schema_version == "province-enterprise-match-v1":
            return self
        if self.status == "matched":
            if not self.cooperation_actions or not self.action_summary:
                raise ValueError("matched enterprise cooperation requires concrete actions")
            if not self.province_action_ref or not self.automaker_action_ref:
                raise ValueError("matched enterprise cooperation requires both final action refs")
        elif self.cooperation_actions:
            raise ValueError("unmatched enterprise cooperation cannot expose applied actions")
        return self


DecisionTrace = Annotated[
    ProvinceDecisionTrace | AutomakerDecisionTrace, Field(discriminator="trace_type")
]


class ProvinceCoordinationProposal(DomainModel):
    schema_version: Literal["province-coordination-proposal-v1"] = (
        "province-coordination-proposal-v1"
    )
    proposal_id: str
    branch_id: str
    source_province_code: str = Field(pattern=r"^\d{2}$")
    target_province_code: str = Field(pattern=r"^\d{2}$")
    priority: int = Field(ge=1, le=2)
    basis_type: Literal["existing_relation", "inferred_from_context"]
    cooperation_focus: Literal["supply_chain", "research_testing", "operating_network"]
    offered_capability: str
    requested_capability: str
    source_success_delta: SubsidyMixDelta
    target_success_delta: SubsidyMixDelta
    fallback_delta: SubsidyMixDelta
    evidence_completeness: float = Field(ge=0, le=1)
    complementarity: float = Field(ge=0, le=1)
    goal_alignment: float = Field(ge=0, le=1)
    public_reason: str = Field(min_length=1, max_length=240)
    evidence_refs: list[str] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def valid_partner_and_basis(self) -> ProvinceCoordinationProposal:
        if self.source_province_code == self.target_province_code:
            raise ValueError("province cannot propose coordination with itself")
        if self.basis_type == "inferred_from_context" and len(self.evidence_refs) < 2:
            raise ValueError("inferred coordination requires at least two context references")
        return self


class ProvinceProposalBatch(DomainModel):
    schema_version: Literal["province-coordination-proposal-batch-v1"] = (
        "province-coordination-proposal-batch-v1"
    )
    province_code: str = Field(pattern=r"^\d{2}$")
    proposed_action: ProvinceActionV5
    proposals: list[ProvinceCoordinationProposal] = Field(default_factory=list, max_length=2)
    enterprise_decision: Literal["offer", "no_offer"] = "no_offer"
    enterprise_no_offer_reason: str | None = None
    enterprise_offers: list[ProvinceEnterpriseOffer] = Field(default_factory=list, max_length=2)
    decision_reasons: list[DecisionReason] = Field(min_length=1, max_length=8)
    rejected_alternatives: list[RejectedAlternative] = Field(default_factory=list, max_length=6)
    change_conditions: list[ChangeCondition] = Field(min_length=1, max_length=6)
    opportunity_costs: list[OpportunityCost] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def valid_proposals(self) -> ProvinceProposalBatch:
        if any(item.source_province_code != self.province_code for item in self.proposals):
            raise ValueError("proposal source must match the batch province")
        priorities = [item.priority for item in self.proposals]
        targets = [item.target_province_code for item in self.proposals]
        if len(priorities) != len(set(priorities)) or len(targets) != len(set(targets)):
            raise ValueError("proposal priorities and targets must be unique")
        enterprise_priorities = [item.priority for item in self.enterprise_offers]
        enterprise_targets = [item.target_automaker_id for item in self.enterprise_offers]
        if any(item.source_province_code != self.province_code for item in self.enterprise_offers):
            raise ValueError("enterprise offer source must match the batch province")
        if self.enterprise_decision == "offer" and not self.enterprise_offers:
            raise ValueError("offer decision requires one or two enterprise offers")
        if self.enterprise_decision == "no_offer" and (
            self.enterprise_offers or not self.enterprise_no_offer_reason
        ):
            raise ValueError("no-offer decision requires a reason and no offers")
        if len(enterprise_priorities) != len(set(enterprise_priorities)) or len(
            enterprise_targets
        ) != len(set(enterprise_targets)):
            raise ValueError("enterprise offer priorities and targets must be unique")
        return self


class ProvinceCoordinationResponse(DomainModel):
    schema_version: Literal["province-coordination-response-v1"] = (
        "province-coordination-response-v1"
    )
    response_id: str
    branch_id: str
    proposal_id: str
    responding_province_code: str = Field(pattern=r"^\d{2}$")
    decision: Literal["accept", "reject"]
    conditions_checked: list[str] = Field(min_length=1, max_length=8)
    rejection_reason: str | None = None
    opportunity_cost: str = Field(min_length=1, max_length=240)
    final_action_ref: str
    evidence_refs: list[str] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def rejection_is_explained(self) -> ProvinceCoordinationResponse:
        if self.decision == "reject" and not self.rejection_reason:
            raise ValueError("rejected coordination requires a reason")
        if self.decision == "accept" and self.rejection_reason:
            raise ValueError("accepted coordination cannot contain a rejection reason")
        return self


class ProvinceResponseBatch(DomainModel):
    schema_version: Literal["province-coordination-response-batch-v1"] = (
        "province-coordination-response-batch-v1"
    )
    province_code: str = Field(pattern=r"^\d{2}$")
    base_final_action: ProvinceActionV5
    responses: list[ProvinceCoordinationResponse] = Field(default_factory=list, max_length=30)
    decision_reasons: list[DecisionReason] = Field(min_length=1, max_length=8)
    opportunity_costs: list[OpportunityCost] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def accepts_at_most_one(self) -> ProvinceResponseBatch:
        if sum(item.decision == "accept" for item in self.responses) > 1:
            raise ValueError("a province can accept at most one coordination proposal")
        if any(item.responding_province_code != self.province_code for item in self.responses):
            raise ValueError("response province must match the batch province")
        return self


class CoordinationRecord(DomainModel):
    schema_version: Literal["province-coordination-match-v2"] = "province-coordination-match-v2"
    coordination_id: str
    proposal_id: str
    response_id: str | None = None
    eligibility_ref: str
    branch_id: str
    left_province_code: str
    right_province_code: str
    status: Literal["matched", "unmatched", "rejected", "resource_invalid"]
    contribution: float = Field(ge=0)
    applied_action_refs: list[str] = Field(default_factory=list, max_length=2)
    evidence_refs: list[str] = Field(min_length=1, max_length=8)
    summary: str


class AgentInvocationRecord(DomainModel):
    schema_version: Literal["agent-invocation-v1"] = "agent-invocation-v1"
    invocation_id: str
    branch_id: str
    agent_id: str
    kind: str
    model: str
    run_mode: Literal["fake", "cache", "live", "fallback"]
    input_hash: str
    output_hash: str
    output_schema: str
    fallback_used: bool = False


class ConsumerResponseRecord(DomainModel):
    response_id: str
    branch_id: str
    event_plan_id: str
    affected_province_codes: list[str]
    demand_effect_index: float
    summary: str


class BranchRuntimeState(DomainModel):
    schema_version: Literal["branch-v8"] = "branch-v8"
    branch_id: str
    kind: BranchKind
    label: str
    parent_checkpoint_id: str
    policy: PolicyV4
    event_applied: bool = False
    current_round: SimulationRound | None = None
    completed_rounds: list[SimulationRound] = Field(default_factory=list)
    province_resource_envelopes: dict[str, ProvinceResourceEnvelope] = Field(default_factory=dict)
    automaker_resource_envelopes: dict[str, AutomakerResourceEnvelope] = Field(default_factory=dict)
    province_initial_actions: dict[str, ProvinceActionV5] = Field(default_factory=dict)
    province_proposed_actions: dict[str, ProvinceActionV5] = Field(default_factory=dict)
    province_proposal_batches: dict[str, ProvinceProposalBatch] = Field(default_factory=dict)
    province_response_batches: dict[str, ProvinceResponseBatch] = Field(default_factory=dict)
    province_final_actions: dict[str, ProvinceActionV5] = Field(default_factory=dict)
    automaker_initial_actions: dict[str, AutomakerActionV2] = Field(default_factory=dict)
    automaker_negotiation_actions: dict[str, AutomakerActionV2] = Field(default_factory=dict)
    automaker_final_actions: dict[str, AutomakerActionV2] = Field(default_factory=dict)
    province_states: dict[str, ProvinceState] = Field(default_factory=dict)
    national_metrics: NationalMetrics = Field(default_factory=NationalMetrics)
    decision_traces: list[DecisionTrace] = Field(default_factory=list)
    province_coordination_proposals: list[ProvinceCoordinationProposal] = Field(
        default_factory=list
    )
    province_coordination_responses: list[ProvinceCoordinationResponse] = Field(
        default_factory=list
    )
    coordination_records: list[CoordinationRecord] = Field(default_factory=list)
    province_enterprise_offers: list[ProvinceEnterpriseOffer] = Field(default_factory=list)
    province_enterprise_offer_responses: list[ProvinceEnterpriseOfferResponse] = Field(
        default_factory=list
    )
    province_enterprise_matches: list[ProvinceEnterpriseMatch] = Field(default_factory=list)
    automaker_counter_offers: list[AutomakerCounterOffer] = Field(default_factory=list)
    province_counter_offer_responses: list[ProvinceCounterOfferResponse] = Field(
        default_factory=list
    )
    competition_outcomes: list[CompetitionOutcome] = Field(default_factory=list)
    top_k_reallocations: list[TopKReallocation] = Field(default_factory=list)
    province_utilities: dict[str, ProvinceUtility] = Field(default_factory=dict)
    consumer_responses: list[ConsumerResponseRecord] = Field(default_factory=list)
    mechanism_totals: dict[str, float] = Field(default_factory=dict)
    agent_invocations: list[AgentInvocationRecord] = Field(default_factory=list)

    @model_validator(mode="after")
    def completed_rounds_are_a_unique_prefix(self) -> BranchRuntimeState:
        expected = list(SimulationRound)[: len(self.completed_rounds)]
        if self.completed_rounds != expected:
            raise ValueError("completed rounds must be a unique SimulationRound prefix")
        if self.current_round is not None:
            allowed = set(self.completed_rounds[-1:])
            if len(self.completed_rounds) < len(SimulationRound):
                allowed.add(list(SimulationRound)[len(self.completed_rounds)])
            if self.current_round not in allowed:
                raise ValueError("current round must be the completed tail or next round")
        return self


class WorldStateV6(DomainModel):
    schema_version: Literal["world-state-v9"] = "world-state-v9"
    product_version: Literal["v3_2_m32"] = "v3_2_m32"
    experiment_id: str
    journey_step: JourneyStep
    status: V32ExperimentStatus
    interpretation: PolicyInterpretation
    design: ExperimentDesign | None = None
    baseline: BaselineSnapshot | None = None
    branches: dict[str, BranchRuntimeState] = Field(default_factory=dict)
    relation_network: ProvinceRelationNetwork | None = None
    automaker_personas: dict[str, AutomakerSimulationPersona] = Field(default_factory=dict)
    seed: int = 20260812
    versions: dict[str, str] = Field(
        default_factory=lambda: {
            "app": "0.9.0",
            "mechanism": "nev-policy-env-v6",
            "event": "event-v9",
            "data": "nev-m29-2025-v2",
            "province_profile": "province-profile-v6",
            "automaker_profile": "automaker-profile-v2",
            "relation_network": "province-relation-network-v3",
            "agent_contract": "m32-competition-negotiation-v1",
            "product_version": "v3_2_m32",
        }
    )


class MetricComparison(DomainModel):
    control: float
    treatment: float
    delta: float


class ProvinceOutcomeDelta(DomainModel):
    province_code: str
    province_name: str
    development_delta: float
    demand_delta: float
    industry_delta: float
    fiscal_pressure_delta: float


class AutomakerOutcomeDelta(DomainModel):
    automaker_id: str
    display_name: str
    changed_province_count: int
    maximum_intensity_delta: float
    facility_changed: bool


class MechanismNode(DomainModel):
    node_type: Literal["policy", "agent_action", "coordination_match", "environment", "metric"]
    ref: str
    label: str
    contribution: float | None = None


class MechanismChain(DomainModel):
    category: Literal["positive", "cost", "reversal_risk"]
    title: str
    nodes: list[MechanismNode] = Field(min_length=3, max_length=8)
    contribution_delta: float
    evidence_refs: list[str] = Field(default_factory=list)


class SensitivityFinding(DomainModel):
    input_group: str
    direction: str
    affected_metric: str
    local_effect: float
    method_note: str = "固定 Agent 行动的一次一项局部敏感性，不代表统计置信区间。"


class ComparisonResultV6(DomainModel):
    schema_version: Literal["comparison-v9"] = "comparison-v9"
    experiment_id: str
    experiment_type: ExperimentType
    control_branch_id: str
    treatment_branch_id: str
    conclusion: str
    gap_direction: Literal["narrowed", "widened", "unchanged"]
    delta_gap: float
    national_metrics: dict[str, MetricComparison]
    province_deltas: list[ProvinceOutcomeDelta]
    automaker_deltas: list[AutomakerOutcomeDelta]
    top_beneficiaries: list[str]
    top_pressured: list[str]
    fiscal_tradeoff: str
    event_robustness: str
    mechanism_chains: list[MechanismChain]
    sensitivity_findings: list[SensitivityFinding]
    active_difference: Literal["policy", "event"]
    same_policy: bool
    same_event: bool
    checkpoint_id: str
    competition_loss_delta: float = 0
    coordination_gain_delta: float = 0
    top_k_reallocation_count: int = 0
    counteroffer_acceptance_rate: float = 0


class EventV6(DomainModel):
    schema_version: Literal["event-v9"] = "event-v9"
    event_id: str
    type: str
    experiment_id: str
    branch_id: str | None = None
    journey_step: JourneyStep
    round: SimulationRound | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class StrategyMarketSnapshot(DomainModel):
    schema_version: Literal["strategy-market-v3"] = "strategy-market-v3"
    experiment_id: str
    branches: dict[str, BranchRuntimeState]
    automaker_signal_count: int
    proposal_count: int
    response_count: int
    matched_count: int
    enterprise_offer_count: int
    enterprise_response_count: int
    enterprise_matched_count: int
    competition_outcome_count: int = 0
    counteroffer_count: int = 0
    counteroffer_response_count: int = 0
    top_k_reallocation_count: int = 0


class PresentationScene(DomainModel):
    scene: Literal[
        "policy_input",
        "enterprise_feedback",
        "province_coordination",
        "resource_reallocation",
        "policy_conclusion",
    ]
    title: str
    summary: str
    evidence_refs: list[str] = Field(min_length=1, max_length=8)


class PresentationSummary(DomainModel):
    schema_version: Literal["presentation-summary-v1"] = "presentation-summary-v1"
    experiment_id: str
    scenes: list[PresentationScene] = Field(min_length=5, max_length=5)
