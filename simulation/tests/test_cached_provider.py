from simulation.data import load_network, load_profiles, load_scenario_policy
from simulation.envs.china_policy_env import ChinaPolicyEnv
from simulation.llm.cached_provider import CachedLLMProvider
from simulation.llm.fake_provider import FakeLLMProvider
from simulation.models.common import Phase


async def test_cache_miss_and_hit_are_explicit(tmp_path) -> None:
    profiles = load_profiles()
    network = load_network()
    policy = load_scenario_policy()
    env = ChinaPolicyEnv(profiles=profiles, network=network, policy=policy)
    provider = CachedLLMProvider(tmp_path, FakeLLMProvider())
    arguments = {
        "profile": profiles["44"],
        "state": env.states["44"],
        "policy": policy,
        "phase": Phase.T1,
        "related": network["44"],
        "neighbor_actions": {},
    }

    fallback = await provider.generate_province_action(**arguments)
    cached = await provider.generate_province_action(**arguments)

    assert fallback.run_mode == "fallback"
    assert fallback.fallback_used is True
    assert cached.run_mode == "cache"
    assert cached.fallback_used is False
