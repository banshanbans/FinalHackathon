from pydantic import Field

from simulation.models.base import DomainModel
from simulation.models.common import Phase, ProvinceReasonCode
from simulation.models.policy import InstrumentMix, TechnologyMix


class ProvinceAction(DomainModel):
    schema_version: str = "province-action-v2"
    action_id: str
    province_code: str = Field(pattern=r"^\d{2}$")
    phase: Phase
    implementation_intensity: float = Field(ge=0, le=1)
    local_match_ratio: float = Field(ge=0, le=1)
    instrument_mix: InstrumentMix
    sme_preference: float = Field(ge=0, le=1)
    regional_delivery_focus: float = Field(ge=0, le=1)
    technology_mix: TechnologyMix
    requested_central_support: float = Field(ge=0, le=1)
    reason_codes: list[ProvinceReasonCode] = Field(min_length=1, max_length=5)
    public_summary: str = Field(min_length=1, max_length=80)
    run_mode: str = "fake"
    fallback_used: bool = False


class MechanismContribution(DomainModel):
    schema_version: str = "mechanism-contribution-v2"
    enterprise_id: str
    province_code: str = Field(pattern=r"^\d{2}$")
    phase: Phase
    policy_match: float = 0
    direct_subsidy: float = 0
    interest_subsidy: float = 0
    financing_guarantee: float = 0
    sme_preference: float = 0
    regional_support: float = 0
    financing_constraint: float = 0
    fiscal_cost: float = 0

    @property
    def net_effect(self) -> float:
        return round(
            self.policy_match
            + self.direct_subsidy
            + self.interest_subsidy
            + self.financing_guarantee
            + self.sme_preference
            + self.regional_support
            + self.financing_constraint
            + self.fiscal_cost,
            4,
        )
