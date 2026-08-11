import asyncio
from copy import deepcopy

from simulation.data import (
    build_enterprise_profiles,
    enterprise_profiles_by_province,
    load_network,
    load_profiles,
    load_scenario_policy,
)
from simulation.envs.china_policy_env import ChinaPolicyEnv
from simulation.llm.fake_provider import FakeLLMProvider
from simulation.models.common import Phase


async def _actions(env: ChinaPolicyEnv):
    provider = FakeLLMProvider()
    province_actions = {}
    for code, profile in env.profiles.items():
        province_actions[code] = await provider.generate_province_action(
            profile=profile,
            state=env.province_states[code],
            policy=env.policy,
            phase=Phase.T1,
            related=env.network[code],
            neighbor_actions={},
            seed=20260812,
            prompt_version="test-v2",
            model_version="fake-v2",
        )
    grouped = enterprise_profiles_by_province(env.enterprise_profiles)
    enterprise_actions = {}
    for code, profiles in grouped.items():
        batch = await provider.generate_enterprise_actions_batch(
            province_profile=env.profiles[code],
            province_action=province_actions[code],
            enterprise_profiles=profiles,
            enterprise_states={
                item.enterprise_id: env.enterprise_states[item.enterprise_id] for item in profiles
            },
            policy=env.policy,
            phase=Phase.T2,
            seed=20260812,
            prompt_version="test-v2",
            model_version="fake-v2",
        )
        enterprise_actions.update({item.enterprise_id: item for item in batch.actions})
    return province_actions, enterprise_actions


def test_environment_is_deterministic_bounded_and_conserved() -> None:
    profiles = load_profiles()
    network = load_network()
    enterprise_profiles = build_enterprise_profiles(profiles)
    policy = load_scenario_policy()
    env_a = ChinaPolicyEnv(
        profiles=profiles,
        network=network,
        enterprise_profiles=enterprise_profiles,
        policy=policy,
    )
    env_b = ChinaPolicyEnv(
        profiles=profiles,
        network=network,
        enterprise_profiles=enterprise_profiles,
        policy=policy,
        province_states=deepcopy(env_a.province_states),
        enterprise_states=deepcopy(env_a.enterprise_states),
    )
    province_actions, enterprise_actions = asyncio.run(_actions(env_a))
    before = {key: state.renewal_willingness for key, state in env_a.enterprise_states.items()}
    result_a = env_a.process_actions(province_actions, enterprise_actions, Phase.T2)
    result_b = env_b.process_actions(province_actions, enterprise_actions, Phase.T2)
    assert result_a == result_b
    province_states, enterprise_states, aggregates, contributions = result_a
    assert len(province_states) == len(aggregates) == 31
    assert len(enterprise_states) == len(contributions) == 186
    for key, state in enterprise_states.items():
        assert 0 <= state.renewal_willingness <= 100
        assert abs(state.renewal_willingness - before[key] - contributions[key].net_effect) < 1e-3
    metrics = env_a.calculate_national_metrics()
    for field in type(metrics).model_fields:
        if field != "schema_version":
            assert 0 <= getattr(metrics, field) <= 100


def test_snapshot_restore_round_trip() -> None:
    env = ChinaPolicyEnv(policy=load_scenario_policy())
    restored = ChinaPolicyEnv.restore(
        env.snapshot(),
        profiles=env.profiles,
        network=env.network,
        enterprise_profiles=env.enterprise_profiles,
    )
    assert restored.policy == env.policy
    assert restored.province_states == env.province_states
    assert restored.enterprise_states == env.enterprise_states
