from pathlib import Path

import pytest
from pydantic import ValidationError

from simulation.adapters.asyncio_adapter import AsyncioSimulationAdapter
from simulation.envs.quarterly_policy_env import settle_quarter
from simulation.llm.fake_provider import FakeLLMProvider
from simulation.models.m34 import (
    EventPlanV2,
    ExperimentDesignV2,
    InteractionWave,
    MacroTick,
    MessageVisibility,
    TransactionState,
)
from simulation.models.v32 import ExperimentType, PolicyV4
from simulation.services.m34_orchestrator import M34Orchestrator


def policy(policy_id: str, values: tuple[float, float, float]) -> PolicyV4:
    return PolicyV4(
        policy_id=policy_id,
        west_central_share=values[0],
        central_central_share=values[1],
        east_central_share=values[2],
    )


def event(
    index: int,
    *,
    branch_scope: str = "both",
    conflict_group: str | None = None,
) -> EventPlanV2:
    return EventPlanV2(
        event_plan_id=f"event_{index}",
        template_id=f"template_{index}",
        name=f"事件 {index}",
        description="冻结情景假设",
        conflict_group=conflict_group,
        scheduled_tick=(MacroTick.Q2, MacroTick.Q3, MacroTick.Q4)[(index - 1) % 3],
        release_wave=(
            InteractionWave.WAVE_0,
            InteractionWave.WAVE_1,
            InteractionWave.WAVE_2,
        )[(index - 1) % 3],
        branch_scope=branch_scope,
        advance_notice=False,
        affected_subjects=["province", "automaker"],
        mechanism_channels=["demand", "industry"],
        evidence_refs=[f"scenario:event-{index}"],
    )


def service(tmp_path: Path) -> M34Orchestrator:
    legacy = AsyncioSimulationAdapter(FakeLLMProvider(), runtime_dir=tmp_path / "legacy")
    return M34Orchestrator(legacy, runtime_dir=tmp_path / "m34")


async def prepare(
    orchestrator: M34Orchestrator,
    *,
    design: ExperimentDesignV2 | None = None,
):
    world = await orchestrator.create_experiment("西部 95%，中部 90%，东部 85%，进行年度同源对比。")
    await orchestrator.confirm_interpretation(
        world.experiment_id,
        world.interpretation.model_copy(update={"status": "confirmed"}),
    )
    design = design or ExperimentDesignV2(
        experiment_type=ExperimentType.POLICY_COMPARISON,
        control_policy=policy("control", (0.95, 0.90, 0.85)),
        treatment_policy=policy("treatment", (0.98, 0.92, 0.86)),
    )
    await orchestrator.confirm_design(world.experiment_id, design)
    return await orchestrator.confirm_baseline(world.experiment_id)


def test_event_plan_cardinality_uniqueness_and_conflicts() -> None:
    control = policy("control", (0.95, 0.90, 0.85))
    treatment = policy("treatment", (0.98, 0.92, 0.86))
    ExperimentDesignV2(
        experiment_type=ExperimentType.POLICY_COMPARISON,
        control_policy=control,
        treatment_policy=treatment,
    )
    ExperimentDesignV2(
        experiment_type=ExperimentType.POLICY_STRESS_TEST,
        control_policy=control,
        treatment_policy=treatment,
        event_plans=[event(1)],
    )
    ExperimentDesignV2(
        experiment_type=ExperimentType.POLICY_STRESS_TEST,
        control_policy=control,
        treatment_policy=treatment,
        event_plans=[event(1), event(2), event(3)],
    )
    with pytest.raises(ValidationError, match="unique"):
        ExperimentDesignV2(
            experiment_type=ExperimentType.POLICY_STRESS_TEST,
            control_policy=control,
            treatment_policy=treatment,
            event_plans=[event(1), event(1)],
        )
    with pytest.raises(ValidationError, match="mutually exclusive"):
        ExperimentDesignV2(
            experiment_type=ExperimentType.POLICY_STRESS_TEST,
            control_policy=control,
            treatment_policy=treatment,
            event_plans=[
                event(1, conflict_group="energy-price"),
                event(2, conflict_group="energy-price"),
            ],
        )


async def test_q1_wave_zero_has_41_agents_per_branch_and_authorized_inboxes(
    tmp_path: Path,
) -> None:
    orchestrator = service(tmp_path)
    world = await prepare(orchestrator)
    world = await orchestrator.run(world.experiment_id, until_tick=MacroTick.Q1)
    for branch in world.branches.values():
        wave_zero = [
            item
            for item in branch.decisions
            if item.tick is MacroTick.Q1 and item.wave is InteractionWave.WAVE_0
        ]
        assert len(wave_zero) == 41
        assert len({item.agent_id for item in wave_zero}) == 41
        messages = {item.message_id: item for item in branch.messages}
        for inbox in branch.inboxes:
            for message_id in inbox.message_ids:
                message = messages[message_id]
                assert message.branch_id == branch.branch_id
                if message.visibility is MessageVisibility.PRIVATE:
                    assert (
                        inbox.agent_id == message.sender_id
                        or inbox.agent_id in message.recipient_ids
                    )
        assert all(item.fallback_used for item in branch.decisions)


async def test_quarter_settlement_is_order_independent_and_checkpoint_is_immutable(
    tmp_path: Path,
) -> None:
    orchestrator = service(tmp_path)
    world = await prepare(orchestrator)
    world = await orchestrator.run(world.experiment_id, until_tick=MacroTick.Q1)
    branch = world.branches["control"]
    settled = [
        item
        for item in branch.sessions
        if item.tick is MacroTick.Q1 and item.state is TransactionState.SETTLED
    ]
    first = settle_quarter(
        None,
        (branch.policy, branch.latest_province_actions, branch.latest_automaker_actions),
        settled,
        [],
        branch_id=branch.branch_id,
        tick=MacroTick.Q1,
    )
    second = settle_quarter(
        None,
        (branch.policy, branch.latest_province_actions, branch.latest_automaker_actions),
        list(reversed(settled)),
        [],
        branch_id=branch.branch_id,
        tick=MacroTick.Q1,
    )
    assert first.state_hash == second.state_hash
    checkpoint = branch.checkpoints[MacroTick.Q1]
    with pytest.raises(ValidationError):
        checkpoint.tick = MacroTick.Q2


async def test_full_year_has_four_checkpoints_resource_conservation_and_comparison(
    tmp_path: Path,
) -> None:
    orchestrator = service(tmp_path)
    design = ExperimentDesignV2(
        experiment_type=ExperimentType.POLICY_STRESS_TEST,
        control_policy=policy("control", (0.95, 0.90, 0.85)),
        treatment_policy=policy("treatment", (0.98, 0.92, 0.86)),
        event_plans=[event(1), event(2), event(3)],
    )
    world = await prepare(orchestrator, design=design)
    baseline_timeline = await orchestrator.get_presentation_timeline(world.experiment_id)
    assert [item.kind for item in baseline_timeline.nodes] == ["policy"]
    world = await orchestrator.run(world.experiment_id, until_tick=MacroTick.Q4)
    assert world.central_call_count == 2
    for branch in world.branches.values():
        assert branch.completed_ticks == list(MacroTick)
        assert len(branch.checkpoints) == 4
        assert len({item.checkpoint_id for item in branch.checkpoints.values()}) == 4
        for tick in MacroTick:
            assert sum(item.tick is tick for item in branch.decisions) <= 180
            assert sum(item.tick is tick for item in branch.messages) <= 500
        assert all(value >= 0 for value in branch.remaining_province_budget.values())
        assert all(value >= 0 for value in branch.remaining_automaker_budget.values())
        assert all(
            branch.remaining_province_budget[code]
            <= branch.province_resource_envelopes[code].available_policy_budget
            for code in branch.remaining_province_budget
        )
        assert all(
            branch.remaining_automaker_budget[agent_id]
            <= branch.automaker_resource_envelopes[agent_id].national_market_budget
            for agent_id in branch.remaining_automaker_budget
        )
    comparison = await orchestrator.get_comparison(world.experiment_id)
    assert comparison.schema_version == "comparison-v10"
    assert comparison.same_event is True
    assert comparison.active_difference == "policy"
    timeline = await orchestrator.get_presentation_timeline(world.experiment_id)
    assert timeline.schema_version == "presentation-timeline-v4"
    assert {item.tick for item in timeline.nodes if item.kind == "settlement"} == set(MacroTick)


async def test_runtime_snapshot_restores_with_hashes(tmp_path: Path) -> None:
    orchestrator = service(tmp_path)
    world = await prepare(orchestrator)
    world = await orchestrator.run(world.experiment_id, until_tick=MacroTick.Q1)
    restored = service(tmp_path)
    state = await restored.get_state(world.experiment_id)
    assert state == world
    events = await restored.get_events(world.experiment_id)
    assert events
    assert events == await orchestrator.get_events(world.experiment_id)
    resumed = await restored.get_events(world.experiment_id, events[-2].event_id)
    assert resumed == [events[-1]]
    with pytest.raises(ValueError, match="LAST_EVENT_ID_INVALID"):
        await restored.get_events(world.experiment_id, "not-an-event-id")
