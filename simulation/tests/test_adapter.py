import asyncio

import pytest

from simulation.adapters.asyncio_adapter import AsyncioSimulationAdapter
from simulation.llm.fake_provider import FakeLLMProvider
from simulation.models.common import Phase, ReviewMode
from simulation.models.experiment import ExperimentConfig


class FailingProposalProvider(FakeLLMProvider):
    async def generate_intervention_proposals(self, **_kwargs):
        raise RuntimeError("proposal generation failed")


class SlowEnterpriseProvider(FakeLLMProvider):
    async def generate_enterprise_actions_batch(self, **kwargs):
        if kwargs["province_profile"].province_code == "44":
            await asyncio.sleep(0.02)
        return await super().generate_enterprise_actions_batch(**kwargs)


class InvalidReviewEvidenceProvider(FakeLLMProvider):
    async def generate_central_review(self, result):
        review = await super().generate_central_review(result)
        review.findings[0].evidence_refs = [
            "national_metrics.sme_financing_accessibility_index",
            "policy_diff",
        ]
        return review


class CountingProvider(FakeLLMProvider):
    def __init__(self):
        self.central = 0
        self.province = 0
        self.enterprise = 0

    async def generate_central_directive(self, *args, **kwargs):
        self.central += 1
        return await super().generate_central_directive(*args, **kwargs)

    async def generate_province_action(self, **kwargs):
        self.province += 1
        return await super().generate_province_action(**kwargs)

    async def generate_province_feedback(self, **kwargs):
        self.province += 1
        return await super().generate_province_feedback(**kwargs)

    async def generate_enterprise_actions_batch(self, **kwargs):
        self.enterprise += 1
        return await super().generate_enterprise_actions_batch(**kwargs)

    async def generate_intervention_proposals(self, **kwargs):
        self.central += 1
        return await super().generate_intervention_proposals(**kwargs)

    async def generate_central_review(self, result):
        self.central += 1
        return await super().generate_central_review(result)


@pytest.mark.asyncio
async def test_directive_approval_is_required(tmp_path) -> None:
    adapter = AsyncioSimulationAdapter(FakeLLMProvider(), runtime_dir=tmp_path)
    world = await adapter.initialize(ExperimentConfig(objective="测试中央政策目标"))
    with pytest.raises(PermissionError):
        await adapter.run_phase(world.experiment_id, Phase.T1)


@pytest.mark.asyncio
async def test_full_demo_has_v21_province_lineage_and_isolated_branches(tmp_path) -> None:
    adapter = AsyncioSimulationAdapter(FakeLLMProvider(), runtime_dir=tmp_path)
    comparison = await adapter.run_full_demo(
        ExperimentConfig(objective="推动制造业设备更新并改善中小企业融资")
    )
    assert comparison.schema_version == "comparison-v3"
    assert len(comparison.province_strategy_transitions) == 31
    assert len(comparison.province_deltas) == 31
    assert sum(item.count for item in comparison.action_migrations) == 186
    assert len(comparison.enterprise_group_changes) == 6
    assert comparison.control_branch_id == "control"
    assert comparison.treatment_branch_id.startswith("treatment_")
    assert {item.path for item in comparison.policy_diff} == {
        "instrument_mix.direct_subsidy",
        "instrument_mix.interest_subsidy",
        "instrument_mix.financing_guarantee",
        "sme_preference",
        "regional_support_bias",
    }
    assert comparison.central_review is not None
    assert comparison.central_review.review_mode == ReviewMode.COMPARISON
    control = await adapter.get_state(comparison.experiment_id, comparison.control_branch_id)
    treatment = await adapter.get_state(comparison.experiment_id, comparison.treatment_branch_id)
    assert control.parent_checkpoint_id == treatment.parent_checkpoint_id
    assert control.policy.regional_support_bias == 0
    assert treatment.policy.regional_support_bias > 0
    assert control.phase == treatment.phase == Phase.T5
    assert len(control.enterprise_states) == len(treatment.enterprise_states) == 186
    assert control.province_personas == treatment.province_personas
    assert all(len(items) == 2 for items in control.province_action_lineage.values())
    assert all(len(items) == 2 for items in treatment.province_action_lineage.values())
    assert all(
        item[-1].previous_action_id == item[0].action_id
        for item in treatment.province_action_lineage.values()
    )
    assert comparison.national_metrics["sme_financing_accessibility_index"].delta > 0
    assert comparison.national_metrics["local_fiscal_pressure_index"].delta > 0


@pytest.mark.asyncio
async def test_reject_intervention_runs_control_only_and_disables_comparison(tmp_path) -> None:
    adapter = AsyncioSimulationAdapter(FakeLLMProvider(), runtime_dir=tmp_path)
    world = await adapter.initialize(ExperimentConfig(objective="测试拒绝干预"))
    await adapter.approve_directive(world.experiment_id, world.policy)
    t3 = await adapter.run_to_phase(world.experiment_id, Phase.T3)
    rejected = await adapter.reject_intervention(
        world.experiment_id, t3.intervention_proposals[0].proposal_id
    )
    assert rejected.intervention_decision == "rejected"
    final = await adapter.run_to_phase(world.experiment_id, Phase.T5)
    assert final.central_review is not None
    assert final.central_review.review_mode == ReviewMode.SINGLE_BRANCH
    assert len(adapter._runtime(world.experiment_id).branches) == 1
    with pytest.raises(ValueError, match="COMPARISON_NOT_AVAILABLE"):
        await adapter.get_comparison(world.experiment_id)


@pytest.mark.asyncio
async def test_call_budget_is_3_central_124_province_and_93_enterprise(tmp_path) -> None:
    provider = CountingProvider()
    adapter = AsyncioSimulationAdapter(provider, runtime_dir=tmp_path)
    await adapter.run_full_demo(ExperimentConfig(objective="测试完整调用预算"))
    assert provider.central == 3
    assert provider.province == 124
    assert provider.enterprise == 93


@pytest.mark.asyncio
async def test_t3_feedback_does_not_change_policy_or_t1_action_lineage(tmp_path) -> None:
    adapter = AsyncioSimulationAdapter(FakeLLMProvider(), runtime_dir=tmp_path)
    world = await adapter.initialize(ExperimentConfig(objective="测试T3非变更意向"))
    await adapter.approve_directive(world.experiment_id, world.policy)
    t2 = await adapter.run_to_phase(world.experiment_id, Phase.T2)
    policy_before = t2.policy.model_copy(deep=True)
    actions_before = t2.province_actions.copy()
    lineage_before = t2.province_action_lineage.copy()
    t3 = await adapter.run_phase(world.experiment_id, Phase.T3)
    assert t3.policy == policy_before
    assert t3.province_actions == actions_before
    assert t3.province_action_lineage == lineage_before
    assert all(len(item.adjustment_intents) <= 3 for item in t3.province_feedback.values())


@pytest.mark.asyncio
async def test_repeated_comparison_does_not_repeat_review_or_events(tmp_path) -> None:
    provider = CountingProvider()
    adapter = AsyncioSimulationAdapter(provider, runtime_dir=tmp_path)
    first = await adapter.run_full_demo(ExperimentConfig(objective="测试Comparison幂等读取"))
    events_before = await adapter.get_events(first.experiment_id)
    central_before = provider.central
    second = await adapter.get_comparison(first.experiment_id)
    events_after = await adapter.get_events(first.experiment_id)
    assert second == first
    assert provider.central == central_before == 3
    assert events_after == events_before


@pytest.mark.asyncio
async def test_invalid_review_evidence_falls_back_and_is_audited(tmp_path) -> None:
    adapter = AsyncioSimulationAdapter(InvalidReviewEvidenceProvider(), runtime_dir=tmp_path)
    comparison = await adapter.run_full_demo(ExperimentConfig(objective="验证复盘证据降级"))

    assert comparison.central_review is not None
    assert all(
        ref.startswith("comparison:")
        for finding in comparison.central_review.findings
        for ref in finding.evidence_refs
    )
    records = (
        await adapter.get_audit(
            comparison.experiment_id,
            actor_kind="central_agent",
            actor_id="central",
            outcome="fallback",
            limit=20,
        )
    ).records
    review_record = next(
        item for item in records if item.payload.operation == "review_comparison"
    )
    assert review_record.payload.fallback_reason
    assert review_record.payload.attempts[-1].error_code == (
        "central_review_evidence_validation_failed"
    )
    assert review_record.payload.attempts[-1].invalid_response_hash
    assert "national_metrics.sme_financing_accessibility_index" not in (
        str(review_record.payload.output_snapshot)
    )


@pytest.mark.asyncio
async def test_replay_cursor_returns_only_new_events(tmp_path) -> None:
    adapter = AsyncioSimulationAdapter(FakeLLMProvider(), runtime_dir=tmp_path)
    world = await adapter.initialize(ExperimentConfig(objective="测试Replay游标"))
    events = await adapter.get_events(world.experiment_id)
    assert len(events) == 33
    assert sum(item.type == "province.persona.ready" for item in events) == 31
    await adapter.approve_directive(world.experiment_id, world.policy)
    new_events = await adapter.get_events(world.experiment_id, events[-1].event_id)
    assert [event.type for event in new_events] == ["central.directive.approved"]


@pytest.mark.asyncio
async def test_event_wait_times_out_without_duplicate_events(tmp_path) -> None:
    adapter = AsyncioSimulationAdapter(FakeLLMProvider(), runtime_dir=tmp_path)
    world = await adapter.initialize(ExperimentConfig(objective="测试事件流断线恢复"))
    events = await adapter.get_events(world.experiment_id)
    after_last = await adapter.wait_for_events(
        world.experiment_id, events[-1].event_id, timeout_seconds=0.001
    )
    assert after_last == []


@pytest.mark.asyncio
async def test_failed_phase_does_not_partially_commit_world_state(tmp_path) -> None:
    adapter = AsyncioSimulationAdapter(FailingProposalProvider(), runtime_dir=tmp_path)
    world = await adapter.initialize(ExperimentConfig(objective="测试阶段原子提交"))
    await adapter.approve_directive(world.experiment_id, world.policy)
    before = await adapter.run_to_phase(world.experiment_id, Phase.T2)
    with pytest.raises(RuntimeError, match="proposal generation failed"):
        await adapter.run_phase(world.experiment_id, Phase.T3)
    assert await adapter.get_state(world.experiment_id) == before


@pytest.mark.asyncio
async def test_enterprise_timeout_falls_back_for_whole_province(tmp_path) -> None:
    adapter = AsyncioSimulationAdapter(
        SlowEnterpriseProvider(), runtime_dir=tmp_path, agent_timeout_seconds=0.001
    )
    world = await adapter.initialize(ExperimentConfig(objective="测试企业批量超时降级"))
    await adapter.approve_directive(world.experiment_id, world.policy)
    t2 = await adapter.run_to_phase(world.experiment_id, Phase.T2)
    assert len(t2.enterprise_actions) == 186
    assert "44" in t2.fallback_provinces
    events = await adapter.get_events(world.experiment_id)
    fallback = [event for event in events if event.type == "enterprise.batch.fallback"]
    assert any(event.payload["province_code"] == "44" for event in fallback)
