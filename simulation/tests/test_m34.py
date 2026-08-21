from pathlib import Path

import pytest
from pydantic import ValidationError

from simulation.adapters.asyncio_adapter import AsyncioSimulationAdapter
from simulation.envs.quarterly_policy_env import settle_quarter
from simulation.llm.fake_provider import FakeLLMProvider
from simulation.models.m34 import (
    EngagementMode,
    EventPlanV2,
    ExperimentDesignV2,
    InteractionSession,
    InteractionWave,
    MacroTick,
    MessageKind,
    MessageVisibility,
    TransactionState,
)
from simulation.models.v32 import ExperimentType, PolicyV4
from simulation.services.m34_orchestrator import M34Orchestrator
from simulation.services.replay import canonical_hash


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
        assert branch.messages
        assert branch.sessions
        assert all(
            item.outgoing_messages
            for item in branch.decisions
            if item.engagement.value == "initiate"
        )
        assert all(
            item.no_action_reason
            for item in branch.decisions
            if item.engagement.value in {"ignore", "monitor"}
        )
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


async def test_domain_validation_rejects_empty_initiate_and_unexplained_monitor(
    tmp_path: Path,
) -> None:
    orchestrator = service(tmp_path)
    world = await prepare(orchestrator)
    world = await orchestrator.run(world.experiment_id, until_tick=MacroTick.Q1)
    branch = world.branches["control"]
    original = branch.decisions[0]
    inbox = next(item for item in branch.inboxes if item.inbox_id == original.inbox_id)

    with pytest.raises(ValueError, match="INITIATE_MESSAGE_REQUIRED"):
        orchestrator._validate_decision(
            branch,
            inbox,
            original.model_copy(
                update={
                    "engagement": EngagementMode.INITIATE,
                    "outgoing_messages": [],
                    "no_action_reason": None,
                }
            ),
        )

    with pytest.raises(ValueError, match="NO_ACTION_REASON_REQUIRED"):
        orchestrator._validate_decision(
            branch,
            inbox,
            original.model_copy(
                update={
                    "engagement": EngagementMode.MONITOR,
                    "outgoing_messages": [],
                    "no_action_reason": None,
                }
            ),
        )

    interactive = next(item for item in branch.decisions if item.outgoing_messages)
    interactive_inbox = next(
        item for item in branch.inboxes if item.inbox_id == interactive.inbox_id
    )
    original_message = interactive.outgoing_messages[0]
    other_recipient = next(
        code
        for code in ("11", "12", "13")
        if code not in {interactive.agent_id, *original_message.recipient_ids}
    )
    invalid_message = original_message.model_copy(
        update={
            "message_id": "message-invalid-multiple-recipients",
            "recipient_ids": [original_message.recipient_ids[0], other_recipient],
        }
    )
    with pytest.raises(ValueError, match="TRANSACTION_SINGLE_COUNTERPART_REQUIRED"):
        orchestrator._validate_decision(
            branch,
            interactive_inbox,
            interactive.model_copy(update={"outgoing_messages": [invalid_message]}),
        )


async def test_q1_automaker_counteroffer_fallback_has_a_summary(tmp_path: Path) -> None:
    orchestrator = service(tmp_path)
    world = await prepare(orchestrator)
    branch = world.branches["control"]
    sender_inbox = orchestrator._build_inbox(
        world,
        branch,
        MacroTick.Q1,
        InteractionWave.WAVE_0,
        "11",
    )
    session_id = next(
        candidate
        for index in range(256)
        if int(
            canonical_hash(((candidate := f"session-q1-counter-{index}"), "byd"))[:2],
            16,
        )
        % 4
        == 0
    )
    proposal = orchestrator._message(
        branch,
        sender_inbox,
        kind=MessageKind.PROVINCE_AUTOMAKER_PACKAGE,
        visibility=MessageVisibility.PRIVATE,
        recipients=["byd"],
        session_id=session_id,
        state=TransactionState.PROPOSED,
        resource_amount=0.02,
        summary="北京向比亚迪模拟主体提出首轮资源包。",
    )
    branch.messages.append(proposal)
    branch.sessions.append(
        InteractionSession(
            session_id=session_id,
            branch_id=branch.branch_id,
            tick=MacroTick.Q1,
            participant_ids=["11", "byd"],
            initiator_id="11",
            state=TransactionState.PROPOSED,
            message_ids=[proposal.message_id],
            reserved_resource=proposal.resource_amount,
        )
    )
    automaker_inbox = orchestrator._build_inbox(
        world,
        branch,
        MacroTick.Q1,
        InteractionWave.WAVE_1,
        "byd",
    )

    responses = orchestrator._fallback_automaker_messages(branch, automaker_inbox)

    assert responses[0].transaction_state is TransactionState.COUNTERED
    assert "首轮验证" in responses[0].public_summary

    next_quarter_inbox = orchestrator._build_inbox(
        world,
        branch,
        MacroTick.Q2,
        InteractionWave.WAVE_0,
        "byd",
    )
    cross_quarter_response = orchestrator._fallback_decision(world, branch, next_quarter_inbox)
    assert cross_quarter_response.attended_message_ids == [proposal.message_id]
    assert next_quarter_inbox.pending_session_ids == [session_id]
    orchestrator._validate_decision(branch, next_quarter_inbox, cross_quarter_response)
    initiator_inbox = orchestrator._build_inbox(
        world,
        branch,
        MacroTick.Q2,
        InteractionWave.WAVE_0,
        "11",
    )
    assert initiator_inbox.pending_session_ids == []


async def test_live_context_reports_remaining_automaker_message_budget(tmp_path: Path) -> None:
    orchestrator = service(tmp_path)
    world = await prepare(orchestrator)
    branch = world.branches["control"]
    automaker_inbox = orchestrator._build_inbox(
        world,
        branch,
        MacroTick.Q1,
        InteractionWave.WAVE_0,
        "byd",
    )
    for index, recipient in enumerate(("11", "12", "13"), 1):
        branch.messages.append(
            orchestrator._message(
                branch,
                automaker_inbox,
                kind=MessageKind.AUTOMAKER_PROVINCE_INTENT,
                visibility=MessageVisibility.PRIVATE,
                recipients=[recipient],
                session_id=f"session-budget-{index}",
                state=TransactionState.PROPOSED,
                resource_amount=0.01,
                summary=f"第 {index} 条已发送互动。",
            )
        )
    next_inbox = orchestrator._build_inbox(
        world,
        branch,
        MacroTick.Q1,
        InteractionWave.WAVE_1,
        "byd",
    )

    context = orchestrator._live_authorized_context(branch, next_inbox)

    assert context.output_constraints.max_automaker_private_messages == 2


async def test_province_fallback_action_respects_remaining_budget(tmp_path: Path) -> None:
    orchestrator = service(tmp_path)
    world = await prepare(orchestrator)
    branch = world.branches["control"]
    branch.remaining_province_budget["11"] = 0.08
    inbox = orchestrator._build_inbox(
        world,
        branch,
        MacroTick.Q1,
        InteractionWave.WAVE_0,
        "11",
    )

    decision = orchestrator._fallback_decision(world, branch, inbox)

    assert decision.province_action is not None
    assert decision.province_action.overall_support_intensity <= 0.08


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
    carried = settle_quarter(
        checkpoint,
        (branch.policy, branch.latest_province_actions, branch.latest_automaker_actions),
        [],
        [],
        branch_id=branch.branch_id,
        tick=MacroTick.Q2,
    )
    assert carried.tick is MacroTick.Q2
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
