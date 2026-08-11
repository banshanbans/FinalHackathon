from pydantic import Field

from simulation.models.base import DomainModel
from simulation.models.common import DataQuality, RegionGroup


class ProvinceProfile(DomainModel):
    schema_version: str = "province-profile-v1"
    province_code: str = Field(pattern=r"^\d{2}$")
    name: str = Field(min_length=2, max_length=12)
    short_name: str = Field(min_length=1, max_length=6)
    region_group: RegionGroup
    economic_scale: float = Field(ge=0, le=1)
    fiscal_capacity: float = Field(ge=0, le=1)
    industrial_diversity: float = Field(ge=0, le=1)
    ai_base: float = Field(ge=0, le=1)
    advanced_manufacturing_base: float = Field(ge=0, le=1)
    green_energy_base: float = Field(ge=0, le=1)
    rd_capacity: float = Field(ge=0, le=1)
    talent_attractiveness: float = Field(ge=0, le=1)
    digital_infrastructure: float = Field(ge=0, le=1)
    employment_pressure: float = Field(ge=0, le=1)
    transition_pressure: float = Field(ge=0, le=1)
    fiscal_conservatism: float = Field(ge=0, le=1)
    cooperation_tendency: float = Field(ge=0, le=1)
    data_quality: DataQuality
    source_year: int = Field(ge=2000, le=2100)


class ProvinceState(DomainModel):
    schema_version: str = "province-state-v1"
    province_code: str = Field(pattern=r"^\d{2}$")
    phase: str = "T0"
    policy_benefit_index: float = Field(default=50, ge=0, le=100)
    innovation_index: float = Field(default=50, ge=0, le=100)
    employment_index: float = Field(default=50, ge=0, le=100)
    fiscal_pressure: float = Field(default=35, ge=0, le=100)
    policy_accessibility: float = Field(default=50, ge=0, le=100)
    talent_attraction: float = Field(default=50, ge=0, le=100)
    cooperation_stock: float = Field(default=20, ge=0, le=100)
    last_action_id: str | None = None
