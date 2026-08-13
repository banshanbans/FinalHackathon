#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from simulation.models.m34 import WorldStateV10
from simulation.services.replay import canonical_hash

FAKE_DIR = Path("runtime/cache/v3_2_m34_fake_regression")
LUNA_DIR = Path("runtime/cache/v3_2_m34_luna")
FORBIDDEN_KEYS = {"reasoning_content", "chain_of_thought", "thoughts"}


def all_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {key for child in value.values() for key in all_keys(child)}
    if isinstance(value, list):
        return {key for child in value for key in all_keys(child)}
    return set()


def main(*, luna: bool) -> None:
    root = LUNA_DIR if luna else FAKE_DIR
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "m34-demo-cache-manifest-v1"
    assert manifest["product_version"] == "v3_2_m34"
    assert manifest["case_count"] == 3
    assert manifest["luna_generated"] is luna
    assert manifest["fallback_expected"] is (not luna)
    for case in manifest["cases"]:
        signatures = set()
        for run in case["runs"]:
            payload = json.loads((root / run["snapshot"]).read_text(encoding="utf-8"))
            assert payload["schema_version"] == "runtime-snapshot-v2"
            assert not FORBIDDEN_KEYS.intersection(all_keys(payload))
            world = WorldStateV10.model_validate(payload["world"])
            assert world.product_version == "v3_2_m34"
            assert world.central_call_count == 2
            assert all(len(branch.checkpoints) == 4 for branch in world.branches.values())
            fallback_count = sum(
                item.fallback_used
                for branch in world.branches.values()
                for item in branch.decisions
            )
            assert (fallback_count == 0) is luna
            signature = canonical_hash(
                {
                    "checkpoint_hashes": run["checkpoint_hashes"],
                    "comparison_hash": run["comparison_hash"],
                    "decision_count": run["decision_count"],
                    "message_count": run["message_count"],
                }
            )
            assert signature == case["consistency_hash"]
            signatures.add(signature)
        assert len(signatures) == 1
    print(json.dumps({"verified": True, "mode": manifest["mode"], "cases": 3}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--luna", action="store_true")
    arguments = parser.parse_args()
    main(luna=arguments.luna)
