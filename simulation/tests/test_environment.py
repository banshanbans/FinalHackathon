import asyncio
from copy import deepcopy

from simulation.data import load_network, load_profiles, load_scenario_policy
from simulation.envs.china_policy_env import ChinaPolicyEnv
from simulation.llm.fake_provider import FakeLLMProvider
from simulation.models.common import Phase


async def _actions(env: ChinaPolicyEnv):
    provider = FakeLLMProvider()
    result = {}
    for code, profile in env.profiles.items():
        result[code] = await provider.generate_province_action(
            profile=profile,
            state=env.states[code],
            policy=env.policy,
            phase=Phase.T1,
            related=env.network[code],
            neighbor_actions={},
        )
    return result


def test_environment_is_deterministic_and_bounded() -> None:
    profiles = load_profiles()
    network = load_network()
    policy = load_scenario_policy()
    env_a = ChinaPolicyEnv(profiles=profiles, network=network, policy=policy)
    env_b = ChinaPolicyEnv(
        profiles=profiles,
        network=network,
        policy=policy,
        states=deepcopy(env_a.states),
    )
    actions = asyncio.run(_actions(env_a))
    before = {code: state.policy_benefit_index for code, state in env_a.states.items()}
    states_a, contributions_a = env_a.process_actions(actions, Phase.T2)
    states_b, contributions_b = env_b.process_actions(actions, Phase.T2)
    assert states_a == states_b
    assert contributions_a == contributions_b
    for code, state in states_a.items():
        assert 0 <= state.policy_benefit_index <= 100
        assert (
            abs(state.policy_benefit_index - before[code] - contributions_a[code].net_effect) < 1e-3
        )


def test_snapshot_restore_round_trip() -> None:
    profiles = load_profiles()
    network = load_network()
    env = ChinaPolicyEnv(profiles=profiles, network=network, policy=load_scenario_policy())
    restored = ChinaPolicyEnv.restore(env.snapshot(), profiles=profiles, network=network)
    assert restored.policy == env.policy
    assert restored.states == env.states
