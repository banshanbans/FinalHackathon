from pydantic import Field, field_validator, model_validator

from simulation.models.base import DomainModel
from simulation.models.common import (
    DecisionPosture,
    EnterpriseArchetype,
    InterprovincialStrategy,
    Phase,
    ProvincePriorityGoal,
    ProvinceReasonCode,
)
from simulation.models.policy import InstrumentMix, TechnologyMix


class ProvinceAction(DomainModel):
    schema_version: str = "province-action-v3"
    action_id: str
    previous_action_id: str | None = None
    province_code: str = Field(pattern=r"^\d{2}$")
    phase: Phase
    primary_goal: ProvincePriorityGoal
    decision_posture: DecisionPosture
    target_enterprise_groups: list[EnterpriseArchetype] = Field(min_length=1, max_length=3)
    interprovincial_strategy: InterprovincialStrategy
    target_province_codes: list[str] = Field(default_factory=list, max_length=2)
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

    @field_validator("target_enterprise_groups")
    @classmethod
    def enterprise_targets_are_unique(
        cls, value: list[EnterpriseArchetype]
    ) -> list[EnterpriseArchetype]:
        if len(value) != len(set(value)):
            raise ValueError("target enterprise groups must be unique")
        return value

    @field_validator("target_province_codes")
    @classmethod
    def province_targets_are_unique_and_valid(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("target province codes must be unique")
        if any(len(code) != 2 or not code.isdigit() for code in value):
            raise ValueError("target province codes must be two digits")
        return value

    @model_validator(mode="after")
    def phase_and_strategy_are_consistent(self) -> "ProvinceAction":
        if self.phase not in {Phase.T1, Phase.T4}:
            raise ValueError("province actions are only valid at T1 or T4")
        if self.phase == Phase.T1 and self.previous_action_id is not None:
            raise ValueError("T1 province action cannot reference a previous action")
        if self.phase == Phase.T4 and self.previous_action_id is None:
            raise ValueError("T4 province action must reference the previous action")
        if self.interprovincial_strategy == InterprovincialStrategy.INDEPENDENT:
            if self.target_province_codes:
                raise ValueError("independent strategy cannot target another province")
        elif not 1 <= len(self.target_province_codes) <= 2:
            raise ValueError("non-independent strategy requires one or two province targets")
        return self


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
