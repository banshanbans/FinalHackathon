from pydantic import Field

from simulation.models.action import MechanismContribution, ProvinceAction
from simulation.models.base import DomainModel
from simulation.models.central import (
    CentralIntervention,
    CentralInterventionProposal,
    CentralPolicyDirective,
    CentralReview,
    PolicyFieldChange,
)
from simulation.models.common import ExperimentStatus, Participation, Phase, RunMode
from simulation.models.enterprise import (
    EnterpriseAction,
    EnterpriseAggregate,
    EnterpriseGroupProfile,
    EnterpriseGroupState,
)
from simulation.models.policy import PolicySchema
from simulation.models.province import ProvinceFeedback, ProvinceProfile, ProvinceState


class NationalMetrics(DomainModel):
    schema_version: str = "national-metrics-v2"
    enterprise_participation_index: float = Field(default=45, ge=0, le=100)
    equipment_renewal_willingness_index: float = Field(default=50, ge=0, le=100)
    sme_financing_accessibility_index: float = Field(default=42, ge=0, le=100)
    industrial_upgrade_index: float = Field(default=40, ge=0, le=100)
    local_fiscal_pressure_index: float = Field(default=35, ge=0, le=100)
    regional_gap_index: float = Field(default=0, ge=0, le=100)


class VersionInfo(DomainModel):
    data: str
    mechanism: str
    prompt: str
    model: str
    app: str = "0.2.0"


class WorldState(DomainModel):
    schema_version: str = "world-state-v2"
    experiment_id: str
    branch_id: str = "control"
    parent_checkpoint_id: str | None = None
    phase: Phase = Phase.T0
    status: ExperimentStatus = ExperimentStatus.AWAITING_APPROVAL
    run_mode: RunMode = RunMode.FAKE
    policy: PolicySchema
    directive: CentralPolicyDirective
    national_metrics: NationalMetrics = Field(default_factory=NationalMetrics)
    province_profiles: dict[str, ProvinceProfile]
    province_states: dict[str, ProvinceState]
    province_actions: dict[str, ProvinceAction] = Field(default_factory=dict)
    province_feedback: dict[str, ProvinceFeedback] = Field(default_factory=dict)
    enterprise_profiles: dict[str, EnterpriseGroupProfile]
    enterprise_states: dict[str, EnterpriseGroupState]
    enterprise_actions: dict[str, EnterpriseAction] = Field(default_factory=dict)
    enterprise_aggregates: dict[str, EnterpriseAggregate] = Field(default_factory=dict)
    contributions: dict[str, MechanismContribution] = Field(default_factory=dict)
    fallback_provinces: list[str] = Field(default_factory=list)
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
    enterprise_participation_delta: float
    renewal_willingness_delta: float
    sme_financing_accessibility_delta: float
    fiscal_pressure_delta: float


class ActionMigration(DomainModel):
    from_participation: Participation
    to_participation: Participation
    count: int = Field(ge=0)


class EnterpriseGroupChange(DomainModel):
    archetype: str
    participation_delta: float
    renewal_willingness_delta: float
    financing_accessibility_delta: float


class ComparisonResult(DomainModel):
    schema_version: str = "comparison-v2"
    experiment_id: str
    checkpoint_id: str
    control_branch_id: str
    treatment_branch_id: str
    policy_diff: list[PolicyFieldChange]
    national_metrics: dict[str, MetricDelta]
    province_deltas: list[ProvinceDelta]
    action_migrations: list[ActionMigration]
    enterprise_group_changes: list[EnterpriseGroupChange]
    mechanism_totals: dict[str, float]
    top_improved: list[str]
    top_pressured: list[str]
    central_review: CentralReview | None = None
