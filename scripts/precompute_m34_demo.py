#!/usr/bin/env python3
import argparse
import asyncio
import json
import os
from pathlib import Path

from simulation.adapters.asyncio_adapter import AsyncioSimulationAdapter
from simulation.llm.fake_provider import FakeLLMProvider
from simulation.llm.live_provider import LiveLLMProvider
from simulation.models.m34 import EventPlanV2, ExperimentDesignV2, InteractionWave, MacroTick
from simulation.models.v32 import ExperimentType, PolicyV4
from simulation.services.m34_orchestrator import M34Orchestrator
from simulation.services.replay import canonical_hash

FAKE_DIR = Path("runtime/cache/v3_2_m34_fake_regression")
LUNA_DIR = Path("runtime/cache/v3_2_m34_luna")


def policy(policy_id: str, values: tuple[float, float, float]) -> PolicyV4:
    return PolicyV4(
        policy_id=policy_id,
        west_central_share=values[0],
        central_central_share=values[1],
        east_central_share=values[2],
    )


def event(index: int, branch_scope: str) -> EventPlanV2:
    return EventPlanV2(
        event_plan_id=f"m34_demo_event_{index}_{branch_scope}",
        template_id=("intelligent_driving_upgrade", "battery_node_upgrade_sichuan")[index % 2],
        name=("智驾能力升级", "电池节点能力升级")[index % 2],
        description="M34 冻结情景假设。",
        scheduled_tick=(MacroTick.Q2, MacroTick.Q3)[index % 2],
        release_wave=(InteractionWave.WAVE_0, InteractionWave.WAVE_1)[index % 2],
        branch_scope=branch_scope,
        affected_subjects=["province", "automaker", "consumer", "supply_chain"],
        mechanism_channels=["demand", "industry", "battery"],
        evidence_refs=[f"scenario:m34-demo-{index}"],
    )


def cases() -> list[ExperimentDesignV2]:
    base = policy("control", (0.95, 0.90, 0.85))
    changed = policy("treatment", (0.98, 0.92, 0.86))
    return [
        ExperimentDesignV2(
            experiment_type=ExperimentType.POLICY_COMPARISON,
            control_policy=base,
            treatment_policy=changed,
        ),
        ExperimentDesignV2(
            experiment_type=ExperimentType.POLICY_STRESS_TEST,
            control_policy=base,
            treatment_policy=changed,
            event_plans=[event(0, "both"), event(1, "both")],
        ),
        ExperimentDesignV2(
            experiment_type=ExperimentType.EVENT_COUNTERFACTUAL,
            control_policy=base,
            treatment_policy=base.model_copy(update={"policy_id": "treatment_same"}),
            event_plans=[event(0, "treatment_only")],
        ),
    ]


async def run_case(
    design: ExperimentDesignV2,
    *,
    case_index: int,
    repetition: int,
    luna: bool,
    output_dir: Path,
) -> dict[str, object]:
    fallback = FakeLLMProvider()
    if luna:
        api_key = os.environ.get("POLICYSCOPE_LLM_API_KEY", "")
        if not api_key:
            raise RuntimeError("POLICYSCOPE_LLM_API_KEY is required for --luna")
        provider = LiveLLMProvider(
            api_key=api_key,
            base_url=os.environ.get("POLICYSCOPE_LLM_BASE_URL", "https://api.openai.com/v1"),
            central_model=os.environ.get("POLICYSCOPE_CENTRAL_MODEL", "gpt-5.6-luna"),
            province_model=os.environ.get("POLICYSCOPE_PROVINCE_MODEL", "gpt-5.6-luna"),
            automaker_model=os.environ.get("POLICYSCOPE_AUTOMAKER_MODEL", "gpt-5.6-luna"),
            fallback=fallback,
            timeout_seconds=60,
            max_concurrency=16,
            max_tokens=4096,
        )
    else:
        provider = fallback
    runtime_dir = output_dir / "runs" / f"case-{case_index}" / f"run-{repetition}"
    legacy = AsyncioSimulationAdapter(provider, runtime_dir=runtime_dir / "legacy")
    orchestrator = M34Orchestrator(
        legacy,
        runtime_dir=runtime_dir / "m34",
        cache_dir=output_dir,
    )
    experiment_id = f"exp_m34_{case_index:012x}"
    world = await orchestrator.create_experiment(
        "西部 95%，中部 90%，东部 85%，按 Q1–Q4 进行年度同源推演。",
        experiment_id=experiment_id,
    )
    await orchestrator.confirm_interpretation(
        experiment_id, world.interpretation.model_copy(update={"status": "confirmed"})
    )
    await orchestrator.confirm_design(experiment_id, design)
    await orchestrator.confirm_baseline(experiment_id)
    completed = await orchestrator.run(experiment_id, until_tick=MacroTick.Q4)
    comparison = await orchestrator.get_comparison(experiment_id)
    fallback_count = sum(
        item.fallback_used for branch in completed.branches.values() for item in branch.decisions
    )
    if luna and fallback_count:
        raise RuntimeError("Luna cache generation produced fallback output; cache rejected")
    return {
        "snapshot": str(
            (runtime_dir / "m34" / experiment_id / "runtime-snapshot.json").relative_to(output_dir)
        ),
        "experiment_type": design.experiment_type.value,
        "checkpoint_hashes": {
            role: [branch.checkpoints[tick].settlement.state_hash for tick in MacroTick]
            for role, branch in completed.branches.items()
        },
        "comparison_hash": canonical_hash(comparison),
        "fallback_count": fallback_count,
        "decision_count": sum(len(branch.decisions) for branch in completed.branches.values()),
        "message_count": sum(len(branch.messages) for branch in completed.branches.values()),
    }


async def main(*, luna: bool) -> None:
    output_dir = LUNA_DIR if luna else FAKE_DIR
    repetitions = 1 if luna else 3
    manifest_cases = []
    for case_index, design in enumerate(cases(), 1):
        runs = [
            await run_case(
                design,
                case_index=case_index,
                repetition=repetition,
                luna=luna,
                output_dir=output_dir,
            )
            for repetition in range(1, repetitions + 1)
        ]
        signatures = {
            canonical_hash(
                {
                    "checkpoint_hashes": run["checkpoint_hashes"],
                    "comparison_hash": run["comparison_hash"],
                    "decision_count": run["decision_count"],
                    "message_count": run["message_count"],
                }
            )
            for run in runs
        }
        if len(signatures) != 1:
            raise RuntimeError(f"M34 deterministic regression mismatch in case {case_index}")
        manifest_cases.append(
            {
                "case": case_index,
                "experiment_type": design.experiment_type.value,
                "consistency_hash": signatures.pop(),
                "runs": runs,
            }
        )
    manifest = {
        "schema_version": "m34-demo-cache-manifest-v1",
        "product_version": "v3_2_m34",
        "mode": "luna" if luna else "fake_regression",
        "luna_generated": luna,
        "fallback_expected": not luna,
        "case_count": 3,
        "repetitions": repetitions,
        "cases": manifest_cases,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"M34 {'Luna' if luna else 'Fake regression'} artifacts: 3 cases x {repetitions} run(s)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--luna", action="store_true")
    arguments = parser.parse_args()
    asyncio.run(main(luna=arguments.luna))
