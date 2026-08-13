#!/usr/bin/env python3
import argparse
import asyncio
import json
import os
from pathlib import Path

from simulation.adapters.asyncio_adapter import AsyncioSimulationAdapter
from simulation.llm.fake_provider import FakeLLMProvider
from simulation.llm.live_provider import LiveLLMProvider
from simulation.models.v32 import (
    EventPlan,
    EventTriggerPoint,
    ExperimentDesign,
    ExperimentType,
    PolicyV4,
)
from simulation.services.v32_orchestrator import V32Orchestrator

# This command is the deterministic outage rehearsal. It must never write into
# the Luna namespace or label fallback output as model-generated.
FALLBACK_CACHE_DIR = Path("runtime/cache/v3_2_m31_fallback")
LUNA_CACHE_DIR = Path("runtime/cache/v3_2_m31_luna")


def policy(policy_id: str, values: tuple[float, float, float]) -> PolicyV4:
    return PolicyV4(
        policy_id=policy_id,
        west_central_share=values[0],
        central_central_share=values[1],
        east_central_share=values[2],
    )


def event(*, branch_scope: str) -> EventPlan:
    return EventPlan(
        event_plan_id=f"demo_event_{branch_scope}",
        template_id="intelligent_driving_upgrade",
        name="全国智驾能力升级",
        description="冻结的 V3.2 演示情景假设。",
        trigger_point=EventTriggerPoint.AFTER_AUTOMAKER_INITIAL,
        advance_notice=False,
        informed_agent_types=[],
        affected_subjects=["province", "automaker", "consumer"],
        mechanism_channels=["intelligent_driving_readiness", "consumer_acceptance"],
        branch_scope=branch_scope,
        evidence_refs=["scenario-method:intelligent-driving-upgrade-v1"],
    )


def cases() -> list[tuple[str, ExperimentDesign]]:
    base = policy("demo_control", (0.95, 0.90, 0.85))
    changed = policy("demo_treatment", (0.98, 0.92, 0.86))
    return [
        (
            "西部 95%，中部 90%，东部 85%，比较提高中央承担比例后的模拟变化。",
            ExperimentDesign(
                experiment_type=ExperimentType.POLICY_COMPARISON,
                control_policy=base,
                treatment_policy=changed,
            ),
        ),
        (
            "西部 95%，中部 90%，东部 85%，比较两套政策共同承受智驾升级情景。",
            ExperimentDesign(
                experiment_type=ExperimentType.POLICY_STRESS_TEST,
                control_policy=base,
                treatment_policy=changed,
                event_plan=event(branch_scope="both"),
            ),
        ),
        (
            "西部 95%，中部 90%，东部 85%，检验智驾升级事件的净影响。",
            ExperimentDesign(
                experiment_type=ExperimentType.EVENT_COUNTERFACTUAL,
                control_policy=base,
                treatment_policy=base.model_copy(update={"policy_id": "demo_same_policy"}),
                event_plan=event(branch_scope="treatment_only"),
            ),
        ),
    ]


async def main(*, luna: bool = False) -> None:
    api_key = os.environ.get("POLICYSCOPE_LLM_API_KEY", "")
    if luna and not api_key:
        raise RuntimeError("POLICYSCOPE_LLM_API_KEY is required for --luna")
    cache_dir = LUNA_CACHE_DIR if luna else FALLBACK_CACHE_DIR
    manifest_cases: list[dict[str, object]] = []
    for index, (policy_text, design) in enumerate(cases(), start=1):
        fallback = FakeLLMProvider()
        provider = (
            LiveLLMProvider(
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
            if luna
            else fallback
        )
        legacy = AsyncioSimulationAdapter(
            provider, runtime_dir=Path("runtime/v32/precompute-legacy")
        )
        orchestrator = V32Orchestrator(
            legacy,
            runtime_dir=Path("runtime/v32/precompute"),
            cache_dir=cache_dir,
        )
        world = await orchestrator.create_experiment(policy_text, seed=20260812)
        await orchestrator.confirm_interpretation(
            world.experiment_id,
            world.interpretation.model_copy(update={"status": "confirmed"}),
        )
        await orchestrator.confirm_design(world.experiment_id, design)
        await orchestrator.confirm_baseline(
            world.experiment_id, expected_data_version=orchestrator.m29.manifest.data_version
        )
        completed = await orchestrator.run(world.experiment_id)
        comparison = await orchestrator.get_comparison(world.experiment_id)
        artifact = orchestrator.export_cache(world.experiment_id)
        manifest_cases.append(
            {
                "case": index,
                "experiment_type": design.experiment_type.value,
                "cache_key": completed.versions["cache_key"],
                "artifact": artifact.name,
                "trace_count": sum(
                    len(branch.decision_traces) for branch in completed.branches.values()
                ),
                "invocation_count": sum(
                    len(branch.agent_invocations) for branch in completed.branches.values()
                ),
                "fallback_count": sum(
                    item.fallback_used
                    for branch in completed.branches.values()
                    for item in branch.agent_invocations
                ),
                "delta_gap": comparison.delta_gap,
            }
        )
    manifest = {
        "schema_version": "v32-demo-cache-manifest-v1",
        "product_version": "PolicyScope V3.2",
        "seed": 20260812,
        "case_count": len(manifest_cases),
        "versions": {
            "policy": "policy-v4",
            "world": "world-state-v8",
            "branch": "branch-v7",
            "province_action": "province-action-v7",
            "automaker_action": "automaker-action-v4",
            "decision_trace": "decision-trace-v3",
            "comparison": "comparison-v8",
            "event": "event-v8",
            "mechanism": "nev-policy-env-v5",
            "data": "nev-m29-2025-v2",
            "province_profile": "province-profile-v6",
            "automaker_profile": "automaker-profile-v2",
            "relation_network": "province-relation-network-v3",
        },
        "agent_provider": {
            "mode": "live" if luna else "fallback",
            "model": "gpt-5.6-luna" if luna else "deterministic-fallback",
            "luna_generated": luna,
        },
        "cases": manifest_cases,
    }
    (cache_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"PolicyScope V3.2 cache precomputed: {len(manifest_cases)} cases.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--luna",
        action="store_true",
        help="Generate the isolated reviewed Luna cache; requires POLICYSCOPE_LLM_API_KEY.",
    )
    args = parser.parse_args()
    asyncio.run(main(luna=args.luna))
