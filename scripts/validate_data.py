#!/usr/bin/env python3
from collections import Counter

from simulation.catalog import automaker_catalog, policy_region_catalog
from simulation.data import (
    PROVINCE_MECHANISM_FIELDS,
    build_province_personas,
    load_automaker_profiles,
    load_network,
    load_profiles,
)
from simulation.domain_constants import AUTOMAKER_IDS, MAINLAND_PROVINCE_CODES
from simulation.models.automaker import AUTOMAKER_PROVENANCE_FIELDS
from simulation.models.common import DataQuality, Phase, PolicyRegion
from simulation.models.policy import PolicySchema


def validate() -> None:
    provinces = policy_region_catalog()
    automakers = automaker_catalog()
    profiles = load_profiles()
    automaker_profiles = load_automaker_profiles()
    network = load_network()
    personas = build_province_personas()

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
        "10 automakers, complete provenance, policy-v3 defaults and annual phases."
    )


if __name__ == "__main__":
    validate()
