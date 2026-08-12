import asyncio

import pytest

from simulation.adapters.asyncio_adapter import AsyncioSimulationAdapter
from simulation.llm.fake_provider import FakeLLMProvider
from simulation.models.common import Phase
from simulation.models.experiment import ExperimentConfig


@pytest.mark.asyncio
async def test_full_same_source_ab_and_call_outputs(tmp_path):
    adapter = AsyncioSimulationAdapter(FakeLLMProvider(), runtime_dir=tmp_path)
    result = await adapter.run_full_demo(ExperimentConfig(objective="验证V3同源A/B"))
    runtime = adapter.runtimes[result.experiment_id]
    treatment = runtime.worlds[result.treatment_branch_id]
    assert result.schema_version == "comparison-v4"
    assert runtime.worlds["control"].parent_checkpoint_id == treatment.parent_checkpoint_id
    assert runtime.worlds["control"].seed == treatment.seed
    assert [item.path for item in result.policy_diff] == [
        "west_central_share",
        "central_central_share",
    ]
    assert len(result.province_deltas) == 31 and len(result.automaker_strategy_transitions) == 10


@pytest.mark.asyncio
async def test_approval_gates_block_unauthorized_run(tmp_path):
    adapter = AsyncioSimulationAdapter(FakeLLMProvider(), runtime_dir=tmp_path)
    world = await adapter.initialize(ExperimentConfig(objective="审批门禁"))
    with pytest.raises(PermissionError):
        await adapter.run_phase(world.experiment_id, Phase.Y1_Q1)


@pytest.mark.asyncio
async def test_reject_intervention_runs_single_branch_without_comparison(tmp_path):
    adapter = AsyncioSimulationAdapter(FakeLLMProvider(), runtime_dir=tmp_path)
    world = await adapter.initialize(ExperimentConfig(objective="拒绝干预"))
    await adapter.approve_directive(world.experiment_id)
    review = await adapter.run_to_phase(world.experiment_id, Phase.YEAR1_REVIEW)
    await adapter.reject_intervention(
        world.experiment_id, review.intervention_proposals[0].proposal_id
    )
    final = await adapter.run_to_phase(world.experiment_id, Phase.COMPLETE)
    assert (
        final.phase is Phase.COMPLETE and final.central_review.review_mode.value == "single_branch"
    )
    with pytest.raises(ValueError, match="COMPARISON_NOT_AVAILABLE"):
        await adapter.get_comparison(world.experiment_id)


@pytest.mark.asyncio
async def test_replay_audit_and_evidence_are_separate(tmp_path):
    adapter = AsyncioSimulationAdapter(FakeLLMProvider(), runtime_dir=tmp_path)
    result = await adapter.run_full_demo(ExperimentConfig(objective="追溯职责"))
    events = await adapter.get_replay(result.experiment_id)
    audit = await adapter.get_audit(result.experiment_id)
    assert events and audit.records
    assert adapter.replay.verify_audit_chain(result.experiment_id)
    evidence = await adapter.get_evidence(result.experiment_id, "mechanism:41")
    assert evidence["method_version"] == "nev-policy-env-v1"


@pytest.mark.asyncio
async def test_branch_runs_can_be_requested_concurrently(tmp_path):
    adapter = AsyncioSimulationAdapter(FakeLLMProvider(), runtime_dir=tmp_path)
    world = await adapter.initialize(ExperimentConfig(objective="并发双分支"))
    await adapter.approve_directive(world.experiment_id)
    review = await adapter.run_to_phase(world.experiment_id, Phase.YEAR1_REVIEW)
    approved = await adapter.approve_intervention(
        world.experiment_id, review.intervention_proposals[0].proposal_id
    )
    branch = await adapter.create_approved_branch(world.experiment_id, approved.intervention_id)
    branches = await adapter.list_branches(world.experiment_id)
    restored_control = await adapter.get_state(world.experiment_id)
    assert {item.kind.value for item in branches} == {"control", "treatment"}
    assert restored_control.intervention_decision == "approved"
    assert restored_control.approved_intervention.intervention_id == approved.intervention_id
    control, treatment = await asyncio.gather(
        adapter.run_to_phase(world.experiment_id, Phase.Y2_Q4, "control"),
        adapter.run_to_phase(world.experiment_id, Phase.Y2_Q4, branch.branch_id),
    )
    assert control.phase is treatment.phase is Phase.Y2_Q4


@pytest.mark.asyncio
async def test_treatment_branch_ids_are_unique_across_experiments(tmp_path):
    adapter = AsyncioSimulationAdapter(FakeLLMProvider(), runtime_dir=tmp_path)
    branch_ids = []
    experiment_ids = []
    for index in range(2):
        world = await adapter.initialize(ExperimentConfig(objective=f"多实验分支隔离 {index}"))
        experiment_ids.append(world.experiment_id)
        await adapter.approve_directive(world.experiment_id)
        review = await adapter.run_to_phase(world.experiment_id, Phase.YEAR1_REVIEW)
        approved = await adapter.approve_intervention(
            world.experiment_id, review.intervention_proposals[0].proposal_id
        )
        branch = await adapter.create_approved_branch(world.experiment_id, approved.intervention_id)
        branch_ids.append(branch.branch_id)

    assert len(set(branch_ids)) == 2
    for expected_experiment_id, branch_id in zip(experiment_ids, branch_ids, strict=True):
        found_experiment_id, _ = await adapter.find_branch(branch_id)
        assert found_experiment_id == expected_experiment_id
