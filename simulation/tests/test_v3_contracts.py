import pytest
from pydantic import ValidationError

from simulation.data import load_automaker_profiles, load_profiles
from simulation.llm.fake_provider import FakeLLMProvider
from simulation.models.common import Phase, PolicyInputMode
from simulation.models.policy import PolicySchema, RegionalShareAdjustments
from simulation.models.province import SubsidyMix


def test_phase_contract_is_annual_and_ordered():
    assert [item.value for item in Phase] == [
        "SETUP",
        "Y1_Q1",
        "Y1_Q2",
        "Y1_Q3",
        "Y1_Q4",
        "YEAR1_REVIEW",
        "Y2_Q1",
        "Y2_Q2",
        "Y2_Q3",
        "Y2_Q4",
        "COMPLETE",
    ]
    assert Phase.Y1_Q4.year == 1 and Phase.Y2_Q2.year == 2 and Phase.COMPLETE.year is None


def test_policy_defaults_are_independent_regional_shares():
    policy = PolicySchema()
    assert (policy.west_central_share, policy.central_central_share, policy.east_central_share) == (
        0.95,
        0.90,
        0.85,
    )
    assert (
        sum((policy.west_central_share, policy.central_central_share, policy.east_central_share))
        > 1
    )


def test_policy_ordering_warns_but_does_not_reject():
    policy = PolicySchema(
        west_central_share=0.80, central_central_share=0.95, east_central_share=0.85
    )
    assert policy.ordering_warnings


def test_delta_input_must_match_reference_plus_adjustment():
    policy = PolicySchema(
        input_mode=PolicyInputMode.DELTA,
        west_central_share=0.97,
        central_central_share=0.91,
        east_central_share=0.84,
        share_adjustments=RegionalShareAdjustments(west=0.02, central=0.01, east=-0.01),
    )
    assert policy.west_central_share == 0.97
    with pytest.raises(ValidationError):
        PolicySchema(
            input_mode="delta",
            west_central_share=0.96,
            share_adjustments=RegionalShareAdjustments(west=0.02),
        )


def test_subsidy_mix_must_sum_to_one():
    assert SubsidyMix(consumer=0.5, fixed_cost=0.3, variable_cost=0.2).consumer == 0.5
    with pytest.raises(ValidationError):
        SubsidyMix(consumer=0.5, fixed_cost=0.3, variable_cost=0.3)


@pytest.mark.asyncio
async def test_automaker_action_has_31_allocations_and_at_most_three_facilities():
    provider = FakeLLMProvider()
    profiles = load_profiles()
    automakers = load_automaker_profiles()
    from simulation.data import load_network, load_province_personas
    from simulation.envs import ChinaPolicyEnv

    env = ChinaPolicyEnv(profiles=profiles, automaker_profiles=automakers)
    personas = load_province_personas()
    network = load_network()
    policy = PolicySchema()
    province_actions = {
        code: await provider.generate_province_action(
            profile=profile,
            persona=personas[code],
            state=env.province_states[code],
            policy=policy,
            phase=Phase.Y1_Q1,
            related=network[code],
            neighbor_actions={},
            previous_action=None,
            feedback=None,
            seed=1,
            prompt_version="v1",
            model_version="fake",
        )
        for code, profile in profiles.items()
    }
    action = await provider.generate_automaker_action(
        profile=automakers["byd"],
        state=env.automaker_states["byd"],
        province_profiles=profiles,
        province_actions=province_actions,
        policy=policy,
        phase=Phase.Y1_Q2,
        previous_action=None,
        seed=1,
        prompt_version="v1",
        model_version="fake",
    )
    assert len(action.province_market_actions) == 31
    assert len(action.facility_actions) <= 3
