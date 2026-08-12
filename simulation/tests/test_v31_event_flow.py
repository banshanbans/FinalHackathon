import asyncio

import pytest
from pydantic import ValidationError

from simulation.adapters.asyncio_adapter import AsyncioSimulationAdapter
from simulation.catalog import event_scenario_catalog
from simulation.data import load_interaction_network, load_profiles
from simulation.llm.fake_provider import FakeLLMProvider
from simulation.models.common import (
    ComparisonMode,
    EventIntensity,
    EventTemplateId,
    Phase,
)
from simulation.models.experiment import ExperimentConfig
from simulation.models.scenario import EventScenario, EventScenarioSelection, SubsidyMixDelta


async def _event_counterfactual(tmp_path, template_id: EventTemplateId):
    adapter = AsyncioSimulationAdapter(FakeLLMProvider(), runtime_dir=tmp_path)
    world = await adapter.initialize(
        ExperimentConfig(
            objective=f"事件反事实 {template_id.value}",
            comparison_mode=ComparisonMode.EVENT_COUNTERFACTUAL,
        )
    )
    await adapter.approve_directive(world.experiment_id)
    await adapter.run_to_phase(world.experiment_id, Phase.YEAR1_REVIEW)
    branch = await adapter.create_event_counterfactual_branches(world.experiment_id)
    await asyncio.gather(
        adapter.run_to_phase(world.experiment_id, Phase.Y2_Q2, "control"),
        adapter.run_to_phase(world.experiment_id, Phase.Y2_Q2, branch.branch_id),
    )
    scenario = await adapter.approve_event_scenario(
        world.experiment_id,
        EventScenarioSelection(template_id=template_id, intensity=EventIntensity.MEDIUM),
    )
    await asyncio.gather(
        adapter.run_to_phase(world.experiment_id, Phase.Y2_Q4, "control"),
        adapter.run_to_phase(world.experiment_id, Phase.Y2_Q4, branch.branch_id),
    )
    return adapter, scenario, await adapter.compare(world.experiment_id)


def test_event_catalog_profiles_and_interaction_network_are_frozen():
    templates = event_scenario_catalog()
    assert set(templates) == set(EventTemplateId)
    assert all(template.mechanism_channels for template in templates.values())
    profiles = load_profiles()
    assert len(profiles) == 31
    for profile in profiles.values():
        for field in (
            "intelligent_driving_readiness_index",
            "regulatory_execution_capacity_index",
            "oil_price_sensitivity_index",
            "supply_chain_complementarity_index",
        ):
            assert 0 <= getattr(profile, field) <= 1
            assert field in profile.provenance
    network = load_interaction_network()
    assert network.schema_version == "province-interaction-network-v1"
    assert {edge.source_province_code for edge in network.edges} == set(profiles)
    assert any(edge.coordinate_eligible for edge in network.edges)
    assert any(not edge.coordinate_eligible for edge in network.edges)


def test_event_parameters_and_subsidy_conservation_are_strict():
    with pytest.raises(ValidationError, match="magnitude"):
        EventScenario(
            scenario_id="invalid",
            template_id=EventTemplateId.OIL_PRICE_RISE,
            family="energy",
            title="invalid",
            intensity=EventIntensity.LOW,
            magnitude=0.75,
            provenance_refs=["scenario:test"],
        )
    with pytest.raises(ValidationError, match="sum to 0"):
        SubsidyMixDelta(consumer=0.1, fixed_cost=0, variable_cost=0)


@pytest.mark.asyncio
async def test_event_counterfactual_has_31_by_31_only_in_treatment(tmp_path):
    adapter, scenario, result = await _event_counterfactual(
        tmp_path, EventTemplateId.L3_ENTERPRISE_LIABILITY_INCREASE
    )
    control = await adapter.get_state(result.experiment_id, result.control_branch_id)
    treatment = await adapter.get_state(result.experiment_id, result.treatment_branch_id)
    assert not control.event_applied and treatment.event_applied
    assert len(control.province_event_signals) == len(control.province_event_responses) == 0
    assert len(treatment.province_event_signals) == len(treatment.province_event_responses) == 31
    assert result.active_difference_proof.same_policy
    assert result.active_difference_proof.active_difference == "event"
    assert result.policy_diff == [] and result.event_diff.changed
    assert scenario.scenario_id == treatment.approved_event_scenario.scenario_id
    eligible = adapter.coordination_eligible_pairs
    for match in treatment.coordination_matches:
        pair = (match.left_province_code, match.right_province_code)
        if match.status.value == "matched":
            assert pair in eligible and match.contribution > 0
        else:
            assert match.contribution == 0
    with pytest.raises(ValueError, match="already approved"):
        await adapter.approve_event_scenario(
            result.experiment_id,
            EventScenarioSelection(
                template_id=EventTemplateId.OIL_PRICE_FALL,
                intensity=EventIntensity.HIGH,
            ),
        )


@pytest.mark.asyncio
async def test_oil_price_scenarios_have_opposite_demand_direction(tmp_path):
    _, _, rise = await _event_counterfactual(tmp_path / "rise", EventTemplateId.OIL_PRICE_RISE)
    _, _, fall = await _event_counterfactual(tmp_path / "fall", EventTemplateId.OIL_PRICE_FALL)
    assert rise.national_metrics["nev_demand"].delta > 0
    assert fall.national_metrics["nev_demand"].delta < 0
