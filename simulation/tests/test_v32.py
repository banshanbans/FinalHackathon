from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from simulation.adapters.asyncio_adapter import AsyncioSimulationAdapter
from simulation.llm.fake_provider import FakeLLMProvider
from simulation.models.v32 import (
    EventIntensityV32,
    EventPlan,
    EventTriggerPoint,
    ExperimentDesign,
    ExperimentType,
    PolicyV4,
    SimulationRound,
)
from simulation.presentation_catalog import presentation_event_catalog
from simulation.services.v32_orchestrator import V32Orchestrator


def service(tmp_path: Path) -> V32Orchestrator:
    legacy = AsyncioSimulationAdapter(FakeLLMProvider(), runtime_dir=tmp_path / "legacy")
    return V32Orchestrator(legacy, runtime_dir=tmp_path / "v32")


def cached_service(tmp_path: Path, *, cache_enabled: bool) -> V32Orchestrator:
    legacy = AsyncioSimulationAdapter(FakeLLMProvider(), runtime_dir=tmp_path / "legacy")
    return V32Orchestrator(
        legacy,
        runtime_dir=tmp_path / ("cache-runtime" if cache_enabled else "source-runtime"),
        cache_dir=tmp_path / "cache",
        cache_enabled=cache_enabled,
    )


class OutsidePriorProvider:
    """Test double proving the orchestrator permits evidence-backed network discovery."""

    run_mode = "live"

    def __init__(self) -> None:
        self.response_payloads: list[dict[str, Any]] = []

    def model_name_for(self, kind: str) -> str:
        del kind
        return "gpt-5.6-luna-test-double"

    async def resolve(self, *, kind, instruction, payload, response_type, fallback):
        del instruction, response_type
        value = fallback()
        if kind == "province_response":
            self.response_payloads.append(payload)
            return value
        if kind != "province_proposal" or value.province_code != "11":
            return value
        prior_targets = {item.target_code for item in payload["coordination_priors"]}
        card = next(
            item for item in payload["partner_cards"] if item["province_code"] not in prior_targets
        )
        target = card["province_code"]
        proposal = value.proposals[0].model_copy(
            update={
                "proposal_id": f"outside_prior_11_{target}",
                "target_province_code": target,
                "basis_type": "inferred_from_context",
                "public_reason": "基于双方产业事实与节点互补，从关系网外发现合作对象。",
                "evidence_refs": card["fact_refs"][:2],
            }
        )
        action = value.proposed_action.model_copy(
            update={
                "action_id": "agent_proposed_action_11",
                "coordination_target_codes": [target],
                "fallback_used": False,
            }
        )
        return value.model_copy(update={"proposed_action": action, "proposals": [proposal]})


def policy(policy_id: str, values: tuple[float, float, float]) -> PolicyV4:
    return PolicyV4(
        policy_id=policy_id,
        west_central_share=values[0],
        central_central_share=values[1],
        east_central_share=values[2],
    )


def event(branch_scope: str = "treatment_only") -> EventPlan:
    return EventPlan(
        event_plan_id="event_intelligent_driving",
        template_id="intelligent_driving_upgrade",
        name="全国智驾能力升级",
        description="冻结情景假设",
        trigger_point=EventTriggerPoint.AFTER_AUTOMAKER_INITIAL,
        advance_notice=False,
        informed_agent_types=[],
        affected_subjects=["province", "automaker", "consumer"],
        mechanism_channels=["intelligent_driving_readiness", "consumer_acceptance"],
        branch_scope=branch_scope,
        evidence_refs=["scenario-method:intelligent-driving-upgrade-v1"],
    )


def catalog_event(
    template_id: str,
    *,
    trigger_point: EventTriggerPoint,
    intensity: EventIntensityV32,
) -> EventPlan:
    template = next(
        item for item in presentation_event_catalog().templates if item.template_id == template_id
    )
    return EventPlan(
        event_plan_id=f"event_{template_id}_{trigger_point.value}_{intensity.value}",
        template_id=template.template_id,
        name=template.title,
        description=template.description,
        trigger_point=trigger_point,
        advance_notice=False,
        informed_agent_types=[],
        affected_subjects=template.affected_subjects,
        mechanism_channels=template.mechanism_channels,
        branch_scope="both",
        intensity=intensity,
        evidence_refs=template.provenance_refs,
    )


async def prepare(orchestrator: V32Orchestrator, design: ExperimentDesign):
    world = await orchestrator.create_experiment(
        "西部 95%，中部 90%，东部 85%，促进消费与产业布局。"
    )
    await orchestrator.confirm_interpretation(
        world.experiment_id,
        world.interpretation.model_copy(update={"status": "confirmed"}),
    )
    await orchestrator.confirm_design(world.experiment_id, design)
    return await orchestrator.confirm_baseline(world.experiment_id)


def test_policy_text_changes_deterministic_interpretation(tmp_path: Path) -> None:
    orchestrator = service(tmp_path)
    first = orchestrator.interpret_policy("西部 95%，中部 90%，东部 85%。")
    second = orchestrator.interpret_policy("西部 98%，中部 92%，东部 88%，加入油价冲击。")
    assert first.interpretation_id != second.interpretation_id
    assert first.executable_policy.west_central_share == 0.95
    assert second.executable_policy.west_central_share == 0.98
    assert second.event_design_hints


def test_three_experiment_types_enforce_active_difference() -> None:
    base = policy("base", (0.95, 0.90, 0.85))
    changed = policy("changed", (0.98, 0.92, 0.86))
    ExperimentDesign(
        experiment_type=ExperimentType.POLICY_COMPARISON,
        control_policy=base,
        treatment_policy=changed,
    )
    ExperimentDesign(
        experiment_type=ExperimentType.POLICY_STRESS_TEST,
        control_policy=base,
        treatment_policy=changed,
        event_plan=event("both"),
    )
    ExperimentDesign(
        experiment_type=ExperimentType.EVENT_COUNTERFACTUAL,
        control_policy=base,
        treatment_policy=base.model_copy(update={"policy_id": "same-values"}),
        event_plan=event(),
    )
    with pytest.raises(ValidationError):
        ExperimentDesign(
            experiment_type=ExperimentType.EVENT_COUNTERFACTUAL,
            control_policy=base,
            treatment_policy=changed,
            event_plan=event(),
        )


async def test_seven_rounds_have_topk_competition_negotiation_and_traces(
    tmp_path: Path,
) -> None:
    orchestrator = service(tmp_path)
    world = await prepare(
        orchestrator,
        ExperimentDesign(
            experiment_type=ExperimentType.POLICY_COMPARISON,
            control_policy=policy("control", (0.95, 0.90, 0.85)),
            treatment_policy=policy("treatment", (0.98, 0.92, 0.86)),
        ),
    )
    baseline_timeline = await orchestrator.get_presentation_timeline(world.experiment_id)
    baseline_hash = next(
        item.source_hash
        for item in baseline_timeline.frames
        if item.frame_id == "frame-baseline-frozen"
    )
    world = await orchestrator.run(world.experiment_id)
    for branch in world.branches.values():
        assert branch.completed_rounds == list(SimulationRound)
        assert len(branch.province_initial_actions) == 31
        assert len(branch.province_final_actions) == 31
        assert len(branch.automaker_initial_actions) == 10
        assert len(branch.automaker_final_actions) == 10
        assert len(branch.decision_traces) == 123
        assert len(branch.agent_invocations) == 154
        assert {item.kind for item in branch.agent_invocations} == {
            "province_initial",
            "automaker_initial",
            "province_proposal",
            "province_response",
            "automaker_negotiation",
            "province_counter_response",
            "automaker_final",
        }
        assert len(branch.province_proposal_batches) == 31
        assert len(branch.province_response_batches) == 31
        assert (
            sum(
                len(action.province_signals) for action in branch.automaker_initial_actions.values()
            )
            == 310
        )
        revision_traces = [
            trace
            for trace in branch.decision_traces
            if trace.round is SimulationRound.PROVINCE_REVISION
        ]
        assert all(len(trace.peer_signals) == 3 for trace in revision_traces)
        assert all(len(trace.enterprise_signals) == 10 for trace in revision_traces)
        assert all(trace.schema_version == "decision-trace-v4" for trace in revision_traces)
        assert all(trace.decision_reasons for trace in revision_traces)
        assert all(trace.change_conditions for trace in revision_traces)
        assert all(trace.opportunity_costs for trace in revision_traces)
        assert all(delta.trigger_refs for trace in revision_traces for delta in trace.action_delta)
        assert any(item.status == "matched" for item in branch.coordination_records)
        assert any(item.status == "unmatched" for item in branch.coordination_records)
        assert all(
            item.contribution == 0
            for item in branch.coordination_records
            if item.status == "unmatched"
        )
        assert all(
            abs(
                action.subsidy_mix.consumer
                + action.subsidy_mix.fixed_cost
                + action.subsidy_mix.variable_cost
                - 1
            )
            < 1e-6
            for action in branch.province_final_actions.values()
        )
        for action in branch.automaker_final_actions.values():
            envelope = branch.automaker_resource_envelopes[action.automaker_id]
            initial_by_province = {
                item.province_code: item.sales_investment_intensity
                for item in branch.automaker_initial_actions[
                    action.automaker_id
                ].province_market_actions
            }
            assert (
                sum(item.sales_investment_intensity for item in action.province_market_actions)
                <= envelope.national_market_budget + 1e-6
            )
            assert (
                sum(
                    item.channel_strategy.value == "expand"
                    for item in action.province_market_actions
                )
                <= envelope.max_expand_provinces
            )
            assert len(action.facility_actions) <= envelope.max_facility_targets
            assert sum(item.investment_intensity for item in action.facility_actions) <= (
                envelope.facility_budget + 1e-6
            )
            assert action.opportunity_costs
            assert any(
                abs(item.sales_investment_intensity - initial_by_province[item.province_code])
                >= 0.005
                for item in action.province_market_actions
            )
            assert any("来自减少" in item for item in action.opportunity_costs)
            assert len(action.province_market_actions) == 31
            assert 2 <= envelope.max_expand_provinces <= 5
            assert (
                sum(
                    item.channel_strategy.value == "expand"
                    for item in action.province_market_actions
                )
                <= envelope.max_expand_provinces
            )
            assert {item.decision for item in action.province_signals} <= {
                "expand",
                "maintain",
                "reduce",
            }
            offers = [
                item
                for item in branch.province_enterprise_offers
                if item.target_automaker_id == action.automaker_id
            ]
            assert {item.offer_id for item in action.enterprise_offer_responses} == {
                item.offer_id for item in offers
            }
            assert sum(item.decision == "accept" for item in action.enterprise_offer_responses) <= 5
        assert branch.competition_outcomes
        assert all(item.loss_index > 0 for item in branch.competition_outcomes)
        assert all(
            any(
                relation.relation_type == "competition"
                and {relation.source_code, relation.target_code}
                == {item.winner_province_code, item.loser_province_code}
                for relation in orchestrator.relation_network.relations
            )
            for item in branch.competition_outcomes
        )
        assert all(
            utility.weights and abs(sum(utility.weights.values()) - 1) < 1e-6
            for utility in branch.province_utilities.values()
        )
        assert len(branch.province_utilities) == 31
        assert branch.automaker_counter_offers
        assert len(branch.province_counter_offer_responses) == len(branch.automaker_counter_offers)
        assert all(
            item.decision in {"accept", "reject"}
            for item in branch.province_counter_offer_responses
        )
        assert all(
            len(batch.enterprise_offers) <= 2
            and (
                (batch.enterprise_decision == "offer" and batch.enterprise_offers)
                or (batch.enterprise_decision == "no_offer" and batch.enterprise_no_offer_reason)
            )
            for batch in branch.province_proposal_batches.values()
        )
        assert branch.province_enterprise_offer_responses
        assert all(
            item.channel_contribution == item.industry_contribution == 0
            for item in branch.province_enterprise_matches
            if item.status != "matched"
        )
    replay = await orchestrator.get_replay(world.experiment_id)
    frozen = [
        index for index, item in enumerate(replay) if item["type"] == "province_proposals.frozen"
    ]
    responses = [
        index for index, item in enumerate(replay) if item["type"] == "province_responses.completed"
    ]
    assert len(frozen) == len(responses) == 2
    assert max(frozen) < min(responses)
    timeline = await orchestrator.get_presentation_timeline(world.experiment_id)
    assert timeline.schema_version == "presentation-timeline-v2"
    assert timeline.current_frame_id == "frame-comparison-result"
    assert [item.value for item in timeline.available_modes] == ["live", "compare"]
    assert len(timeline.frames) == 10
    assert timeline.event_markers == []
    assert (
        next(
            item.source_hash for item in timeline.frames if item.frame_id == "frame-baseline-frozen"
        )
        == baseline_hash
    )
    replay_ids = {item["event_id"] for item in replay}
    frames = [
        await orchestrator.get_presentation_frame(world.experiment_id, item.frame_id)
        for item in timeline.frames
    ]
    round_frames = [item for item in frames if item.frame_id.startswith("frame-round-")]
    assert all(set(item.branch_projections) == {"control", "treatment"} for item in round_frames)
    assert all(1 <= len(item.spotlights) <= 3 for item in round_frames)
    for item in round_frames:
        actors = [spotlight.focus_subjects[0].subject_id for spotlight in item.spotlights]
        assert len(actors) == len(set(actors))
        assert (
            item.model_dump()
            == (
                await orchestrator.get_presentation_frame(world.experiment_id, item.frame_id)
            ).model_dump()
        )
    province_initial = next(
        item for item in frames if item.frame_id == "frame-round-province_initial"
    )
    automaker_initial = next(
        item for item in frames if item.frame_id == "frame-round-automaker_initial"
    )
    assert all(
        moment.response_status == "pending"
        for moment in province_initial.decision_moments
        if moment.round is SimulationRound.PROVINCE_INITIAL
    )
    assert any(
        moment.actual_responses
        for moment in automaker_initial.decision_moments
        if moment.round is SimulationRound.PROVINCE_INITIAL
    )
    for item in round_frames:
        for moment in item.decision_moments:
            for option in moment.option_evaluations:
                assert option.score == pytest.approx(
                    max(
                        -100,
                        min(100, sum(component.contribution for component in option.components)),
                    )
                )
                parameters = {
                    parameter.parameter: parameter.value for parameter in option.parameters
                }
                if {
                    "consumer_share",
                    "fixed_cost_share",
                    "variable_cost_share",
                } <= parameters.keys():
                    assert parameters["consumer_share"] + parameters[
                        "fixed_cost_share"
                    ] + parameters["variable_cost_share"] == pytest.approx(1)
                    assert parameters["support"] <= parameters["available_budget"] + 1e-6
                if {"market_total", "market_budget"} <= parameters.keys():
                    assert parameters["market_total"] <= parameters["market_budget"] + 1e-6
    assert all(source_id in replay_ids for item in frames for source_id in item.source_event_ids)
    replay_by_id = {item["event_id"]: item for item in replay}
    assert all(
        replay_by_id[source_id]["branch_id"] in {None, projection.branch_id}
        for item in frames
        for projection in item.branch_projections.values()
        for source_id in projection.source_event_ids
    )
    settlement = await orchestrator.get_presentation_frame(
        world.experiment_id, "frame-round-environment_settlement"
    )
    assert set(settlement.branch_projections) == {"control", "treatment"}
    assert all(len(item.province_values) == 31 for item in settlement.branch_projections.values())
    assert all(len(item.metric_summary) == 6 for item in settlement.branch_projections.values())
    revision = await orchestrator.get_presentation_frame(
        world.experiment_id, "frame-round-province_revision"
    )
    assert revision.spotlights and revision.divergences
    assert any(
        item.kind.value == "coordination"
        for projection in revision.branch_projections.values()
        for item in projection.overlay_records
    )
    comparison_frame = await orchestrator.get_presentation_frame(
        world.experiment_id, "frame-comparison-result"
    )
    assert comparison_frame.difference_projection is not None
    assert comparison_frame.difference_projection.map_projection.mode == "difference"
    assert (
        comparison_frame.source_hash
        == (
            await orchestrator.get_presentation_frame(
                world.experiment_id, "frame-comparison-result"
            )
        ).source_hash
    )
    with pytest.raises(KeyError, match="presentation frame not found"):
        await orchestrator.get_presentation_frame(world.experiment_id, "missing-frame")


async def test_agent_can_choose_outside_coordination_prior_with_context(
    tmp_path: Path,
) -> None:
    provider = OutsidePriorProvider()
    legacy = AsyncioSimulationAdapter(FakeLLMProvider(), runtime_dir=tmp_path / "legacy")
    orchestrator = V32Orchestrator(
        legacy,
        runtime_dir=tmp_path / "v32",
        agent_provider=provider,
    )
    world = await prepare(
        orchestrator,
        ExperimentDesign(
            experiment_type=ExperimentType.POLICY_COMPARISON,
            control_policy=policy("control", (0.95, 0.90, 0.85)),
            treatment_policy=policy("treatment", (0.98, 0.92, 0.86)),
        ),
    )
    world = await orchestrator.run(
        world.experiment_id, until_round=SimulationRound.PROVINCE_REVISION
    )
    for branch in world.branches.values():
        proposal = next(
            item
            for item in branch.province_coordination_proposals
            if item.source_province_code == "11"
        )
        prior_targets = {
            item.target_code
            for item in orchestrator.relation_network.relations
            if item.source_code == "11" and item.relation_type == "coordination"
        }
        assert proposal.target_province_code not in prior_targets
        assert proposal.basis_type == "inferred_from_context"
        assert len(proposal.evidence_refs) >= 2
    assert provider.response_payloads
    assert all(
        all(item.branch_id == payload["branch_id"] for item in payload["incoming_proposals"])
        for payload in provider.response_payloads
    )


def test_orchestrator_has_no_positional_or_fixed_pairing_rule() -> None:
    source = Path("simulation/services/v32_orchestrator.py").read_text(encoding="utf-8")
    assert "codes[index" not in source
    assert "MAINLAND_PROVINCE_CODES[index" not in source
    assert "fixed_pairs" not in source


async def test_event_counterfactual_redecides_automakers_and_is_deterministic(
    tmp_path: Path,
) -> None:
    async def run_once(directory: Path):
        orchestrator = service(directory)
        base = policy("base", (0.95, 0.90, 0.85))
        world = await prepare(
            orchestrator,
            ExperimentDesign(
                experiment_type=ExperimentType.EVENT_COUNTERFACTUAL,
                control_policy=base,
                treatment_policy=base.model_copy(update={"policy_id": "same-values"}),
                event_plan=event(),
            ),
        )
        world = await orchestrator.run(world.experiment_id)
        comparison = await orchestrator.get_comparison(world.experiment_id)
        timeline = await orchestrator.get_presentation_timeline(world.experiment_id)
        return world, comparison, timeline

    first_world, first, first_timeline = await run_once(tmp_path / "first")
    _, second, _ = await run_once(tmp_path / "second")
    assert first.same_policy is True
    assert first.same_event is False
    assert first.active_difference == "event"
    assert all(item.changed_province_count > 0 for item in first.automaker_deltas)
    assert any(
        trace.action_delta
        for trace in first_world.branches["treatment"].decision_traces
        if trace.round is SimulationRound.AUTOMAKER_FINAL
    )
    assert first.national_metrics == second.national_metrics
    assert first.delta_gap == second.delta_gap
    assert len(first_timeline.event_markers) == 1
    marker = first_timeline.event_markers[0]
    assert marker.template_id == "intelligent_driving_upgrade"
    assert marker.branch_scope == "treatment_only"
    event_frame_id = f"frame-event-{marker.event_plan_id}"
    assert event_frame_id in {item.frame_id for item in first_timeline.frames}
    event_frame = await service(tmp_path / "first").get_presentation_frame(
        first_world.experiment_id, event_frame_id
    )
    assert all(
        item.value == 0 for item in event_frame.branch_projections["control"].province_values
    )
    assert any(
        item.value > 0 for item in event_frame.branch_projections["treatment"].province_values
    )


@pytest.mark.parametrize(
    ("template_id", "trigger_point", "intensity"),
    [
        (
            "battery_node_upgrade_sichuan",
            EventTriggerPoint.BEFORE_PROVINCE_INITIAL,
            EventIntensityV32.LOW,
        ),
        (
            "intelligent_driving_upgrade",
            EventTriggerPoint.AFTER_PROVINCE_INITIAL,
            EventIntensityV32.MEDIUM,
        ),
        (
            "l3_enterprise_liability_increase",
            EventTriggerPoint.AFTER_AUTOMAKER_INITIAL,
            EventIntensityV32.HIGH,
        ),
        (
            "oil_price_fall",
            EventTriggerPoint.BEFORE_PROVINCE_INITIAL,
            EventIntensityV32.MEDIUM,
        ),
        (
            "oil_price_rise",
            EventTriggerPoint.AFTER_AUTOMAKER_INITIAL,
            EventIntensityV32.HIGH,
        ),
    ],
)
async def test_presentation_event_matrix_completes_with_frozen_trigger_order(
    tmp_path: Path,
    template_id: str,
    trigger_point: EventTriggerPoint,
    intensity: EventIntensityV32,
) -> None:
    orchestrator = service(tmp_path / template_id)
    world = await prepare(
        orchestrator,
        ExperimentDesign(
            experiment_type=ExperimentType.POLICY_STRESS_TEST,
            control_policy=policy("control", (0.95, 0.90, 0.85)),
            treatment_policy=policy("treatment", (0.98, 0.92, 0.86)),
            event_plan=catalog_event(
                template_id,
                trigger_point=trigger_point,
                intensity=intensity,
            ),
        ),
    )
    world = await orchestrator.run(world.experiment_id)
    timeline = await orchestrator.get_presentation_timeline(world.experiment_id)
    assert world.status.value == "completed"
    event_frame_id = f"frame-event-event_{template_id}_{trigger_point.value}_{intensity.value}"
    frame_ids = [item.frame_id for item in timeline.frames]
    event_index = frame_ids.index(event_frame_id)
    boundary_id = {
        EventTriggerPoint.BEFORE_PROVINCE_INITIAL: "frame-baseline-frozen",
        EventTriggerPoint.AFTER_PROVINCE_INITIAL: "frame-round-province_initial",
        EventTriggerPoint.AFTER_AUTOMAKER_INITIAL: "frame-round-automaker_initial",
    }[trigger_point]
    assert event_index == frame_ids.index(boundary_id) + 1
    assert timeline.event_markers[0].intensity is intensity
    event_frame = await orchestrator.get_presentation_frame(world.experiment_id, event_frame_id)
    assert set(event_frame.branch_projections) == {"control", "treatment"}
    treatment = event_frame.branch_projections["treatment"]
    assert len(treatment.province_values) == 31
    exposed_codes = {item.province_code for item in treatment.province_values if item.value > 0}
    assert exposed_codes == (
        {"51"}
        if template_id == "battery_node_upgrade_sichuan"
        else set(item.province_code for item in treatment.province_values)
    )
    assert treatment.key_changes[0].title == "事件情景已冻结"


async def test_presentation_event_stream_resumes_strictly_after_last_event_id(
    tmp_path: Path,
) -> None:
    orchestrator = service(tmp_path)
    world = await prepare(
        orchestrator,
        ExperimentDesign(
            experiment_type=ExperimentType.POLICY_COMPARISON,
            control_policy=policy("control", (0.95, 0.90, 0.85)),
            treatment_policy=policy("treatment", (0.98, 0.92, 0.86)),
        ),
    )
    before = await orchestrator.get_events(world.experiment_id)
    cursor = before[-1].event_id
    await orchestrator.run(world.experiment_id, until_round=SimulationRound.PROVINCE_INITIAL)
    resumed = await orchestrator.wait_for_events(world.experiment_id, cursor, timeout_seconds=0.01)
    assert resumed
    assert cursor not in {item.event_id for item in resumed}
    assert len({item.event_id for item in resumed}) == len(resumed)
    assert any(item.type == "round.completed" for item in resumed)
    assert (
        await orchestrator.wait_for_events(
            world.experiment_id, resumed[-1].event_id, timeout_seconds=0.01
        )
        == []
    )


async def test_runtime_restores_partial_and_completed_experiment_after_restart(
    tmp_path: Path,
) -> None:
    first = service(tmp_path)
    design = ExperimentDesign(
        experiment_type=ExperimentType.POLICY_COMPARISON,
        control_policy=policy("control", (0.95, 0.90, 0.85)),
        treatment_policy=policy("treatment", (0.98, 0.92, 0.86)),
    )
    world = await prepare(
        first,
        design,
    )
    assert await first.confirm_interpretation(world.experiment_id, world.interpretation) == world
    assert await first.confirm_design(world.experiment_id, design) == world
    assert await first.confirm_baseline(world.experiment_id) == world
    world = await first.run(
        world.experiment_id,
        until_round=SimulationRound.PROVINCE_INITIAL,
    )
    experiment_id = world.experiment_id
    before_events = await first.get_events(experiment_id)
    before_timeline = await first.get_presentation_timeline(experiment_id)
    snapshot_path = tmp_path / "v32" / experiment_id / "runtime-snapshot.json"
    replay_path = tmp_path / "v32" / experiment_id / "replay.jsonl"
    assert snapshot_path.is_file()
    replay_inode = replay_path.stat().st_ino
    replay_prefix = replay_path.read_bytes()

    second = service(tmp_path)
    assert second.has_experiment(experiment_id)
    restored = await second.get_state(experiment_id)
    assert restored == world
    assert await second.get_events(experiment_id) == before_events
    assert (
        await second.get_presentation_timeline(experiment_id)
    ).source_world_hash == before_timeline.source_world_hash

    completed = await second.run(experiment_id)
    after_events = await second.get_events(experiment_id)
    assert replay_path.stat().st_ino == replay_inode
    assert replay_path.read_bytes().startswith(replay_prefix)
    next_counter = int(after_events[len(before_events)].event_id.rsplit("_", 1)[1])
    assert next_counter == len(before_events) + 1
    comparison = await second.get_comparison(experiment_id)

    third = service(tmp_path)
    assert third.has_experiment(experiment_id)
    assert await third.get_state(experiment_id) == completed
    assert await third.get_comparison(experiment_id) == comparison
    assert await third.get_events(experiment_id) == after_events


async def test_runtime_restore_rejects_truncated_snapshot(tmp_path: Path) -> None:
    first = service(tmp_path)
    world = await first.create_experiment("西部 95%，中部 90%，东部 85%。")
    snapshot_path = tmp_path / "v32" / world.experiment_id / "runtime-snapshot.json"
    snapshot_path.write_text('{"schema_version":', encoding="utf-8")

    restarted = service(tmp_path)
    with pytest.raises(ValueError, match="RUNTIME_SNAPSHOT_JSON_INVALID"):
        restarted.has_experiment(world.experiment_id)


async def test_completed_experiment_cache_restores_same_five_round_result(tmp_path: Path) -> None:
    design = ExperimentDesign(
        experiment_type=ExperimentType.POLICY_COMPARISON,
        control_policy=policy("control", (0.95, 0.90, 0.85)),
        treatment_policy=policy("treatment", (0.98, 0.92, 0.86)),
    )
    source = cached_service(tmp_path, cache_enabled=False)
    source_world = await prepare(source, design)
    source_world = await source.run(source_world.experiment_id)
    source.export_cache(source_world.experiment_id)

    restored = cached_service(tmp_path, cache_enabled=True)
    restored_world = await prepare(restored, design)
    restored_world = await restored.run(restored_world.experiment_id)
    replay = await restored.get_replay(restored_world.experiment_id)
    assert restored_world.status.value == "completed"
    assert any(item["type"] == "cache.hit" for item in replay)
    assert (
        restored_world.branches["control"].national_metrics
        == source_world.branches["control"].national_metrics
    )
