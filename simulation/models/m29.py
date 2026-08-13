from __future__ import annotations

from typing import Literal

from pydantic import Field, HttpUrl, model_validator

from simulation.domain_constants import AUTOMAKER_IDS, MAINLAND_PROVINCE_CODES
from simulation.models.base import FrozenDomainModel

M29DataQuality = Literal["verified", "proxy", "scenario_assumption"]
ReviewStatus = Literal["unreviewed", "source_checked", "accepted", "rejected"]


class M29SourceRecord(FrozenDomainModel):
    schema_version: Literal["source-record-v1"] = "source-record-v1"
    source_id: str
    institution: str = Field(min_length=1)
    title: str = Field(min_length=1)
    url: HttpUrl
    reference_period: str
    accessed_at: str
    source_tier: Literal["primary", "official_repost", "association", "secondary"]
    quality: M29DataQuality


class M29RawFact(FrozenDomainModel):
    schema_version: Literal["raw-fact-v1"] = "raw-fact-v1"
    record_id: str
    subject_type: Literal["province", "automaker", "facility", "policy", "route"]
    subject_id: str
    metric_code: str
    metric_name: str
    raw_value: str | float | int | bool | None
    raw_unit: str
    reference_period: str
    statistical_scope: str
    source_id: str
    source_institution: str
    source_url: HttpUrl
    source_title: str
    accessed_at: str
    transformation: str
    missing_handling: str
    data_quality: M29DataQuality
    review_status: ReviewStatus
    selected_for_baseline: bool = False
    selection_reason: str = ""


class M29PolicyFact(FrozenDomainModel):
    schema_version: Literal["policy-fact-v1"] = "policy-fact-v1"
    policy_id: str
    province_code: str | None = Field(default=None, pattern=r"^\d{2}$")
    province_name: str
    category: str
    title: str
    published_period: str
    effective_period: str
    tool_summary: str
    eligibility_or_execution: str
    source_id: str
    data_quality: M29DataQuality
    review_status: ReviewStatus


class M29FacilityFact(FrozenDomainModel):
    schema_version: Literal["facility-fact-v1"] = "facility-fact-v1"
    facility_id: str
    name: str
    province_code: str = Field(pattern=r"^\d{2}$")
    province_name: str
    city: str
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    entity_name: str
    entity_scope: str
    facility_type: str
    products_or_route: str
    capacity_value: str | float | int | None
    capacity_unit: str
    operation_year: str
    status: str
    source_id: str
    data_quality: M29DataQuality
    review_status: ReviewStatus


class M29RelationFact(FrozenDomainModel):
    schema_version: Literal["relation-fact-v1"] = "relation-fact-v1"
    relation_id: str
    source_province_code: str = Field(pattern=r"^\d{2}$")
    target_province_code: str = Field(pattern=r"^\d{2}$")
    relation_type: Literal[
        "battery_material",
        "battery_cell",
        "auto_parts",
        "vehicle_collaboration",
        "rd_technology",
        "testing_certification",
        "industrial_park",
        "competition",
        "industry_transfer",
        "logistics",
        "official_agreement",
    ]
    direction: Literal["directed", "bidirectional"]
    involved_entities: list[str]
    reference_period: str
    relation_status: Literal["current", "historical", "planned", "uncertain"]
    evidence_scope: str
    evidence_summary: str
    source_id: str
    data_quality: M29DataQuality
    review_status: ReviewStatus
    coordination_eligible: bool

    @model_validator(mode="after")
    def valid_cross_province_relation(self) -> M29RelationFact:
        if self.source_province_code == self.target_province_code:
            raise ValueError("M29 relation facts must be cross-province")
        if self.coordination_eligible and (
            self.review_status != "accepted" or self.relation_status not in {"current", "planned"}
        ):
            raise ValueError("coordination eligibility requires an accepted credible relation")
        return self


class M29DerivedFeature(FrozenDomainModel):
    schema_version: Literal["derived-feature-v1"] = "derived-feature-v1"
    feature_id: str
    subject_type: Literal["province", "automaker"]
    subject_id: str
    feature_code: str
    value: float = Field(ge=0, le=1)
    baseline_period: str
    input_fact_ids: list[str]
    formula: str
    direction: Literal["positive", "cost", "mixed"]
    winsorization: Literal["p05_p95"] = "p05_p95"
    normalization: Literal["min_max"] = "min_max"
    missing_handling: str
    data_quality: Literal["proxy"] = "proxy"
    method_version: Literal["m29-feature-method-v1"] = "m29-feature-method-v1"


class M29ProvinceProfile(FrozenDomainModel):
    schema_version: Literal["province-profile-v6"] = "province-profile-v6"
    province_code: str = Field(pattern=r"^\d{2}$")
    name: str
    short_name: str
    policy_region: Literal["east", "central", "west"]
    baseline_year: Literal[2025] = 2025
    feature_values: dict[str, float]
    feature_refs: dict[str, str]
    fact_summary: list[str] = Field(min_length=3, max_length=12)
    fact_refs: list[str] = Field(min_length=3, max_length=24)
    data_quality: Literal["proxy"] = "proxy"

    @model_validator(mode="after")
    def valid_profile(self) -> M29ProvinceProfile:
        if self.province_code not in MAINLAND_PROVINCE_CODES:
            raise ValueError("M29 province profile is outside the 31-province scope")
        if set(self.feature_values) != set(self.feature_refs):
            raise ValueError("M29 province features and references must match")
        if any(value < 0 or value > 1 for value in self.feature_values.values()):
            raise ValueError("M29 province features must be normalized")
        return self


class M29AutomakerProfile(FrozenDomainModel):
    schema_version: Literal["automaker-profile-v2"] = "automaker-profile-v2"
    automaker_id: str
    display_name: str
    entity_scope: str
    baseline_year: Literal[2025] = 2025
    feature_values: dict[str, float]
    feature_refs: dict[str, str]
    fact_summary: list[str] = Field(min_length=3, max_length=12)
    fact_refs: list[str] = Field(min_length=3, max_length=30)
    production_province_codes: list[str]
    technology_route_mix: dict[str, float]
    product_segment_mix: dict[str, float]
    expansion_posture: Literal["expansion", "disciplined", "defensive"]
    data_quality: Literal["proxy"] = "proxy"

    @model_validator(mode="after")
    def valid_profile(self) -> M29AutomakerProfile:
        if self.automaker_id not in AUTOMAKER_IDS:
            raise ValueError("unknown M29 automaker")
        if set(self.feature_values) != set(self.feature_refs):
            raise ValueError("M29 automaker features and references must match")
        if any(value < 0 or value > 1 for value in self.feature_values.values()):
            raise ValueError("M29 automaker features must be normalized")
        if not set(self.production_province_codes) <= set(MAINLAND_PROVINCE_CODES):
            raise ValueError("M29 automaker footprint contains an unknown province")
        for mix in (self.technology_route_mix, self.product_segment_mix):
            if abs(sum(mix.values()) - 1) > 1e-6:
                raise ValueError("M29 automaker mixes must sum to one")
        return self


class M29NetworkEdge(FrozenDomainModel):
    edge_id: str
    source_code: str = Field(pattern=r"^\d{2}$")
    target_code: str = Field(pattern=r"^\d{2}$")
    relation_type: Literal["observation", "competition", "coordination"]
    weight: float = Field(ge=0, le=1)
    data_quality: M29DataQuality
    evidence_refs: list[str] = Field(min_length=1, max_length=8)


class M29ProvinceRelationNetwork(FrozenDomainModel):
    schema_version: Literal["province-relation-network-v3"] = "province-relation-network-v3"
    edges: list[M29NetworkEdge]


class M29SnapshotManifest(FrozenDomainModel):
    schema_version: Literal["m29-snapshot-manifest-v1"] = "m29-snapshot-manifest-v1"
    data_version: Literal["nev-m29-2025-v2"] = "nev-m29-2025-v2"
    generated_at: str
    input_files: list[str]
    province_count: Literal[31] = 31
    automaker_count: Literal[10] = 10
    counts: dict[str, int]
    quality_counts: dict[str, int]
    internal_quality_counts: dict[str, int]
    acceptance_counts: dict[str, int]
    selected_periods: dict[str, str]
    missing_value_policy: str
    snapshot_hash: str
