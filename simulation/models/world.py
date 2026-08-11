from pydantic import Field

from simulation.models.action import MechanismContribution, ProvinceAction
from simulation.models.base import DomainModel
from simulation.models.central import (
    CentralIntervention,
    CentralInterventionProposal,
    CentralPolicyDirective,
    CentralReview,
)
from simulation.models.common import ExperimentStatus, Phase, RunMode
from simulation.models.policy import PolicySchema
from simulation.models.province import ProvinceState


class NationalMetrics(DomainModel):
    schema_version: str = "national-metrics-v1"
    overall_policy_benefit: float = Field(default=50, ge=0, le=100)
    policy_accessibility: float = Field(default=50, ge=0, le=100)
    innovation_vitality: float = Field(default=50, ge=0, le=100)
    employment_support: float = Field(default=50, ge=0, le=100)
    regional_gap: float = Field(default=0, ge=0, le=100)
    fiscal_pressure: float = Field(default=35, ge=0, le=100)
    cooperation_density: float = Field(default=0, ge=0, le=100)
    industry_concentration: float = Field(default=0, ge=0, le=100)


class VersionInfo(DomainModel):
    data: str
    mechanism: str
    prompt: str
    model: str
    app: str = "0.1.0"


class NetworkEffect(DomainModel):
    source_province: str
    target_province: str
    effect_type: str
    magnitude: float


class WorldState(DomainModel):
    schema_version: str = "world-state-v1"
    experiment_id: str
    branch_id: str = "control"
    parent_checkpoint_id: str | None = None
    phase: Phase = Phase.T0
    status: ExperimentStatus = ExperimentStatus.AWAITING_APPROVAL
    run_mode: RunMode = RunMode.FAKE
    policy: PolicySchema
    directive: CentralPolicyDirective
    national_metrics: NationalMetrics = Field(default_factory=NationalMetrics)
    provinces: dict[str, ProvinceState]
    actions: dict[str, ProvinceAction] = Field(default_factory=dict)
    contributions: dict[str, MechanismContribution] = Field(default_factory=dict)
    network_effects: list[NetworkEffect] = Field(default_factory=list)
    intervention_proposals: list[CentralInterventionProposal] = Field(default_factory=list)
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
    policy_benefit_delta: float
    accessibility_delta: float
    fiscal_pressure_delta: float


class ComparisonResult(DomainModel):
    schema_version: str = "comparison-v1"
    experiment_id: str
    checkpoint_id: str
    control_branch_id: str
    treatment_branch_id: str
    policy_diff: dict[str, dict[str, float]]
    national_metrics: dict[str, MetricDelta]
    province_deltas: list[ProvinceDelta]
    mechanism_totals: dict[str, float]
    top_improved: list[str]
    top_pressured: list[str]
    central_review: CentralReview | None = None
