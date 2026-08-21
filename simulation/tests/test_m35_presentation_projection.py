from pathlib import Path

import pytest

from simulation.adapters.asyncio_adapter import AsyncioSimulationAdapter
from simulation.llm.fake_provider import FakeLLMProvider
from simulation.models.m34 import (
    EventPlanV2,
    ExperimentDesignV2,
    InteractionWave,
    MacroTick,
    WorldStateV10,
)
from simulation.models.v32 import ExperimentType, PolicyV4
from simulation.services.m34_orchestrator import M34Orchestrator
from simulation.services.m34_presentation import M34PresentationProjection


def _policy(policy_id: str, values: tuple[float, float, float]) -> PolicyV4:
    return PolicyV4(
        policy_id=policy_id,
        west_central_share=values[0],
        central_central_share=values[1],
        east_central_share=values[2],
    )


@pytest.fixture(scope="module")
async def completed_quarters_world(tmp_path_factory: pytest.TempPathFactory) -> WorldStateV10:
    root: Path = tmp_path_factory.mktemp("m35-presentation")
    legacy = AsyncioSimulationAdapter(FakeLLMProvider(), runtime_dir=root / "legacy")
    orchestrator = M34Orchestrator(legacy, runtime_dir=root / "m34")
    world = await orchestrator.create_experiment("西部 98%，中部 92%，东部 86%，进行年度同源对比。")
    await orchestrator.confirm_interpretation(
        world.experiment_id,
        world.interpretation.model_copy(update={"status": "confirmed"}),
    )
    await orchestrator.confirm_design(
        world.experiment_id,
        ExperimentDesignV2(
            experiment_type=ExperimentType.POLICY_STRESS_TEST,
            control_policy=_policy("control", (0.95, 0.90, 0.85)),
            treatment_policy=_policy("treatment", (0.98, 0.92, 0.86)),
            event_plans=[
                EventPlanV2(
                    event_plan_id="m35-event",
                    template_id="m35-event-template",
                    name="供应链压力情景",
                    description="验证事件进入授权上下文后的因果展示。",
                    scheduled_tick=MacroTick.Q2,
                    release_wave=InteractionWave.WAVE_1,
                    branch_scope="both",
                    advance_notice=False,
                    affected_subjects=["province", "automaker"],
                    mechanism_channels=["industry"],
                    evidence_refs=["scenario:m35-event"],
                )
            ],
        ),
    )
    await orchestrator.confirm_baseline(world.experiment_id)
    return await orchestrator.run(world.experiment_id, until_tick=MacroTick.Q2)


def test_m35_presentation_projects_causal_story_without_cross_branch_edges(
    completed_quarters_world: WorldStateV10,
) -> None:
    projection = M34PresentationProjection(completed_quarters_world, comparison_available=False)
    timeline = projection.build_timeline()
    wave = next(node for node in timeline.nodes if node.kind == "wave")
    frame = projection.get_frame(wave.node_id)

    assert timeline.schema_version == "presentation-timeline-v4"
    assert frame.schema_version == "presentation-frame-v5"
    assert frame.question
    assert frame.chapter_label.startswith("Q")
    assert frame.wave_label in {"首次行动", "条件回应", "协议收敛"}

    for role in ("control", "treatment"):
        branch = frame.branches[role]
        assert all(edge.branch_id == role for edge in branch.game_edges)
        assert all(spotlight.branch_id == role for spotlight in branch.spotlights)
        assert [edge.reveal_order for edge in branch.game_edges] == sorted(
            edge.reveal_order for edge in branch.game_edges
        )
        assert all(
            edge.source.subject_ref.startswith(("province:", "automaker:", "event:"))
            and edge.target.subject_ref.startswith(("province:", "automaker:", "event:"))
            for edge in branch.game_edges
        )
        for spotlight in branch.spotlights:
            assert [beat.beat for beat in spotlight.beats] == [
                "focus",
                "observe",
                "decide",
                "action",
                "response",
                "settle",
            ]
            assert spotlight.actor.display_name not in {spotlight.actor.subject_id, ""}
            assert spotlight.counterpart.display_name not in {
                spotlight.counterpart.subject_id,
                "",
            }


def test_m35_uses_one_shared_annual_scale_for_every_frame(
    completed_quarters_world: WorldStateV10,
) -> None:
    projection = M34PresentationProjection(completed_quarters_world, comparison_available=False)
    timeline = projection.build_timeline()
    scales = {
        projection.get_frame(node.node_id).shared_scale.model_dump_json() for node in timeline.nodes
    }
    assert len(scales) == 1
    assert timeline.shared_scale.difference_bound > 0


def test_m35_settlement_spotlight_exposes_result_contribution_truthfully(
    completed_quarters_world: WorldStateV10,
) -> None:
    projection = M34PresentationProjection(completed_quarters_world, comparison_available=False)
    timeline = projection.build_timeline()
    settlement = next(
        node for node in timeline.nodes if node.kind == "settlement" and node.tick.value == "Q1"
    )
    frame = projection.get_frame(settlement.node_id)
    spotlights = [
        spotlight for branch in frame.branches.values() for spotlight in branch.spotlights
    ]
    assert spotlights
    assert any(spotlight.settlement.contributed for spotlight in spotlights)
    assert all(
        spotlight.settlement.contribution == 0
        for spotlight in spotlights
        if not spotlight.settlement.contributed
    )
    assert all(
        change.quarterly_change is None
        for spotlight in spotlights
        for change in [
            *spotlight.settlement.province_changes,
            *spotlight.settlement.national_changes,
        ]
    )
    assert all(spotlight.settlement.direct_contribution_label for spotlight in spotlights)
    assert all(spotlight.settlement.attribution_note for spotlight in spotlights)

    q2_settlement = next(
        node for node in timeline.nodes if node.kind == "settlement" and node.tick.value == "Q2"
    )
    province_code = spotlights[0].settlement.province_changes[0].province_code
    q2_view = projection._settlement_view(  # noqa: SLF001 - projection contract unit test
        completed_quarters_world.branches["control"],
        q2_settlement,
        participant_ids=[province_code],
        contributed=False,
        contribution=0,
        result_summary="测试季度共享变化",
    )
    assert all(
        change.quarterly_change is not None
        for change in [
            *q2_view.province_changes,
            *q2_view.national_changes,
        ]
    )


def test_m351_divergence_union_supports_all_four_user_visible_types(
    completed_quarters_world: WorldStateV10,
) -> None:
    projection = M34PresentationProjection(completed_quarters_world, comparison_available=False)
    timeline = projection.build_timeline()
    wave = next(node for node in timeline.nodes if node.kind == "wave")
    frame = projection.get_frame(wave.node_id)
    original = frame.branches["control"].spotlights[0]
    treatment = original.model_copy(update={"branch_id": "treatment"})

    control_only = projection._divergences(  # noqa: SLF001 - projection contract unit test
        {"control": [original], "treatment": []}
    )
    treatment_only = projection._divergences(  # noqa: SLF001 - projection contract unit test
        {"control": [], "treatment": [treatment]}
    )
    state_changed = projection._divergences(  # noqa: SLF001 - projection contract unit test
        {
            "control": [original],
            "treatment": [
                treatment.model_copy(
                    update={
                        "action": treatment.action.model_copy(
                            update={"state_label": f"{treatment.action.state_label}（变化）"}
                        )
                    }
                )
            ],
        }
    )
    decision_changed = projection._divergences(  # noqa: SLF001 - projection contract unit test
        {
            "control": [original],
            "treatment": [
                treatment.model_copy(
                    update={"decision_summary": f"{treatment.decision_summary}（调整）"}
                )
            ],
        }
    )

    assert control_only[0].divergence_type == "control_only"
    assert control_only[0].treatment_state_label == "未发生"
    assert treatment_only[0].divergence_type == "treatment_only"
    assert treatment_only[0].control_state_label == "未发生"
    assert state_changed[0].divergence_type == "state_changed"
    assert decision_changed[0].divergence_type == "decision_changed"


def test_m35_wave_replay_does_not_leak_same_quarter_settlement(
    completed_quarters_world: WorldStateV10,
) -> None:
    projection = M34PresentationProjection(completed_quarters_world, comparison_available=False)
    timeline = projection.build_timeline()
    q1_wave = next(
        node for node in timeline.nodes if node.kind == "wave" and node.tick.value == "Q1"
    )
    q2_wave = next(
        node for node in timeline.nodes if node.kind == "wave" and node.tick.value == "Q2"
    )
    q1_settlement = next(
        node for node in timeline.nodes if node.kind == "settlement" and node.tick.value == "Q1"
    )
    first_wave = projection.get_frame(q1_wave.node_id)
    second_quarter_wave = projection.get_frame(q2_wave.node_id)
    first_settlement = projection.get_frame(q1_settlement.node_id)

    assert all(
        value.value is None
        for branch in first_wave.branches.values()
        for value in branch.province_values
    )
    assert second_quarter_wave.branches["control"].province_values == (
        first_settlement.branches["control"].province_values
    )


def test_m35_event_frame_projects_event_to_authorized_subject_causal_layer(
    completed_quarters_world: WorldStateV10,
) -> None:
    projection = M34PresentationProjection(completed_quarters_world, comparison_available=False)
    timeline = projection.build_timeline()
    event_node = next(node for node in timeline.nodes if node.kind == "event")
    event_frame = projection.get_frame(event_node.node_id)

    for role in ("control", "treatment"):
        branch = event_frame.branches[role]
        assert branch.game_edges
        assert all(edge.branch_id == role for edge in branch.game_edges)
        assert branch.game_edges[0].source.subject_type == "event"
        assert branch.game_edges[0].relation == "event_impact"
        assert branch.spotlights[0].actor.subject_type == "event"
        assert branch.spotlights[0].counterpart.subject_type in {"province", "automaker"}
        assert all(edge.relation == "event_impact" for edge in branch.game_edges)
