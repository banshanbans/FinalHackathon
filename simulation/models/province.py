from typing import Literal

from pydantic import Field, field_validator, model_validator

from simulation.domain_constants import MAINLAND_PROVINCE_CODES
from simulation.models.base import DomainModel
from simulation.models.common import (
    AdjustmentDirection,
    DataQuality,
    PeerResponseMode,
    Phase,
    PolicyRegion,
    ProvinceConstraint,
    ProvincePersonaType,
    ProvinceReasonCode,
    ProvinceSignalType,
    RunMode,
    SignalDirection,
    SignalSeverity,
    StrategyAssessment,
)
from simulation.models.provenance import ProvenanceRecord


class ProvinceProfile(DomainModel):
    schema_version: Literal["province-profile-v5"] = "province-profile-v5"
    province_code: str = Field(pattern=r"^\d{2}$")
    name: str
    short_name: str
    policy_region: PolicyRegion
    baseline_year: Literal[2025] = 2025
    fiscal_capacity: float = Field(ge=0, le=1)
    fiscal_rigidity: float = Field(ge=0, le=1)
    nev_industry_base: float = Field(ge=0, le=1)
    vehicle_manufacturing_base: float = Field(ge=0, le=1)
    components_base: float = Field(ge=0, le=1)
    rd_activity: float = Field(ge=0, le=1)
    market_scale: float = Field(ge=0, le=1)
    willingness_to_pay_index: float = Field(ge=0, le=1)
    land_cost_index: float = Field(ge=0, le=1)
    talent_cost_index: float = Field(ge=0, le=1)
    energy_cost_index: float = Field(ge=0, le=1)
    logistics_cost_index: float = Field(ge=0, le=1)
    battery_supply_distance_index: float = Field(ge=0, le=1)
    charging_infrastructure_index: float = Field(ge=0, le=1)
    urbanization_index: float = Field(ge=0, le=1)
    vehicle_consumption_index: float = Field(ge=0, le=1)
    nev_penetration_index: float = Field(ge=0, le=1)
    intelligent_driving_readiness_index: float = Field(ge=0, le=1)
    regulatory_execution_capacity_index: float = Field(ge=0, le=1)
    oil_price_sensitivity_index: float = Field(ge=0, le=1)
    supply_chain_complementarity_index: float = Field(ge=0, le=1)
    peer_province_codes: list[str] = Field(min_length=3, max_length=5)
    data_quality: DataQuality
    provenance: dict[str, ProvenanceRecord]

    @model_validator(mode="after")
    def valid_codes(self) -> "ProvinceProfile":
        if self.province_code not in MAINLAND_PROVINCE_CODES:
            raise ValueError("province is outside the 31-province simulation scope")
        if len(self.peer_province_codes) != len(set(self.peer_province_codes)):
            raise ValueError("peer province codes must be unique")
        if self.province_code in self.peer_province_codes:
            raise ValueError("province cannot observe itself as a peer")
        if not set(self.peer_province_codes) <= set(MAINLAND_PROVINCE_CODES):
            raise ValueError("unknown peer province code")
        return self


class ProvincePersonaAxes(DomainModel):
    fiscal_capacity: float = Field(ge=0, le=1)
    industry_attraction: float = Field(ge=0, le=1)
    consumption_activation: float = Field(ge=0, le=1)
    operating_cost_competitiveness: float = Field(ge=0, le=1)
    supply_chain_coordination: float = Field(ge=0, le=1)
    peer_response_sensitivity: float = Field(ge=0, le=1)


class ProvinceDecisionPersona(DomainModel):
    schema_version: Literal["province-persona-v2"] = "province-persona-v2"
    province_code: str = Field(pattern=r"^\d{2}$")
    axes: ProvincePersonaAxes
    primary_type: ProvincePersonaType
    secondary_type: ProvincePersonaType | None = None
    key_constraints: list[ProvinceConstraint] = Field(min_length=1, max_length=3)
    profile_version: Literal["province-profile-v5"] = "province-profile-v5"
    network_version: str = "nev-peer-network-v1"
    method_version: str = "province-persona-method-v2"
    data_quality: Literal[DataQuality.PROXY, DataQuality.DEMO] = DataQuality.PROXY
    summary: str = Field(min_length=1, max_length=80)

    @field_validator("key_constraints")
    @classmethod
    def constraints_unique(cls, value: list[ProvinceConstraint]) -> list[ProvinceConstraint]:
        if len(value) != len(set(value)):
            raise ValueError("persona constraints must be unique")
        return value


class SubsidyMix(DomainModel):
    consumer: float = Field(ge=0, le=1)
    fixed_cost: float = Field(ge=0, le=1)
    variable_cost: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def sums_to_one(self) -> "SubsidyMix":
        if abs(self.consumer + self.fixed_cost + self.variable_cost - 1) > 1e-6:
            raise ValueError("province subsidy mix must sum to 1")
        return self


class ProvinceAction(DomainModel):
    schema_version: Literal["province-action-v4"] = "province-action-v4"
    action_id: str
    previous_action_id: str | None = None
    province_code: str = Field(pattern=r"^\d{2}$")
    phase: Phase
    overall_support_intensity: float = Field(ge=0, le=1)
    subsidy_mix: SubsidyMix
    peer_response_mode: PeerResponseMode
    observed_peer_codes: list[str] = Field(default_factory=list, max_length=3)
    reason_codes: list[ProvinceReasonCode] = Field(min_length=1, max_length=5)
    summary: str = Field(min_length=1, max_length=80)
    run_mode: RunMode = RunMode.FAKE
    fallback_used: bool = False
    fallback_reason: str | None = Field(default=None, max_length=240)

    @model_validator(mode="after")
    def valid_action(self) -> "ProvinceAction":
        if self.phase not in {Phase.Y1_Q1, Phase.Y2_Q1}:
            raise ValueError("province actions are only valid in Q1")
        if self.phase is Phase.Y1_Q1 and self.previous_action_id is not None:
            raise ValueError("year-one province action cannot have previous action")
        if self.phase is Phase.Y2_Q1 and self.previous_action_id is None:
            raise ValueError("year-two province action must reference year one")
        peers = self.observed_peer_codes
        if len(peers) != len(set(peers)) or self.province_code in peers:
            raise ValueError("observed peers must be unique and cannot include self")
        if not set(peers) <= set(MAINLAND_PROVINCE_CODES):
            raise ValueError("unknown observed peer")
        if self.fallback_used != (self.run_mode is RunMode.FALLBACK) or self.fallback_used != bool(
            self.fallback_reason
        ):
            raise ValueError("fallback fields are inconsistent")
        return self


PROVINCE_ADJUSTMENT_PATHS = frozenset(
    {
        "overall_support_intensity",
        "subsidy_mix.consumer",
        "subsidy_mix.fixed_cost",
        "subsidy_mix.variable_cost",
        "peer_response_mode",
    }
)


class ProvinceSignal(DomainModel):
    signal_type: ProvinceSignalType
    direction: SignalDirection
    severity: SignalSeverity
    evidence_refs: list[str] = Field(min_length=1, max_length=4)


class AdjustmentIntent(DomainModel):
    path: str
    direction: AdjustmentDirection
    reason: str = Field(min_length=1, max_length=160)

    @field_validator("path")
    @classmethod
    def path_is_allowed(cls, value: str) -> str:
        if value not in PROVINCE_ADJUSTMENT_PATHS:
            raise ValueError("unsupported province adjustment path")
        return value


class CentralShareRecommendation(DomainModel):
    west_delta: float = Field(default=0, ge=-1, le=1)
    central_delta: float = Field(default=0, ge=-1, le=1)
    east_delta: float = Field(default=0, ge=-1, le=1)


class ProvinceFeedback(DomainModel):
    schema_version: Literal["province-feedback-v4"] = "province-feedback-v4"
    feedback_id: str
    province_code: str = Field(pattern=r"^\d{2}$")
    phase: Literal[Phase.Y1_Q4] = Phase.Y1_Q4
    strategy_assessment: StrategyAssessment
    signals: list[ProvinceSignal] = Field(default_factory=list, max_length=6)
    constraints: list[ProvinceConstraint] = Field(min_length=1, max_length=3)
    adjustment_intents: list[AdjustmentIntent] = Field(default_factory=list, max_length=3)
    central_share_recommendation: CentralShareRecommendation = Field(
        default_factory=CentralShareRecommendation
    )
    reason_codes: list[ProvinceReasonCode] = Field(min_length=1, max_length=5)
    evidence_refs: list[str] = Field(min_length=1, max_length=8)
    summary: str = Field(min_length=1, max_length=80)
    run_mode: RunMode = RunMode.FAKE
    fallback_used: bool = False
    fallback_reason: str | None = Field(default=None, max_length=240)


class ProvinceState(DomainModel):
    schema_version: Literal["province-state-v5"] = "province-state-v5"
    province_code: str = Field(pattern=r"^\d{2}$")
    phase: Phase = Phase.SETUP
    local_matching_burden_index: float = Field(default=0, ge=0, le=100)
    fiscal_space_index: float = Field(default=50, ge=0, le=100)
    local_support_index: float = Field(default=50, ge=0, le=100)
    demand_index: float = Field(default=50, ge=0, le=100)
    industry_activity_index: float = Field(default=50, ge=0, le=100)
    development_index: float = Field(default=50, ge=0, le=100)
    fiscal_pressure_index: float = Field(default=50, ge=0, le=100)
    event_exposure_index: float = Field(default=0, ge=0, le=100)
    event_response_effect_index: float = Field(default=0, ge=0, le=100)
    last_action_id: str | None = None
    last_feedback_id: str | None = None
    last_event_response_id: str | None = None
