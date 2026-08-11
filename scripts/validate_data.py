#!/usr/bin/env python3
import json

from simulation.data import DATA_DIR, load_network, load_profiles
from simulation.models.common import DataQuality


def validate() -> None:
    profiles = load_profiles()
    network = load_network()
    if len(profiles) != 31:
        raise ValueError(f"expected 31 province profiles, found {len(profiles)}")
    if set(network) != set(profiles):
        raise ValueError("network sources must exactly match province profile codes")
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
    print("Data validation passed: 31 profiles, 31 Top-5 networks, 3 verified sources.")


if __name__ == "__main__":
    validate()
