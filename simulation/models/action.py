from pydantic import Field, model_validator

from simulation.models.base import DomainModel
from simulation.models.common import (
    Industry,
    InteractionStrategy,
    Phase,
    ReasonCode,
    Stance,
    TalentStrategy,
)


class ProvinceAction(DomainModel):
    schema_version: str = "province-action-v1"
    action_id: str
    province_code: str = Field(pattern=r"^\d{2}$")
    phase: Phase
    stance: Stance
    implementation_intensity: float = Field(ge=0, le=1)
    local_budget_ratio: float = Field(ge=0, le=1)
    priority_industries: list[Industry] = Field(min_length=1, max_length=2)
    talent_strategy: TalentStrategy
    interaction_strategy: InteractionStrategy
    target_provinces: list[str] = Field(default_factory=list, max_length=5)
    requested_central_support: float = Field(ge=0, le=1)
    reason_codes: list[ReasonCode] = Field(min_length=1, max_length=5)
    public_summary: str = Field(min_length=1, max_length=80)
    run_mode: str = "fake"
    fallback_used: bool = False

    @model_validator(mode="after")
    def target_codes_are_unique_and_external(self) -> "ProvinceAction":
        if len(set(self.target_provinces)) != len(self.target_provinces):
            raise ValueError("target provinces must be unique")
        if self.province_code in self.target_provinces:
            raise ValueError("province cannot target itself")
        if any(len(code) != 2 or not code.isdigit() for code in self.target_provinces):
            raise ValueError("target province codes must be two digits")
        return self


class MechanismContribution(DomainModel):
    schema_version: str = "mechanism-contribution-v1"
    province_code: str
    phase: Phase
    policy_match: float = 0
    central_support: float = 0
    local_investment: float = 0
    cooperation_spillover: float = 0
    geographic_spillover: float = 0
    competition_crowding_out: float = 0
    fiscal_execution_cost: float = 0

    @property
    def net_effect(self) -> float:
        return round(
            self.policy_match
            + self.central_support
            + self.local_investment
            + self.cooperation_spillover
            + self.geographic_spillover
            - self.competition_crowding_out
            - self.fiscal_execution_cost,
            4,
        )
