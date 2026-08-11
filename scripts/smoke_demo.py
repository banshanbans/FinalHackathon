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
from simulation.models.common import RunMode
from simulation.models.experiment import ExperimentConfig


async def run(assert_complete: bool) -> None:
    started_at = perf_counter()
    requested_mode = RunMode(os.getenv("POLICYSCOPE_RUN_MODE", "fake"))
    fallback = FakeLLMProvider()
    if requested_mode == RunMode.CACHE:
        provider = CachedLLMProvider(Path("runtime/cache/default"), fallback)
    else:
        provider = fallback
    adapter = AsyncioSimulationAdapter(provider, runtime_dir=Path("runtime"))
    result = await adapter.run_full_demo(
        ExperimentConfig(
            objective=(
                "在有限财政支持下推动制造业设备升级，提高中小企业参与度，"
                "并兼顾绿色转型、就业稳定和区域可达性。"
            ),
            run_mode=requested_mode,
            model_version=f"{requested_mode.value}-v2",
        )
    )
    control = await adapter.get_state(result.experiment_id, result.control_branch_id)
    treatment = await adapter.get_state(result.experiment_id, result.treatment_branch_id)
    action_modes = Counter(
        action.run_mode
        for world in (control, treatment)
        for action in world.province_actions.values()
    )
    summary = {
        "experiment_id": result.experiment_id,
        "province_count": len(result.province_deltas),
        "control_branch": result.control_branch_id,
        "treatment_branch": result.treatment_branch_id,
        "policy_diff": [item.model_dump(mode="json") for item in result.policy_diff],
        "national_deltas": {key: metric.delta for key, metric in result.national_metrics.items()},
        "enterprise_count": len(control.enterprise_states),
        "action_migration_count": sum(item.count for item in result.action_migrations),
        "control_fallback_provinces": control.fallback_provinces,
        "treatment_fallback_provinces": treatment.fallback_provinces,
        "review_id": result.central_review.review_id if result.central_review else None,
        "final_action_modes": dict(sorted(action_modes.items())),
        "elapsed_seconds": round(perf_counter() - started_at, 4),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if assert_complete:
        assert summary["province_count"] == 31
        assert summary["enterprise_count"] == 186
        assert summary["action_migration_count"] == 186
        assert summary["review_id"]
        assert len(summary["policy_diff"]) >= 2
        assert summary["elapsed_seconds"] < 20
        if requested_mode == RunMode.CACHE:
            assert summary["control_fallback_provinces"] == []
            assert summary["treatment_fallback_provinces"] == []


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assert-complete", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.assert_complete))


if __name__ == "__main__":
    main()
