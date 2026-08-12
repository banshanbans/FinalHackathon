from typing import Literal

from pydantic import Field, field_validator, model_validator

from simulation.domain_constants import AUTOMAKER_IDS, MAINLAND_PROVINCE_CODES
from simulation.models.base import DomainModel
from simulation.models.common import (
    AutomakerReasonCode,
    ChannelStrategy,
    DataQuality,
    ExpansionPosture,
    FacilityActionKind,
    Phase,
    RunMode,
    SimulatedRoiBand,
)
from simulation.models.provenance import ProvenanceRecord

AUTOMAKER_PROVENANCE_FIELDS = frozenset(
    {
        "liquidity_index",
        "sales_scale_index",
        "sales_growth_index",
        "product_segment_mix",
        "profitability_index",
        "production_footprint",
        "technology_route_mix",
        "capacity_utilization_index",
        "channel_coverage_by_province",
    }
)


class ProvinceChannelCoverage(DomainModel):
    province_code: str = Field(pattern=r"^\d{2}$")
    coverage_index: float = Field(ge=0, le=1)


class ProductionFootprint(DomainModel):
    province_code: str = Field(pattern=r"^\d{2}$")
    role: Literal["vehicle", "component", "rd", "mixed"]
    baseline_note: str = Field(min_length=1, max_length=160)
    provenance_ref: str


class AutomakerProfile(DomainModel):
    schema_version: Literal["automaker-profile-v1"] = "automaker-profile-v1"
    automaker_id: str
    display_name: str = Field(min_length=2, max_length=20)
    entity_scope: str = Field(min_length=3, max_length=160)
    baseline_year: Literal[2025] = 2025
    sales_scale_index: float = Field(ge=0, le=1)
    sales_growth_index: float = Field(ge=0, le=1)
    profitability_index: float = Field(ge=0, le=1)
    liquidity_index: float = Field(ge=0, le=1)
    capacity_utilization_index: float = Field(ge=0, le=1)
    channel_coverage_by_province: list[ProvinceChannelCoverage]
    production_footprint: list[ProductionFootprint]
    product_segment_mix: dict[str, float] = Field(min_length=1)
    technology_route_mix: dict[str, float] = Field(min_length=1)
    expansion_posture: ExpansionPosture
    data_quality: DataQuality
    provenance: dict[str, ProvenanceRecord]

    @field_validator("automaker_id")
    @classmethod
    def known_automaker(cls, value: str) -> str:
        if value not in AUTOMAKER_IDS:
            raise ValueError("unknown automaker id")
        return value

    @field_validator("product_segment_mix", "technology_route_mix")
    @classmethod
    def valid_mix(cls, value: dict[str, float]) -> dict[str, float]:
        if (
            any(item < 0 or item > 1 for item in value.values())
            or abs(sum(value.values()) - 1) > 1e-6
        ):
            raise ValueError("automaker mix values must be in 0–1 and sum to 1")
        return value

    @model_validator(mode="after")
    def complete_baseline(self) -> "AutomakerProfile":
        coverage = [item.province_code for item in self.channel_coverage_by_province]
        if len(coverage) != 31 or set(coverage) != set(MAINLAND_PROVINCE_CODES):
            raise ValueError("automaker channel coverage must contain all 31 provinces once")
        footprint = [item.province_code for item in self.production_footprint]
        if len(footprint) != len(set(footprint)) or not set(footprint) <= set(
            MAINLAND_PROVINCE_CODES
        ):
            raise ValueError(
                "automaker production footprint must use unique mainland province codes"
            )
        if not AUTOMAKER_PROVENANCE_FIELDS <= set(self.provenance):
            raise ValueError("automaker profile provenance is incomplete")
        if self.data_quality is DataQuality.DEMO or any(
            item.quality is DataQuality.DEMO for item in self.provenance.values()
        ):
            raise ValueError("real automaker baselines cannot use demo provenance")
        return self


class ProvinceMarketAction(DomainModel):
    province_code: str = Field(pattern=r"^\d{2}$")
    sales_investment_intensity: float = Field(ge=0, le=1)
    channel_strategy: ChannelStrategy


class FacilityAction(DomainModel):
    province_code: str = Field(pattern=r"^\d{2}$")
    action: FacilityActionKind
    investment_intensity: float = Field(ge=0, le=1)


class AutomakerAction(DomainModel):
    schema_version: Literal["automaker-action-v1"] = "automaker-action-v1"
    action_id: str
    previous_action_id: str | None = None
    automaker_id: str
    phase: Phase
    province_market_actions: list[ProvinceMarketAction]
    facility_actions: list[FacilityAction] = Field(default_factory=list, max_length=3)
    simulated_roi_band: SimulatedRoiBand
    reason_codes: list[AutomakerReasonCode] = Field(min_length=1, max_length=5)
    summary: str = Field(min_length=1, max_length=80)
    run_mode: RunMode = RunMode.FAKE
    fallback_used: bool = False
    fallback_reason: str | None = Field(default=None, max_length=240)

    @model_validator(mode="after")
    def action_is_complete(self) -> "AutomakerAction":
        if self.automaker_id not in AUTOMAKER_IDS:
            raise ValueError("unknown automaker id")
        codes = [item.province_code for item in self.province_market_actions]
        if len(codes) != 31 or set(codes) != set(MAINLAND_PROVINCE_CODES):
            raise ValueError("automaker action must contain exactly 31 province allocations")
        facilities = [item.province_code for item in self.facility_actions]
        if len(facilities) != len(set(facilities)) or not set(facilities) <= set(
            MAINLAND_PROVINCE_CODES
        ):
            raise ValueError("facility actions must use unique mainland province codes")
        if self.phase not in {Phase.Y1_Q2, Phase.Y2_Q2}:
            raise ValueError("automaker actions are only valid in Q2")
        if self.phase is Phase.Y1_Q2 and self.previous_action_id is not None:
            raise ValueError("year-one automaker action cannot have a previous action")
        if self.phase is Phase.Y2_Q2 and self.previous_action_id is None:
            raise ValueError("year-two automaker action must reference year one")
        if self.fallback_used != (self.run_mode is RunMode.FALLBACK):
            raise ValueError("fallback flag and run mode must agree")
        if self.fallback_used != bool(self.fallback_reason):
            raise ValueError("fallback reason is required only for fallback output")
        return self


class AutomakerState(DomainModel):
    schema_version: Literal["automaker-state-v1"] = "automaker-state-v1"
    automaker_id: str
    phase: Phase = Phase.SETUP
    simulated_roi_index: float = Field(default=50, ge=0, le=100)
    sales_activity_index: float = Field(default=50, ge=0, le=100)
    facility_activity_index: float = Field(default=0, ge=0, le=100)
    operating_cost_index: float = Field(default=50, ge=0, le=100)
    last_action_id: str | None = None
