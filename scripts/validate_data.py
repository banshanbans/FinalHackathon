#!/usr/bin/env python3
import json

from simulation.data import (
    DATA_DIR,
    build_enterprise_profiles,
    load_enterprise_archetypes,
    load_enterprise_profiles,
    load_network,
    load_profiles,
)
from simulation.models.common import DataQuality


def validate() -> None:
    profiles = load_profiles()
    network = load_network()
    archetypes = load_enterprise_archetypes()
    enterprises = build_enterprise_profiles(profiles, archetypes)
    frozen_enterprises = load_enterprise_profiles()
    if len(profiles) != 31:
        raise ValueError(f"expected 31 province profiles, found {len(profiles)}")
    if set(network) != set(profiles):
        raise ValueError("network sources must exactly match province profile codes")
    if len(archetypes) != 6 or len(enterprises) != 186:
        raise ValueError("V2 requires 6 archetypes and 31×6 enterprise groups")
    if frozen_enterprises != enterprises:
        raise ValueError("committed enterprise snapshot differs from deterministic generation")
    for code in profiles:
        province_groups = [item for item in enterprises.values() if item.province_code == code]
        if len(province_groups) != 6 or len({item.archetype for item in province_groups}) != 6:
            raise ValueError(f"province {code} does not contain six unique enterprise groups")
        if abs(sum(item.weight for item in province_groups) - 1.0) > 1e-6:
            raise ValueError(f"province {code} enterprise weights must sum to 1")
    for source, edges in network.items():
        if not 3 <= len(edges) <= 5:
            raise ValueError(f"{source} must have between 3 and 5 related provinces")
        targets = [edge.target for edge in edges]
        if len(targets) != len(set(targets)):
            raise ValueError(f"{source} contains duplicate network targets")
        if source in targets:
            raise ValueError(f"{source} contains a self edge")
        unknown = set(targets) - set(profiles)
        if unknown:
            raise ValueError(f"{source} references unknown provinces: {sorted(unknown)}")

    verified = {
        code for code, profile in profiles.items() if profile.data_quality == DataQuality.VERIFIED
    }
    if verified != {"14", "33", "44"}:
        raise ValueError(f"verified set must be 14/33/44, got {sorted(verified)}")
    provenance = json.loads((DATA_DIR / "provenance.json").read_text(encoding="utf-8"))
    if set(provenance["verified_provinces"]) != verified:
        raise ValueError("verified profiles and provenance entries do not match")
    for code, item in provenance["verified_provinces"].items():
        if not item.get("url") or not item.get("transformation"):
            raise ValueError(f"verified province {code} lacks provenance")
    provenance_v2 = json.loads((DATA_DIR / "provenance_v2.json").read_text(encoding="utf-8"))
    if provenance_v2["schema_version"] != "provenance-v2":
        raise ValueError("V2 provenance schema is missing")
    print(
        "Data validation passed: 31 profiles, 186 enterprise groups, "
        "31 Top-5 networks, 3 verified province sources."
    )


if __name__ == "__main__":
    validate()
