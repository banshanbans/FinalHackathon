#!/usr/bin/env python3
import argparse
import asyncio
import json
import os
from collections import Counter
from pathlib import Path
from time import perf_counter

from simulation.adapters.asyncio_adapter import AsyncioSimulationAdapter
from simulation.llm.cached_provider import CachedLLMProvider
from simulation.llm.fake_provider import FakeLLMProvider
from simulation.models.common import Phase, RunMode
from simulation.models.experiment import ExperimentConfig


async def run(assert_complete: bool) -> None:
    started_at = perf_counter()
    requested_mode = RunMode(os.getenv("POLICYSCOPE_RUN_MODE", "fake"))
    fallback = FakeLLMProvider()
    provider = (
        CachedLLMProvider(Path("runtime/cache/v3_1"), fallback, write_through=True)
        if requested_mode is RunMode.CACHE
        else fallback
    )
    adapter = AsyncioSimulationAdapter(provider, runtime_dir=Path("runtime"))
    result = await adapter.run_full_demo(
        ExperimentConfig(
            objective=(
                "比较冻结中央政策与事件情景对地方财政空间、新能源汽车需求和产业布局的模拟影响。"
            ),
            run_mode=requested_mode,
            model_version=(
                "cache-nev-v2"
                if requested_mode is RunMode.CACHE
                else f"{requested_mode.value}-nev-v2"
            ),
        )
    )
    control = await adapter.get_state(result.experiment_id, result.control_branch_id)
    treatment = await adapter.get_state(result.experiment_id, result.treatment_branch_id)
    action_modes = Counter(
        action.run_mode.value
        for world in (control, treatment)
        for action in [*world.province_actions.values(), *world.automaker_actions.values()]
    )
    audit = await adapter.get_audit(result.experiment_id, limit=500)
    summary = {
        "schema_version": result.schema_version,
        "experiment_id": result.experiment_id,
        "province_count": len(result.province_deltas),
        "automaker_count": len(result.automaker_strategy_transitions),
        "control_branch": result.control_branch_id,
        "treatment_branch": result.treatment_branch_id,
        "control_phase": control.phase.value,
        "treatment_phase": treatment.phase.value,
        "policy_diff": [item.model_dump(mode="json") for item in result.policy_diff],
        "delta_gap": result.delta_gap,
        "six_metric_count": len(result.national_metrics),
        "province_strategy_transition_count": len(result.province_strategy_transitions),
        "automaker_strategy_transition_count": len(result.automaker_strategy_transitions),
        "event_transition_count": len(result.province_event_transitions),
        "comparison_mode": result.comparison_mode.value,
        "active_difference": result.active_difference_proof.active_difference,
        "audit_record_count": len(audit.records),
        "audit_chain_valid": adapter.replay.verify_audit_chain(result.experiment_id),
        "final_action_modes": dict(sorted(action_modes.items())),
        "cache_hits": getattr(provider, "cache_hits", None),
        "cache_misses": getattr(provider, "cache_misses", None),
        "elapsed_seconds": round(perf_counter() - started_at, 4),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if assert_complete:
        assert summary["schema_version"] == "comparison-v5"
        assert summary["province_count"] == 31
        assert summary["automaker_count"] == 10
        assert summary["control_phase"] == Phase.Y2_Q4.value
        assert summary["treatment_phase"] == Phase.Y2_Q4.value
        assert summary["province_strategy_transition_count"] == 31
        assert summary["automaker_strategy_transition_count"] == 10
        assert summary["event_transition_count"] == 31
        assert summary["six_metric_count"] == 6
        assert summary["audit_record_count"] > 0
        assert summary["audit_chain_valid"] is True
        assert len(summary["policy_diff"]) >= 1
        assert summary["elapsed_seconds"] < 20
        if requested_mode is RunMode.CACHE:
            assert summary["final_action_modes"].get("fallback", 0) == 0
            assert summary["cache_hits"] == 281
            assert summary["cache_misses"] == 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assert-complete", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.assert_complete))


if __name__ == "__main__":
    main()
