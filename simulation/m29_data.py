from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from simulation.data import NetworkEdge
from simulation.domain_constants import AUTOMAKER_IDS, MAINLAND_PROVINCE_CODES
from simulation.models.automaker import (
    AutomakerProfile,
    ProductionFootprint,
    ProvinceChannelCoverage,
)
from simulation.models.common import DataQuality, ExpansionPosture, PolicyRegion
from simulation.models.m29 import (
    M29AutomakerProfile,
    M29DerivedFeature,
    M29FacilityFact,
    M29PolicyFact,
    M29ProvinceProfile,
    M29ProvinceRelationNetwork,
    M29RawFact,
    M29RelationFact,
    M29SnapshotManifest,
    M29SourceRecord,
)
from simulation.models.provenance import ProvenanceRecord
from simulation.models.province import ProvinceProfile
from simulation.services.persona import build_province_personas

PROJECT_ROOT = Path(__file__).resolve().parents[1]
M29_DATA_DIR = PROJECT_ROOT / "data" / "m29"
PROVENANCE_FIELDS = (
    "liquidity_index",
    "sales_scale_index",
    "sales_growth_index",
    "product_segment_mix",
    "profitability_index",
    "production_footprint",
    "technology_route_mix",
    "capacity_utilization_index",
    "channel_coverage_by_province",
)


def _read_json(path: Path) -> object:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _source_year(reference_period: str) -> int:
    match = re.search(r"20\d{2}", reference_period)
    return int(match.group()) if match else 2025


def _quality(value: str) -> DataQuality:
    return DataQuality.VERIFIED if value == "verified" else DataQuality.PROXY


@dataclass(frozen=True)
class M29Snapshot:
    manifest: M29SnapshotManifest
    sources: dict[str, M29SourceRecord]
    facts: dict[str, M29RawFact]
    policy_facts: dict[str, M29PolicyFact]
    facility_facts: dict[str, M29FacilityFact]
    relation_facts: dict[str, M29RelationFact]
    features: dict[str, M29DerivedFeature]
    province_profiles: dict[str, M29ProvinceProfile]
    automaker_profiles: dict[str, M29AutomakerProfile]
    relation_network: M29ProvinceRelationNetwork
    mechanism_province_profiles: dict[str, ProvinceProfile]
    mechanism_automaker_profiles: dict[str, AutomakerProfile]
    observation_network: dict[str, list[NetworkEdge]]

    def evidence(self, prefix: str, object_id: str) -> dict[str, object]:
        indexes: dict[str, tuple[str, dict[str, object]]] = {
            "fact": ("raw_fact", self.facts),
            "feature": ("derived_feature", self.features),
            "relation": ("relation_fact", self.relation_facts),
            "source": ("source_record", self.sources),
        }
        if prefix not in indexes:
            raise KeyError(prefix)
        record_type, index = indexes[prefix]
        try:
            record = index[object_id]
        except KeyError as exc:
            raise KeyError(f"M29 evidence not found: {prefix}:{object_id}") from exc
        return {"type": record_type, "record": record.model_dump(mode="json")}


def _provenance(
    feature: M29DerivedFeature,
    facts: dict[str, M29RawFact],
    sources: dict[str, M29SourceRecord],
) -> ProvenanceRecord:
    fact = next((facts[item] for item in feature.input_fact_ids if item in facts), None)
    if fact is None:
        return ProvenanceRecord(
            source_name="PolicyScope M29 版本化派生方法",
            source_url="https://www.stats.gov.cn/sj/ndsj/",
            source_year=2025,
            retrieved_at=date(2026, 8, 13),
            original_unit="normalized proxy",
            original_value=None,
            transformation=feature.formula[:300],
            missing_value_handling=feature.missing_handling[:160],
            quality=DataQuality.PROXY,
        )
    source = sources[fact.source_id]
    return ProvenanceRecord(
        source_name=str(source.institution)[:120],
        source_url=source.url,
        source_year=_source_year(fact.reference_period),
        retrieved_at=date.fromisoformat(fact.accessed_at),
        original_unit=fact.raw_unit[:80],
        original_value=fact.raw_value,
        transformation=feature.formula[:300],
        missing_value_handling=feature.missing_handling[:160],
        quality=_quality(fact.data_quality),
    )


def load_m29_snapshot(data_dir: Path | None = None) -> M29Snapshot:
    root = data_dir or M29_DATA_DIR
    manifest = M29SnapshotManifest.model_validate(_read_json(root / "snapshot_manifest_v1.json"))
    sources = {
        item.source_id: item
        for raw in _read_json(root / "source_records_v1.json")
        for item in [M29SourceRecord.model_validate(raw)]
    }
    facts = {
        item.record_id: item
        for raw in _read_json(root / "raw_facts_v1.json")
        for item in [M29RawFact.model_validate(raw)]
    }
    policy_facts = {
        item.policy_id: item
        for raw in _read_json(root / "policy_facts_v1.json")
        for item in [M29PolicyFact.model_validate(raw)]
    }
    facility_facts = {
        item.facility_id: item
        for raw in _read_json(root / "facility_facts_v1.json")
        for item in [M29FacilityFact.model_validate(raw)]
    }
    relation_facts = {
        item.relation_id: item
        for raw in _read_json(root / "relation_facts_v1.json")
        for item in [M29RelationFact.model_validate(raw)]
    }
    features = {
        item.feature_id: item
        for raw in _read_json(root / "derived_features_v1.json")
        for item in [M29DerivedFeature.model_validate(raw)]
    }
    province_profiles = {
        item.province_code: item
        for raw in _read_json(root / "province_profiles_v6.json")
        for item in [M29ProvinceProfile.model_validate(raw)]
    }
    automaker_profiles = {
        item.automaker_id: item
        for raw in _read_json(root / "automaker_profiles_v2.json")
        for item in [M29AutomakerProfile.model_validate(raw)]
    }
    relation_network = M29ProvinceRelationNetwork.model_validate(
        _read_json(root / "province_relation_network_v3.json")
    )

    if set(province_profiles) != set(MAINLAND_PROVINCE_CODES):
        raise ValueError("M29 snapshot must contain exactly the frozen 31 provinces")
    if set(automaker_profiles) != set(AUTOMAKER_IDS):
        raise ValueError("M29 snapshot must contain exactly the frozen 10 automakers")
    if any(fact.source_id not in sources for fact in facts.values()):
        raise ValueError("M29 raw facts contain orphan source references")

    observation_network: dict[str, list[NetworkEdge]] = {
        code: [] for code in MAINLAND_PROVINCE_CODES
    }
    for edge in relation_network.edges:
        if edge.relation_type == "observation":
            observation_network[edge.source_code].append(
                NetworkEdge(target=edge.target_code, weight=edge.weight)
            )
    if any(not 3 <= len(edges) <= 5 for edges in observation_network.values()):
        raise ValueError("M29 observation network must expose 3–5 peers per province")

    mechanism_province_profiles: dict[str, ProvinceProfile] = {}
    for code, profile in province_profiles.items():
        profile_features = {key: features[ref] for key, ref in profile.feature_refs.items()}
        mechanism_province_profiles[code] = ProvinceProfile(
            province_code=code,
            name=profile.name,
            short_name=profile.short_name,
            policy_region=PolicyRegion(profile.policy_region),
            **profile.feature_values,
            peer_province_codes=[edge.target for edge in observation_network[code]],
            data_quality=DataQuality.PROXY,
            provenance={
                key: _provenance(feature, facts, sources)
                for key, feature in profile_features.items()
            },
        )

    mechanism_automaker_profiles: dict[str, AutomakerProfile] = {}
    for automaker_id, profile in automaker_profiles.items():
        primary_feature = features[next(iter(profile.feature_refs.values()))]
        base_provenance = _provenance(primary_feature, facts, sources)
        values = profile.feature_values
        channel_estimates = {
            fact.metric_code.removeprefix("channel_coverage_index__"): float(fact.raw_value)
            for fact in facts.values()
            if fact.subject_type == "automaker"
            and fact.subject_id == automaker_id
            and fact.metric_code.startswith("channel_coverage_index__")
            and isinstance(fact.raw_value, (int, float))
        }
        mechanism_automaker_profiles[automaker_id] = AutomakerProfile(
            automaker_id=automaker_id,
            display_name=profile.display_name,
            entity_scope=profile.entity_scope,
            sales_scale_index=values["sales_scale_index"],
            sales_growth_index=values["sales_growth_index"],
            profitability_index=values["profitability_index"],
            liquidity_index=values["liquidity_index"],
            capacity_utilization_index=values["capacity_utilization_index"],
            channel_coverage_by_province=[
                ProvinceChannelCoverage(
                    province_code=code,
                    coverage_index=channel_estimates.get(
                        code,
                        round(
                            min(
                                1.0,
                                0.15
                                + 0.55 * mechanism_province_profiles[code].market_scale
                                + 0.30 * values["sales_scale_index"],
                            ),
                            4,
                        ),
                    ),
                )
                for code in MAINLAND_PROVINCE_CODES
            ],
            production_footprint=[
                ProductionFootprint(
                    province_code=code,
                    role="mixed",
                    baseline_note="M29 公开披露归纳的冻结生产布局",
                    provenance_ref="production_footprint",
                )
                for code in profile.production_province_codes
            ],
            product_segment_mix=profile.product_segment_mix,
            technology_route_mix=profile.technology_route_mix,
            expansion_posture=ExpansionPosture(profile.expansion_posture),
            data_quality=DataQuality.PROXY,
            provenance={field: base_provenance for field in PROVENANCE_FIELDS},
        )

    return M29Snapshot(
        manifest=manifest,
        sources=sources,
        facts=facts,
        policy_facts=policy_facts,
        facility_facts=facility_facts,
        relation_facts=relation_facts,
        features=features,
        province_profiles=province_profiles,
        automaker_profiles=automaker_profiles,
        relation_network=relation_network,
        mechanism_province_profiles=mechanism_province_profiles,
        mechanism_automaker_profiles=mechanism_automaker_profiles,
        observation_network=observation_network,
    )


def load_m29_personas(snapshot: M29Snapshot) -> dict[str, object]:
    return build_province_personas(
        snapshot.mechanism_province_profiles, snapshot.observation_network
    )
