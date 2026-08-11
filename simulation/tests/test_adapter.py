import asyncio

import pytest

from simulation.adapters.asyncio_adapter import AsyncioSimulationAdapter
from simulation.llm.fake_provider import FakeLLMProvider
from simulation.models.common import Phase
from simulation.models.experiment import ExperimentConfig


class FailingProposalProvider(FakeLLMProvider):
    async def generate_intervention_proposals(self, **_kwargs):
        raise RuntimeError("proposal generation failed")


class SlowProvinceProvider(FakeLLMProvider):
    async def generate_province_action(self, **kwargs):
        if kwargs["profile"].province_code == "44":
            await asyncio.sleep(0.02)
        return await super().generate_province_action(**kwargs)


@pytest.mark.asyncio
async def test_directive_approval_is_required(tmp_path) -> None:
    adapter = AsyncioSimulationAdapter(FakeLLMProvider(), runtime_dir=tmp_path)
    world = await adapter.initialize(ExperimentConfig(objective="测试中央政策目标"))
    with pytest.raises(PermissionError):
        await adapter.run_phase(world.experiment_id, Phase.T1)


@pytest.mark.asyncio
async def test_full_demo_has_isolated_branches_and_review(tmp_path) -> None:
    adapter = AsyncioSimulationAdapter(FakeLLMProvider(), runtime_dir=tmp_path)
    comparison = await adapter.run_full_demo(ExperimentConfig(objective="促进创新并兼顾区域均衡"))
    assert len(comparison.province_deltas) == 31
    assert comparison.control_branch_id == "control"
    assert comparison.treatment_branch_id.startswith("treatment_")
    assert set(comparison.policy_diff) == {"regional_bias", "cooperation_incentive"}
    assert comparison.central_review is not None
    control = await adapter.get_state(comparison.experiment_id, comparison.control_branch_id)
    treatment = await adapter.get_state(comparison.experiment_id, comparison.treatment_branch_id)
    assert control.parent_checkpoint_id == treatment.parent_checkpoint_id
    assert control.policy.regional_bias == 0
    assert treatment.policy.regional_bias > 0
    assert control.phase == treatment.phase == Phase.T5
    assert comparison.national_metrics["policy_accessibility"].delta > 0
    assert comparison.national_metrics["regional_gap"].delta < 0
    assert comparison.national_metrics["fiscal_pressure"].delta > 0


@pytest.mark.asyncio
async def test_replay_cursor_returns_only_new_events(tmp_path) -> None:
    adapter = AsyncioSimulationAdapter(FakeLLMProvider(), runtime_dir=tmp_path)
    world = await adapter.initialize(ExperimentConfig(objective="测试Replay游标"))
    events = await adapter.get_events(world.experiment_id)
    assert len(events) == 2
    await adapter.approve_directive(world.experiment_id)
    new_events = await adapter.get_events(world.experiment_id, events[-1].event_id)
    assert [event.type for event in new_events] == ["central.directive.approved"]


@pytest.mark.asyncio
async def test_event_wait_times_out_without_duplicate_events(tmp_path) -> None:
    adapter = AsyncioSimulationAdapter(FakeLLMProvider(), runtime_dir=tmp_path)
    world = await adapter.initialize(ExperimentConfig(objective="测试事件流断线恢复"))
    events = await adapter.get_events(world.experiment_id)
    after_last = await adapter.wait_for_events(
        world.experiment_id,
        events[-1].event_id,
        timeout_seconds=0.001,
    )
    assert after_last == []


@pytest.mark.asyncio
async def test_failed_phase_does_not_partially_commit_world_state(tmp_path) -> None:
    adapter = AsyncioSimulationAdapter(FailingProposalProvider(), runtime_dir=tmp_path)
    world = await adapter.initialize(ExperimentConfig(objective="测试阶段原子提交"))
    await adapter.approve_directive(world.experiment_id)
    before = await adapter.run_to_phase(world.experiment_id, Phase.T2)

    with pytest.raises(RuntimeError, match="proposal generation failed"):
        await adapter.run_phase(world.experiment_id, Phase.T3)

    after = await adapter.get_state(world.experiment_id)
    assert after == before


@pytest.mark.asyncio
async def test_single_agent_timeout_uses_explicit_fallback(tmp_path) -> None:
    adapter = AsyncioSimulationAdapter(
        SlowProvinceProvider(),
        runtime_dir=tmp_path,
        agent_timeout_seconds=0.001,
    )
    world = await adapter.initialize(ExperimentConfig(objective="测试单省超时降级"))
    await adapter.approve_directive(world.experiment_id)
    t1 = await adapter.run_phase(world.experiment_id, Phase.T1)

    assert len(t1.actions) == 31
    assert t1.actions["44"].fallback_used is True
    assert t1.actions["44"].run_mode == "fallback"
