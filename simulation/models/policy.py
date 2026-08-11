from math import isclose

from pydantic import Field, model_validator

from simulation.models.base import DomainModel


class InstrumentMix(DomainModel):
    direct_subsidy: float = Field(default=0.45, ge=0, le=1)
    interest_subsidy: float = Field(default=0.35, ge=0, le=1)
    financing_guarantee: float = Field(default=0.20, ge=0, le=1)

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> "InstrumentMix":
        total = self.direct_subsidy + self.interest_subsidy + self.financing_guarantee
        if not isclose(total, 1.0, abs_tol=1e-6):
            raise ValueError(f"instrument mix must sum to 1.0, got {total}")
        return self


class TechnologyMix(DomainModel):
    digital: float = Field(default=0.40, ge=0, le=1)
    green: float = Field(default=0.30, ge=0, le=1)
    general: float = Field(default=0.30, ge=0, le=1)

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> "TechnologyMix":
        total = self.digital + self.green + self.general
        if not isclose(total, 1.0, abs_tol=1e-6):
            raise ValueError(f"technology mix must sum to 1.0, got {total}")
        return self


class PolicySchema(DomainModel):
    schema_version: str = "policy-v2"
    policy_id: str = "equipment_renewal_v2"
    domain: str = "manufacturing_equipment_renewal"
    support_intensity: float = Field(default=70, ge=0, le=100)
    local_match_requirement: float = Field(default=0.50, ge=0, le=1)
    instrument_mix: InstrumentMix = Field(default_factory=InstrumentMix)
    sme_preference: float = Field(default=0.60, ge=0, le=1)
    regional_support_bias: float = Field(default=0.0, ge=-1, le=1)
    technology_mix: TechnologyMix = Field(default_factory=TechnologyMix)
    mechanism_version: str = "equipment-renewal-env-v2"
