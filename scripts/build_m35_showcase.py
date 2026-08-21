#!/usr/bin/env python3
"""Build one complete, reproducible M35 Presentation showcase experiment.

The agent behavior is deterministic FAKE data.  Its narrative playbook was
drafted with Codex gpt-5.6-luna and manually constrained to the frozen M34
schemas, subject list and transaction/resource rules.  Authoritative metrics
continue to come from the quarterly deterministic environment.
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from simulation.adapters.asyncio_adapter import AsyncioSimulationAdapter
from simulation.llm.fake_provider import FakeLLMProvider
from simulation.models.m34 import (
    EventPlanV2,
    ExperimentDesignV2,
    InteractionWave,
    MacroTick,
)
from simulation.models.v32 import ExperimentType, PolicyV4
from simulation.services.m34_orchestrator import M34Orchestrator

DEFAULT_EXPERIMENT_ID = "exp_m34_35ca2026081a"


def policy(policy_id: str, shares: tuple[float, float, float]) -> PolicyV4:
    return PolicyV4(
        policy_id=policy_id,
        west_central_share=shares[0],
        central_central_share=shares[1],
        east_central_share=shares[2],
    )


def showcase_events() -> list[EventPlanV2]:
    return [
        EventPlanV2(
            event_plan_id="m35_showcase_smart_upgrade",
            template_id="intelligent_driving_upgrade",
            name="全国智能化适配升级情景",
            description="检验技术适配变化如何进入省份与车企模拟主体的授权上下文。",
            scheduled_tick=MacroTick.Q2,
            release_wave=InteractionWave.WAVE_0,
            branch_scope="both",
            intensity="medium",
            advance_notice=True,
            affected_subjects=["province", "automaker"],
            mechanism_channels=["consumer_acceptance", "rd_activity"],
            evidence_refs=["scenario-method:intelligent-driving-upgrade-v1"],
        ),
        EventPlanV2(
            event_plan_id="m35_showcase_supply_pressure",
            template_id="battery_node_upgrade_sichuan",
            name="西部电池节点协同情景",
            description="检验供应链距离与共享验证能力对区域协同的影响。",
            scheduled_tick=MacroTick.Q3,
            release_wave=InteractionWave.WAVE_0,
            branch_scope="both",
            intensity="medium",
            advance_notice=False,
            affected_subjects=["province", "automaker"],
            mechanism_channels=["battery_access", "logistics_cost"],
            evidence_refs=["scenario-method:battery-node-upgrade-v1"],
        ),
        EventPlanV2(
            event_plan_id="m35_showcase_cost_pressure",
            template_id="oil_price_rise",
            name="运营成本压力情景",
            description="检验运营成本变化如何触发季度末资源取舍。",
            scheduled_tick=MacroTick.Q4,
            release_wave=InteractionWave.WAVE_0,
            branch_scope="both",
            intensity="low",
            advance_notice=False,
            affected_subjects=["province", "automaker"],
            mechanism_channels=["operating_cost", "consumer_demand"],
            evidence_refs=["scenario-method:oil-price-rise-v1"],
        ),
    ]


async def build(experiment_id: str, runtime_dir: Path) -> None:
    legacy = AsyncioSimulationAdapter(
        FakeLLMProvider(), runtime_dir=runtime_dir / "legacy-showcase"
    )
    orchestrator = M34Orchestrator(legacy, runtime_dir=runtime_dir / "m34")
    world = await orchestrator.create_experiment(
        "西部 98%，中部 92%，东部 86%，构建 M35 年度同源展示方案。",
        experiment_id=experiment_id,
    )
    runtime = orchestrator.runtimes[experiment_id]
    runtime.world.versions.update(
        {
            "demo_narrative": "m35-showcase-v1",
            "narrative_origin": "codex-gpt-5.6-luna-curated",
            "result_origin": "deterministic-quarterly-environment",
        }
    )
    if world.status.value == "completed":
        completed = world
    else:
        await orchestrator.confirm_interpretation(
            experiment_id,
            world.interpretation.model_copy(update={"status": "confirmed"}),
        )
        await orchestrator.confirm_design(
            experiment_id,
            ExperimentDesignV2(
                experiment_type=ExperimentType.POLICY_STRESS_TEST,
                control_policy=policy("m35-showcase-control", (0.95, 0.90, 0.85)),
                treatment_policy=policy("m35-showcase-treatment", (0.98, 0.92, 0.86)),
                event_plans=showcase_events(),
            ),
        )
        await orchestrator.confirm_baseline(experiment_id)
        completed = await orchestrator.run(experiment_id, until_tick=MacroTick.Q4)
    timeline = await orchestrator.get_presentation_timeline(experiment_id)
    comparison = await orchestrator.get_comparison(experiment_id)
    counts = {
        role: {
            "decisions": len(branch.decisions),
            "messages": len(branch.messages),
            "sessions": len(branch.sessions),
            "settled": sum(item.settled_contribution > 0 for item in branch.sessions),
        }
        for role, branch in completed.branches.items()
    }
    print(f"experiment_id={experiment_id}")
    print(f"status={completed.status.value}")
    print(f"timeline_frames={len(timeline.nodes)}")
    print(f"branch_counts={counts}")
    print(f"comparison_metrics={len(comparison.national_metrics)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-id", default=DEFAULT_EXPERIMENT_ID)
    parser.add_argument("--runtime-dir", type=Path, default=Path("runtime"))
    args = parser.parse_args()
    asyncio.run(build(args.experiment_id, args.runtime_dir))
