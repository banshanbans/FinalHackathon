from pydantic import Field, field_validator, model_validator

from simulation.models.base import DomainModel
from simulation.models.common import (
    AdjustmentDirection,
    CentralSupportType,
    DataQuality,
    EnterpriseArchetype,
    EnterpriseSignalType,
    Phase,
    ProvinceConstraint,
    ProvincePersonaType,
    ProvincePriorityGoal,
    ProvinceReasonCode,
    RegionGroup,
    SignalSeverity,
    StrategyAssessment,
)

ADJUSTMENT_PATHS = {
    "implementation_intensity",
    "local_match_ratio",
    "instrument_mix.direct_subsidy",
    "instrument_mix.interest_subsidy",
    "instrument_mix.financing_guarantee",
    "sme_preference",
    "regional_delivery_focus",
    "technology_mix.digital",
    "technology_mix.green",
    "technology_mix.general",
}


class ProvinceProfile(DomainModel):
    schema_version: str = "province-profile-v3"
    province_code: str = Field(pattern=r"^\d{2}$")
    name: str = Field(min_length=2, max_length=12)
    short_name: str = Field(min_length=1, max_length=6)
    region_group: RegionGroup
    economic_scale: float = Field(ge=0, le=1)
    fiscal_capacity: float = Field(ge=0, le=1)
    industrial_diversity: float = Field(ge=0, le=1)
    advanced_manufacturing_base: float = Field(ge=0, le=1)
    digital_infrastructure: float = Field(ge=0, le=1)
    green_energy_base: float = Field(ge=0, le=1)
    sme_density: float = Field(ge=0, le=1)
    credit_access: float = Field(ge=0, le=1)
    transition_pressure: float = Field(ge=0, le=1)
    fiscal_conservatism: float = Field(ge=0, le=1)
    rd_capacity: float = Field(ge=0, le=1)
    employment_pressure: float = Field(ge=0, le=1)
    cooperation_tendency: float = Field(ge=0, le=1)
    data_quality: DataQuality
    source_year: int = Field(ge=2000, le=2100)


class ProvincePersonaAxes(DomainModel):
    execution_drive: float = Field(ge=0, le=1)
    fiscal_prudence: float = Field(ge=0, le=1)
    sme_inclusiveness: float = Field(ge=0, le=1)
    technology_ambition: float = Field(ge=0, le=1)
    green_priority: float = Field(ge=0, le=1)
    cooperation_orientation: float = Field(ge=0, le=1)


class ProvinceDecisionPersona(DomainModel):
    schema_version: str = "province-persona-v1"
    province_code: str = Field(pattern=r"^\d{2}$")
    axes: ProvincePersonaAxes
    primary_type: ProvincePersonaType
    secondary_type: ProvincePersonaType | None = None
    priority_goals: list[ProvincePriorityGoal] = Field(min_length=1, max_length=2)
    key_constraints: list[ProvinceConstraint] = Field(min_length=2, max_length=2)
    profile_version: str = "province-profile-v3"
    network_version: str = "province-network-v1"
    method_version: str = "province-persona-method-v1"
    data_quality: DataQuality
    public_summary: str = Field(min_length=1, max_length=80)

    @field_validator("data_quality")
    @classmethod
    def persona_quality_is_not_verified(cls, value: DataQuality) -> DataQuality:
        if value == DataQuality.VERIFIED:
            raise ValueError("province persona quality must be proxy or demo")
        return value

    @field_validator("priority_goals", "key_constraints")
    @classmethod
    def persona_lists_are_unique(cls, value: list[object]) -> list[object]:
        if len(value) != len(set(value)):
            raise ValueError("province persona lists must not contain duplicates")
        return value


class ProvinceState(DomainModel):
    schema_version: str = "province-state-v2"
    province_code: str = Field(pattern=r"^\d{2}$")
    phase: Phase = Phase.T0
    enterprise_participation_index: float = Field(default=45, ge=0, le=100)
    equipment_renewal_willingness_index: float = Field(default=50, ge=0, le=100)
    sme_financing_accessibility_index: float = Field(default=42, ge=0, le=100)
    industrial_upgrade_index: float = Field(default=40, ge=0, le=100)
    fiscal_pressure_index: float = Field(default=35, ge=0, le=100)
    last_action_id: str | None = None


class EnterpriseSignal(DomainModel):
    cohort_type: EnterpriseArchetype
    signal_type: EnterpriseSignalType
    severity: SignalSeverity
    evidence_refs: list[str] = Field(min_length=1, max_length=4)


class AdjustmentIntent(DomainModel):
    path: str
    direction: AdjustmentDirection
    reason_code: ProvinceReasonCode

    @field_validator("path")
    @classmethod
    def path_is_frozen(cls, value: str) -> str:
        if value not in ADJUSTMENT_PATHS:
            raise ValueError(f"unsupported province adjustment path: {value}")
        return value


class ProvinceFeedback(DomainModel):
    schema_version: str = "province-feedback-v3"
    feedback_id: str
    province_code: str = Field(pattern=r"^\d{2}$")
    phase: Phase = Phase.T3
    strategy_assessment: StrategyAssessment
    enterprise_signals: list[EnterpriseSignal] = Field(default_factory=list, max_length=6)
    priority_enterprise_groups: list[EnterpriseArchetype] = Field(min_length=1, max_length=3)
    key_constraints: list[ProvinceConstraint] = Field(min_length=1, max_length=3)
    adjustment_intents: list[AdjustmentIntent] = Field(default_factory=list, max_length=3)
    requested_support_type: CentralSupportType
    requested_central_support: float = Field(ge=0, le=1)
    reason_codes: list[ProvinceReasonCode] = Field(min_length=1, max_length=5)
    evidence_refs: list[str] = Field(min_length=1, max_length=8)
    public_summary: str = Field(min_length=1, max_length=80)
    run_mode: str = "fake"
    fallback_used: bool = False

    @field_validator("priority_enterprise_groups", "key_constraints")
    @classmethod
    def feedback_lists_are_unique(cls, value: list[object]) -> list[object]:
        if len(value) != len(set(value)):
            raise ValueError("province feedback lists must not contain duplicates")
        return value

    @model_validator(mode="after")
    def support_type_matches_intensity(self) -> "ProvinceFeedback":
        if (
            self.requested_central_support == 0
            and self.requested_support_type != CentralSupportType.NONE
        ):
            raise ValueError("zero support intensity requires support type none")
        if (
            self.requested_central_support > 0
            and self.requested_support_type == CentralSupportType.NONE
        ):
            raise ValueError("positive support intensity requires a support type")
        return self
