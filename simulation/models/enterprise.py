from pydantic import Field, model_validator

from simulation.models.base import DomainModel
from simulation.models.common import (
    DataQuality,
    EnterpriseArchetype,
    EnterpriseReasonCode,
    FinancingChoice,
    Participation,
    Phase,
    UpgradeType,
)


class EnterpriseArchetypeDefinition(DomainModel):
    schema_version: str = "enterprise-archetype-v2"
    archetype: EnterpriseArchetype
    display_name: str = Field(min_length=2, max_length=24)
    weight: float = Field(gt=0, le=1)
    equipment_age_pressure: float = Field(ge=0, le=1)
    digital_readiness: float = Field(ge=0, le=1)
    green_transition_pressure: float = Field(ge=0, le=1)
    financing_constraint: float = Field(ge=0, le=1)
    collateral_capacity: float = Field(ge=0, le=1)
    cash_flow_resilience: float = Field(ge=0, le=1)
    export_exposure: float = Field(ge=0, le=1)
    data_quality: DataQuality = DataQuality.DEMO


class EnterpriseGroupProfile(DomainModel):
    schema_version: str = "enterprise-profile-v2"
    enterprise_id: str = Field(pattern=r"^\d{2}:[a-z_]+$")
    province_code: str = Field(pattern=r"^\d{2}$")
    archetype: EnterpriseArchetype
    display_name: str = Field(min_length=2, max_length=24)
    weight: float = Field(gt=0, le=1)
    equipment_age_pressure: float = Field(ge=0, le=1)
    digital_readiness: float = Field(ge=0, le=1)
    green_transition_pressure: float = Field(ge=0, le=1)
    financing_constraint: float = Field(ge=0, le=1)
    collateral_capacity: float = Field(ge=0, le=1)
    cash_flow_resilience: float = Field(ge=0, le=1)
    export_exposure: float = Field(ge=0, le=1)
    data_quality: DataQuality = DataQuality.DEMO
    source_year: int = Field(default=2024, ge=2000, le=2100)


class EnterpriseGroupState(DomainModel):
    schema_version: str = "enterprise-state-v2"
    enterprise_id: str
    province_code: str = Field(pattern=r"^\d{2}$")
    phase: Phase = Phase.T0
    participation_score: float = Field(default=45, ge=0, le=100)
    renewal_willingness: float = Field(default=50, ge=0, le=100)
    financing_accessibility: float = Field(default=45, ge=0, le=100)
    upgrade_progress: float = Field(default=35, ge=0, le=100)
    last_action_id: str | None = None


class EnterpriseAction(DomainModel):
    schema_version: str = "enterprise-action-v2"
    action_id: str
    enterprise_id: str
    province_code: str = Field(pattern=r"^\d{2}$")
    archetype: EnterpriseArchetype
    phase: Phase
    participation: Participation
    upgrade_type: UpgradeType
    financing_choice: FinancingChoice
    investment_intensity: float = Field(ge=0, le=1)
    requested_support: float = Field(ge=0, le=1)
    reason_codes: list[EnterpriseReasonCode] = Field(min_length=1, max_length=5)
    public_summary: str = Field(min_length=1, max_length=80)

    @model_validator(mode="after")
    def action_combination_is_consistent(self) -> "EnterpriseAction":
        inactive = self.participation in {Participation.WAIT, Participation.DECLINE}
        if inactive and self.upgrade_type != UpgradeType.NONE:
            raise ValueError("waiting or declining enterprise cannot choose an upgrade type")
        if inactive and self.investment_intensity != 0:
            raise ValueError("waiting or declining enterprise must have zero investment intensity")
        if (
            self.participation == Participation.DECLINE
            and self.financing_choice != FinancingChoice.NONE
        ):
            raise ValueError("declining enterprise must not choose financing")
        if self.participation in {Participation.PARTICIPATE, Participation.CONDITIONAL}:
            if (
                self.upgrade_type == UpgradeType.NONE
                or self.financing_choice == FinancingChoice.NONE
            ):
                raise ValueError("active enterprise must choose upgrade and financing")
        return self


class EnterpriseActionBatch(DomainModel):
    schema_version: str = "enterprise-action-batch-v2"
    batch_id: str
    province_code: str = Field(pattern=r"^\d{2}$")
    phase: Phase
    actions: list[EnterpriseAction]
    run_mode: str = "fake"
    fallback_used: bool = False
    fallback_reason: str | None = Field(default=None, max_length=240)

    @model_validator(mode="after")
    def contains_all_archetypes_once(self) -> "EnterpriseActionBatch":
        expected = set(EnterpriseArchetype)
        actual = [item.archetype for item in self.actions]
        if len(actual) != len(expected) or set(actual) != expected:
            raise ValueError("enterprise action batch must contain every archetype exactly once")
        if any(item.province_code != self.province_code for item in self.actions):
            raise ValueError("enterprise action batch cannot mix provinces")
        if any(item.phase != self.phase for item in self.actions):
            raise ValueError("enterprise action batch cannot mix phases")
        if len({item.enterprise_id for item in self.actions}) != len(expected):
            raise ValueError("enterprise IDs must be unique within a batch")
        return self


class EnterpriseAggregate(DomainModel):
    schema_version: str = "enterprise-aggregate-v2"
    province_code: str = Field(pattern=r"^\d{2}$")
    participation_index: float = Field(ge=0, le=100)
    renewal_willingness_index: float = Field(ge=0, le=100)
    sme_financing_accessibility_index: float = Field(ge=0, le=100)
    industrial_upgrade_index: float = Field(ge=0, le=100)
    participation_counts: dict[Participation, int]
