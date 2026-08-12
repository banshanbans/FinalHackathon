from typing import Literal

from pydantic import Field, JsonValue

from simulation.models.action import MechanismContribution
from simulation.models.automaker import AutomakerAction, AutomakerProfile, AutomakerState
from simulation.models.base import DomainModel
from simulation.models.central import (
    CentralIntervention,
    CentralInterventionProposal,
    CentralReview,
    CentralSubsidyDirective,
    PolicyFieldChange,
)
from simulation.models.common import BranchKind, ComparisonMode, ExperimentStatus, Phase, RunMode
from simulation.models.policy import PolicySchema
from simulation.models.province import (
    ProvinceAction,
    ProvinceDecisionPersona,
    ProvinceFeedback,
    ProvinceProfile,
    ProvinceState,
)
from simulation.models.scenario import (
    CoordinationMatch,
    EventScenario,
    EventScenarioDiff,
    ProvinceEventResponse,
    ProvinceEventSignal,
)


class NationalMetrics(DomainModel):
    schema_version: str = "national-nev-metrics-v1"
    regional_development_gap: float = Field(default=0, ge=0, le=100)
    central_fiscal_burden: float = Field(default=0, ge=0, le=100)
    local_fiscal_pressure: float = Field(default=50, ge=0, le=100)
    nev_demand: float = Field(default=50, ge=0, le=100)
    new_investment_concentration: float = Field(default=0, ge=0, le=100)
    industrial_agglomeration: float = Field(default=0, ge=0, le=100)


class BatteryIndustryNode(DomainModel):
    province_code: str = Field(pattern=r"^\d{2}$")
    node_strength: float = Field(ge=0, le=1)
    node_type: str


class ProvinceBatteryAccess(DomainModel):
    province_code: str = Field(pattern=r"^\d{2}$")
    nearest_node_code: str = Field(pattern=r"^\d{2}$")
    distance_index: float = Field(ge=0, le=1)


class VersionInfo(DomainModel):
    data: str
    mechanism: str
    prompt: str
    model: str
    app: str = "0.5.0"


class WorldState(DomainModel):
    schema_version: str = "world-state-v5"
    experiment_id: str
    branch_id: str = "control"
    branch_kind: BranchKind = BranchKind.CONTROL
    parent_checkpoint_id: str | None = None
    phase: Phase = Phase.SETUP
    status: ExperimentStatus = ExperimentStatus.AWAITING_APPROVAL
    run_mode: RunMode = RunMode.FAKE
    comparison_mode: ComparisonMode = ComparisonMode.POLICY_INTERVENTION
    policy: PolicySchema
    directive: CentralSubsidyDirective
    national_metrics: NationalMetrics = Field(default_factory=NationalMetrics)
    province_profiles: dict[str, ProvinceProfile]
    province_personas: dict[str, ProvinceDecisionPersona]
    province_states: dict[str, ProvinceState]
    province_actions: dict[str, ProvinceAction] = Field(default_factory=dict)
    province_action_lineage: dict[str, list[ProvinceAction]] = Field(default_factory=dict)
    province_feedback: dict[str, ProvinceFeedback] = Field(default_factory=dict)
    automaker_profiles: dict[str, AutomakerProfile]
    automaker_states: dict[str, AutomakerState]
    automaker_actions: dict[str, AutomakerAction] = Field(default_factory=dict)
    automaker_action_lineage: dict[str, list[AutomakerAction]] = Field(default_factory=dict)
    contributions: dict[str, MechanismContribution] = Field(default_factory=dict)
    fixed_variable_thresholds: dict[str, JsonValue] = Field(default_factory=dict)
    approved_event_scenario: EventScenario | None = None
    event_applied: bool = False
    scenario_application_branch_ids: list[str] = Field(default_factory=list)
    event_exposure_by_province: dict[str, float] = Field(default_factory=dict)
    province_event_signals: dict[str, ProvinceEventSignal] = Field(default_factory=dict)
    province_event_responses: dict[str, ProvinceEventResponse] = Field(default_factory=dict)
    coordination_matches: list[CoordinationMatch] = Field(default_factory=list)
    fallback_event_provinces: list[str] = Field(default_factory=list)
    fallback_provinces: list[str] = Field(default_factory=list)
    fallback_automakers: list[str] = Field(default_factory=list)
    intervention_proposals: list[CentralInterventionProposal] = Field(default_factory=list)
    intervention_decision: str | None = None
    approved_intervention: CentralIntervention | None = None
    central_review: CentralReview | None = None
    versions: VersionInfo
    seed: int


class MetricDelta(DomainModel):
    control: float
    treatment: float
    delta: float


class ProvinceDelta(DomainModel):
    province_code: str
    province_name: str
    development_delta: float
    demand_delta: float
    industry_activity_delta: float
    fiscal_pressure_delta: float


class StrategyFieldChange(DomainModel):
    path: str
    from_value: JsonValue
    to_value: JsonValue


class ProvinceStrategyTransition(DomainModel):
    province_code: str = Field(pattern=r"^\d{2}$")
    province_name: str
    control_action_id: str
    treatment_action_id: str
    changed: bool
    changes: list[StrategyFieldChange] = Field(default_factory=list)


class AutomakerStrategyTransition(DomainModel):
    automaker_id: str
    display_name: str
    control_action_id: str
    treatment_action_id: str
    changed_province_allocations: int = Field(ge=0, le=31)
    facility_changes: list[StrategyFieldChange] = Field(default_factory=list)


class ActiveDifferenceProof(DomainModel):
    comparison_mode: ComparisonMode
    checkpoint_id: str
    same_policy: bool
    same_event: bool
    active_difference: Literal["policy", "event"]


class ProvinceEventTransition(DomainModel):
    province_code: str = Field(pattern=r"^\d{2}$")
    control_response_id: str | None = None
    treatment_response_id: str | None = None
    control_mode: str | None = None
    treatment_mode: str | None = None


class ComparisonResult(DomainModel):
    schema_version: str = "comparison-v5"
    experiment_id: str
    checkpoint_id: str
    control_branch_id: str
    treatment_branch_id: str
    comparison_mode: ComparisonMode
    active_difference_proof: ActiveDifferenceProof
    policy_diff: list[PolicyFieldChange]
    event_diff: EventScenarioDiff
    delta_gap: float
    national_metrics: dict[str, MetricDelta]
    province_strategy_transitions: list[ProvinceStrategyTransition]
    automaker_strategy_transitions: list[AutomakerStrategyTransition]
    province_event_transitions: list[ProvinceEventTransition]
    province_deltas: list[ProvinceDelta]
    mechanism_totals: dict[str, float]
    top_improved: list[str]
    top_pressured: list[str]
    central_review: CentralReview | None = None


class ProvinceNeighbor(DomainModel):
    province_code: str = Field(pattern=r"^\d{2}$")
    province_name: str
    weight: float = Field(ge=0, le=1)


class ProvinceAutomakerEvidence(DomainModel):
    profile: AutomakerProfile
    state: AutomakerState | None = None
    action: AutomakerAction | None = None


class ProvinceAgentBranchSnapshot(DomainModel):
    branch_id: str
    branch_kind: BranchKind
    phase: Phase
    state: ProvinceState
    current_action: ProvinceAction | None = None
    action_lineage: list[ProvinceAction] = Field(default_factory=list)
    feedback: ProvinceFeedback | None = None
    automakers: list[ProvinceAutomakerEvidence] = Field(default_factory=list)
    mechanism_summary: dict[str, float] = Field(default_factory=dict)
    event_exposure: float | None = Field(default=None, ge=0, le=1)
    event_signal: ProvinceEventSignal | None = None
    event_response: ProvinceEventResponse | None = None
    coordination_matches: list[CoordinationMatch] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class ProvinceAgentDetail(DomainModel):
    schema_version: str = "province-agent-detail-v2"
    experiment_id: str
    province_code: str = Field(pattern=r"^\d{2}$")
    profile: ProvinceProfile
    persona: ProvinceDecisionPersona
    top_k_neighbors: list[ProvinceNeighbor]
    branches: dict[BranchKind, ProvinceAgentBranchSnapshot]


class AutomakerDetail(DomainModel):
    schema_version: str = "automaker-detail-v1"
    experiment_id: str
    automaker_id: str
    profile: AutomakerProfile
    branches: dict[BranchKind, AutomakerState]
    actions: dict[BranchKind, AutomakerAction | None]
    disclaimer: str = "车企资料仅作为冻结基线；未来行为与结果均为机制模拟，不代表真实企业承诺。"
