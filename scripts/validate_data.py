#!/usr/bin/env python3
import json
from collections import Counter

from validate_analysis_map import validate as validate_analysis_map

from simulation.catalog import automaker_catalog, policy_region_catalog
from simulation.data import (
    PROVINCE_MECHANISM_FIELDS,
    build_province_personas,
    load_automaker_profiles,
    load_network,
    load_profiles,
)
from simulation.domain_constants import AUTOMAKER_IDS, MAINLAND_PROVINCE_CODES
from simulation.m29_data import M29_DATA_DIR, load_m29_snapshot
from simulation.models.automaker import AUTOMAKER_PROVENANCE_FIELDS
from simulation.models.common import DataQuality, Phase, PolicyRegion
from simulation.models.policy import PolicySchema


def validate() -> None:
    validate_analysis_map()
    provinces = policy_region_catalog()
    automakers = automaker_catalog()
    profiles = load_profiles()
    automaker_profiles = load_automaker_profiles()
    network = load_network()
    personas = build_province_personas()
    m29 = load_m29_snapshot()

    expected_codes = set(MAINLAND_PROVINCE_CODES)
    if len(provinces) != 31 or set(provinces) != expected_codes:
        raise ValueError("policy region catalog must cover 31 provinces exactly once")
    if "66" in provinces:
        raise ValueError("Xinjiang Production and Construction Corps is not a province agent")
    region_counts = Counter(item.policy_region for item in provinces.values())
    expected_counts = {
        PolicyRegion.WEST: 12,
        PolicyRegion.CENTRAL: 10,
        PolicyRegion.EAST: 9,
    }
    if region_counts != expected_counts:
        raise ValueError(f"invalid policy region split: {region_counts}")

    if tuple(automakers) != AUTOMAKER_IDS or len(set(automakers)) != 10:
        raise ValueError("automaker catalog must contain the 10 frozen unique IDs")
    if set(profiles) != expected_codes or set(personas) != expected_codes:
        raise ValueError("province profiles and personas must cover all 31 provinces")
    if set(network) != expected_codes:
        raise ValueError("peer network must cover all 31 provinces")
    if set(automaker_profiles) != set(AUTOMAKER_IDS):
        raise ValueError("automaker profiles must cover the 10 frozen IDs")
    if set(m29.province_profiles) != expected_codes:
        raise ValueError("M29 province-profile-v6 must cover all 31 provinces")
    if set(m29.automaker_profiles) != set(AUTOMAKER_IDS):
        raise ValueError("M29 automaker-profile-v2 must cover all 10 automakers")
    if any(fact.source_id not in m29.sources for fact in m29.facts.values()):
        raise ValueError("M29 raw fact contains an orphan source ID")
    requirement_records = json.loads(
        (M29_DATA_DIR / "requirements_acceptance_v1.json").read_text(encoding="utf-8")
    )
    if len(requirement_records) != 177 or any(
        item.get("final_status") != "accepted_trusted" for item in requirement_records
    ):
        raise ValueError("M29 must accept all 177 requirements under the trusted-data rule")

    for code, profile in profiles.items():
        if profile.data_quality not in {DataQuality.VERIFIED, DataQuality.PROXY}:
            raise ValueError(f"province {code} uses a disallowed quality label")
        if not set(PROVINCE_MECHANISM_FIELDS) <= set(profile.provenance):
            raise ValueError(f"province {code} lacks mechanism provenance")
        for field_name, source in profile.provenance.items():
            if not source.source_url or not source.source_year or not source.original_unit:
                raise ValueError(f"province {code}.{field_name} provenance is incomplete")
            if source.quality not in {DataQuality.VERIFIED, DataQuality.PROXY}:
                raise ValueError(f"province {code}.{field_name} has invalid quality")

    for automaker_id, profile in automaker_profiles.items():
        if profile.baseline_year != 2025:
            raise ValueError(f"automaker {automaker_id} baseline year must be 2025")
        if not AUTOMAKER_PROVENANCE_FIELDS <= set(profile.provenance):
            raise ValueError(f"automaker {automaker_id} provenance is incomplete")
        for field_name, source in profile.provenance.items():
            if not source.source_url or not source.source_year or not source.original_unit:
                raise ValueError(f"automaker {automaker_id}.{field_name} provenance is incomplete")
            if source.quality is DataQuality.DEMO:
                raise ValueError(f"automaker {automaker_id}.{field_name} cannot be demo data")

    policy = PolicySchema()
    if (
        policy.west_central_share,
        policy.central_central_share,
        policy.east_central_share,
    ) != (0.95, 0.90, 0.85):
        raise ValueError("V3 default central shares must be 95% / 90% / 85%")
    expected_phases = (
        "SETUP",
        "Y1_Q1",
        "Y1_Q2",
        "Y1_Q3",
        "Y1_Q4",
        "YEAR1_REVIEW",
        "Y2_Q1",
        "Y2_Q2",
        "Y2_Q3",
        "Y2_Q4",
        "COMPLETE",
    )
    if tuple(item.value for item in Phase) != expected_phases:
        raise ValueError("annual V3 phase contract is inconsistent")

    print(
        "Data validation passed: 31 provinces (west 12 / central 10 / east 9), "
        "10 automakers, complete provenance, M29 facts/relations/177 requirements, "
        "policy-v3 defaults and annual phases."
    )


if __name__ == "__main__":
    validate()
