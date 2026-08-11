from pydantic import Field

from simulation.models.base import DomainModel
from simulation.models.common import DataQuality, Phase, ProvinceReasonCode, RegionGroup


class ProvinceProfile(DomainModel):
    schema_version: str = "province-profile-v2"
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
    data_quality: DataQuality
    source_year: int = Field(ge=2000, le=2100)


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


class ProvinceFeedback(DomainModel):
    schema_version: str = "province-feedback-v2"
    feedback_id: str
    province_code: str = Field(pattern=r"^\d{2}$")
    phase: Phase = Phase.T3
    implementation_assessment: str = Field(min_length=1, max_length=40)
    priority_enterprise_groups: list[str] = Field(min_length=1, max_length=3)
    requested_central_support: float = Field(ge=0, le=1)
    reason_codes: list[ProvinceReasonCode] = Field(min_length=1, max_length=5)
    evidence_refs: list[str] = Field(min_length=1, max_length=8)
    public_summary: str = Field(min_length=1, max_length=80)
    run_mode: str = "fake"
    fallback_used: bool = False
