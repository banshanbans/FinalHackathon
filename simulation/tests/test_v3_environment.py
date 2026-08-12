import pytest

from simulation.data import (
    load_automaker_profiles,
    load_network,
    load_profiles,
    load_province_personas,
)
from simulation.envs import (
    ChinaPolicyEnv,
    delta_gap,
    fixed_variable_cost_threshold,
    normalized_gini,
    normalized_hhi,
    province_development_index,
)
from simulation.llm.fake_provider import FakeLLMProvider
from simulation.models.common import Phase
from simulation.models.policy import PolicySchema


def test_gap_and_hhi_are_normalized():
    assert normalized_gini([10] * 31) == 0
    assert normalized_hhi([10] * 31) == 0
    assert 0 <= normalized_gini([0] * 30 + [100]) <= 100
    assert 0 <= normalized_hhi([0] * 30 + [100]) <= 100


def test_development_and_delta_gap_contract():
    assert province_development_index(60, 40) == 50
    assert delta_gap(9, 11) == -2


def test_fixed_variable_threshold_is_versioned_and_bounded():
    result = fixed_variable_cost_threshold("41", 0.2, 0.4)
    assert result.crossing_quarter in {1, 2, 3, 4, None}
    assert len(result.variable_support_effects) == 4


@pytest.mark.asyncio
async def test_settlement_is_deterministic_and_complete():
    profiles = load_profiles()
    automakers = load_automaker_profiles()
    personas = load_province_personas()
    network = load_network()
    provider = FakeLLMProvider()
    policy = PolicySchema()
    env = ChinaPolicyEnv(profiles=profiles, automaker_profiles=automakers, policy=policy)
    province_actions = {
        code: await provider.generate_province_action(
            profile=profiles[code],
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
        for code in profiles
    }
    automaker_actions = {
        key: await provider.generate_automaker_action(
            profile=automakers[key],
            state=env.automaker_states[key],
            province_profiles=profiles,
            province_actions=province_actions,
            policy=policy,
            phase=Phase.Y1_Q2,
            previous_action=None,
            seed=1,
            prompt_version="v1",
            model_version="fake",
        )
        for key in automakers
    }
    first = env.settle_year(
        policy=policy,
        province_actions=province_actions,
        automaker_actions=automaker_actions,
        phase=Phase.Y1_Q4,
    )
    second = env.settle_year(
        policy=policy,
        province_actions=province_actions,
        automaker_actions=automaker_actions,
        phase=Phase.Y1_Q4,
    )
    assert first == second
    assert len(first.province_states) == 31 and len(first.automaker_states) == 10
    assert len(first.mechanism_contributions) == 62
    assert all(
        abs(sum(term.contribution for term in item.terms) - item.raw_value) < 1e-6
        for item in first.mechanism_contributions.values()
    )


def test_settlement_rejects_wrong_phase():
    env = ChinaPolicyEnv()
    with pytest.raises(ValueError, match="Q4"):
        env.settle_year(
            policy=PolicySchema(), province_actions={}, automaker_actions={}, phase=Phase.Y1_Q3
        )
