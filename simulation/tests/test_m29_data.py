import json
from collections import Counter

from simulation.domain_constants import AUTOMAKER_IDS, MAINLAND_PROVINCE_CODES
from simulation.m29_data import M29_DATA_DIR, load_m29_snapshot


def test_m29_snapshot_has_complete_subjects_and_no_orphans() -> None:
    snapshot = load_m29_snapshot()
    assert set(snapshot.province_profiles) == set(MAINLAND_PROVINCE_CODES)
    assert set(snapshot.automaker_profiles) == set(AUTOMAKER_IDS)
    assert all(fact.source_id in snapshot.sources for fact in snapshot.facts.values())
    assert len(snapshot.facts) == len(set(snapshot.facts))
    assert len(snapshot.relation_facts) == len(set(snapshot.relation_facts))


def test_m29_requirement_governance_is_complete() -> None:
    requirements = json.loads((M29_DATA_DIR / "requirements_acceptance_v1.json").read_text())
    assert len(requirements) == 177
    counts = Counter(item["final_status"] for item in requirements)
    assert counts == {"accepted_trusted": 177}
    assert sum(counts.values()) == 177
    assert all(item.get("decision_reason") for item in requirements)


def test_m29_networks_are_separate_and_coordination_is_evidence_backed() -> None:
    snapshot = load_m29_snapshot()
    grouped = Counter(edge.relation_type for edge in snapshot.relation_network.edges)
    assert grouped["observation"] == 93
    assert grouped["competition"] == 93
    assert grouped["coordination"] > 0
    assert all(edge.source_code != edge.target_code for edge in snapshot.relation_network.edges)
    for edge in snapshot.relation_network.edges:
        if edge.relation_type == "coordination":
            assert all(ref in snapshot.relation_facts for ref in edge.evidence_refs)
            assert all(
                snapshot.relation_facts[ref].coordination_eligible for ref in edge.evidence_refs
            )
            assert all(
                snapshot.relation_facts[ref].review_status == "accepted"
                for ref in edge.evidence_refs
            )


def test_m29_derived_features_are_proxy_and_traceable() -> None:
    snapshot = load_m29_snapshot()
    assert len(snapshot.features) == 31 * 21 + 10 * 6
    assert all(feature.data_quality == "proxy" for feature in snapshot.features.values())
    assert all(feature.formula for feature in snapshot.features.values())
    assert all(0 <= feature.value <= 1 for feature in snapshot.features.values())
    for profile in snapshot.province_profiles.values():
        assert set(profile.feature_refs.values()) <= set(snapshot.features)
        assert profile.fact_refs


def test_m29_period_selection_uses_whole_family_fallback() -> None:
    snapshot = load_m29_snapshot()
    assert snapshot.manifest.selected_periods["gdp_total"] == "2024"
    assert snapshot.manifest.selected_periods["resident_population"] == "2024"
    assert snapshot.manifest.data_version == "nev-m29-2025-v2"


def test_m29_trusted_estimates_fill_priority_gaps() -> None:
    snapshot = load_m29_snapshot()
    assert snapshot.manifest.quality_counts == {"trusted": len(snapshot.facts)}
    for code in MAINLAND_PROVINCE_CODES:
        province_metrics = {
            fact.metric_code
            for fact in snapshot.facts.values()
            if fact.subject_type == "province" and fact.subject_id == code
        }
        assert {
            "nev_production",
            "nev_penetration_rate",
            "charging_piles_total",
            "intelligent_driving_readiness_index",
            "regulatory_execution_capacity_index",
            "oil_price_sensitivity_index",
        } <= province_metrics
    for automaker_id in AUTOMAKER_IDS:
        automaker_metrics = {
            fact.metric_code
            for fact in snapshot.facts.values()
            if fact.subject_type == "automaker" and fact.subject_id == automaker_id
        }
        assert all(
            f"channel_coverage_index__{code}" in automaker_metrics
            for code in MAINLAND_PROVINCE_CODES
        )
