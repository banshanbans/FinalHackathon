#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from simulation.models.v32 import BranchRuntimeState, ComparisonResultV6, SimulationRound

FALLBACK_CACHE_DIR = Path("runtime/cache/v3_2_m31_fallback")
LUNA_CACHE_DIR = Path("runtime/cache/v3_2_m31_luna")
EXPECTED_TYPES = {"policy_comparison", "policy_stress_test", "event_counterfactual"}
FORBIDDEN_KEYS = {"reasoning_content", "chain_of_thought", "thoughts"}


def all_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {key for child in value.values() for key in all_keys(child)}
    if isinstance(value, list):
        return {key for child in value for key in all_keys(child)}
    return set()


def verify_branch(branch: BranchRuntimeState, *, luna: bool) -> None:
    assert branch.completed_rounds == list(SimulationRound)
    assert len(branch.province_initial_actions) == 31
    assert len(branch.province_final_actions) == 31
    assert len(branch.automaker_initial_actions) == 10
    assert len(branch.automaker_final_actions) == 10
    assert len(branch.decision_traces) == 82
    assert len(branch.agent_invocations) == 113
    if luna:
        assert all(not item.fallback_used for item in branch.agent_invocations)
        assert all(item.model == "gpt-5.6-luna" for item in branch.agent_invocations)
    else:
        assert all(item.fallback_used for item in branch.agent_invocations)
    assert len(branch.province_states) == 31
    assert all(
        len(action.province_market_actions) == 31
        for action in branch.automaker_final_actions.values()
    )
    assert all(
        len(batch.enterprise_offers) <= 2 for batch in branch.province_proposal_batches.values()
    )
    for action in branch.automaker_final_actions.values():
        offers = [
            item
            for item in branch.province_enterprise_offers
            if item.target_automaker_id == action.automaker_id
        ]
        assert {item.offer_id for item in action.enterprise_offer_responses} == {
            item.offer_id for item in offers
        }
        assert sum(item.decision == "accept" for item in action.enterprise_offer_responses) <= 5
    assert all(
        item.channel_contribution == item.industry_contribution == 0
        for item in branch.province_enterprise_matches
        if item.status != "matched"
    )


def main(*, luna: bool = False) -> None:
    cache_dir = LUNA_CACHE_DIR if luna else FALLBACK_CACHE_DIR
    manifest = json.loads((cache_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "v32-demo-cache-manifest-v1"
    assert manifest["case_count"] == 3
    assert manifest["versions"]["data"] == "nev-m29-2025-v2"
    assert manifest["agent_provider"] == (
        {"mode": "live", "model": "gpt-5.6-luna", "luna_generated": True}
        if luna
        else {
            "mode": "fallback",
            "model": "deterministic-fallback",
            "luna_generated": False,
        }
    )
    assert {case["experiment_type"] for case in manifest["cases"]} == EXPECTED_TYPES
    verified: list[dict[str, object]] = []
    for case in manifest["cases"]:
        artifact = cache_dir / case["artifact"]
        payload = json.loads(artifact.read_text(encoding="utf-8"))
        assert payload["schema_version"] == "v32-m31-agent-cache-v1"
        assert payload["agent_provider"]["mode"] == ("live" if luna else "fake")
        assert payload["agent_provider"]["province_model"] == (
            "gpt-5.6-luna" if luna else "deterministic-fallback"
        )
        assert payload["agent_provider"]["fallback_count"] == (0 if luna else 226)
        assert case["fallback_count"] == (0 if luna else 226)
        assert payload["cache_key"] == case["cache_key"]
        assert payload["versions"]["cache_key"] == case["cache_key"]
        assert payload["versions"]["data"] == "nev-m29-2025-v2"
        assert not FORBIDDEN_KEYS.intersection(all_keys(payload))
        branches = {
            key: BranchRuntimeState.model_validate(value)
            for key, value in payload["branches"].items()
        }
        assert set(branches) == {"control", "treatment"}
        for branch in branches.values():
            verify_branch(branch, luna=luna)
        comparison = ComparisonResultV6.model_validate(payload["comparison"])
        assert comparison.schema_version == "comparison-v8"
        assert comparison.experiment_type.value == case["experiment_type"]
        verified.append(
            {
                "experiment_type": comparison.experiment_type.value,
                "cache_key": case["cache_key"],
                "trace_count": sum(len(branch.decision_traces) for branch in branches.values()),
            }
        )
    print(json.dumps(verified, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--luna",
        action="store_true",
        help="Verify the isolated live Luna cache and reject any fallback invocation.",
    )
    arguments = parser.parse_args()
    main(luna=arguments.luna)
