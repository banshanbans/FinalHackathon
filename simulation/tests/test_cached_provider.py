from simulation.adapters.asyncio_adapter import AsyncioSimulationAdapter
from simulation.data import (
    enterprise_profiles_by_province,
    load_network,
    load_profiles,
    load_province_personas,
    load_scenario_policy,
)
from simulation.envs.china_policy_env import ChinaPolicyEnv
from simulation.llm.cached_provider import CachedLLMProvider
from simulation.llm.fake_provider import FakeLLMProvider
from simulation.models.common import Phase
from simulation.models.experiment import ExperimentConfig


async def test_cache_miss_and_hit_are_explicit_and_version_complete(tmp_path) -> None:
    profiles = load_profiles()
    network = load_network()
    policy = load_scenario_policy()
    personas = load_province_personas()
    env = ChinaPolicyEnv(profiles=profiles, network=network, policy=policy)
    provider = CachedLLMProvider(tmp_path, FakeLLMProvider())
    arguments = {
        "profile": profiles["44"],
        "persona": personas["44"],
        "state": env.province_states["44"],
        "policy": policy,
        "phase": Phase.T1,
        "related": network["44"],
        "neighbor_actions": {},
        "previous_action": None,
        "feedback": None,
        "seed": 20260812,
        "prompt_version": "prompt-v3",
        "model_version": "model-v3",
    }
    fallback = await provider.generate_province_action(**arguments)
    cached = await provider.generate_province_action(**arguments)
    assert fallback.run_mode == "fallback"
    assert fallback.fallback_used is True
    assert cached.run_mode == "cache"
    assert cached.fallback_used is False
    changed = await provider.generate_province_action(
        **{**arguments, "prompt_version": "prompt-v3.1"}
    )
    assert changed.run_mode == "fallback"


async def test_enterprise_batch_cache_contains_all_six_groups(tmp_path) -> None:
    env = ChinaPolicyEnv(policy=load_scenario_policy())
    personas = load_province_personas()
    provider = CachedLLMProvider(tmp_path, FakeLLMProvider())
    fake = FakeLLMProvider()
    province_action = await fake.generate_province_action(
        profile=env.profiles["41"],
        persona=personas["41"],
        state=env.province_states["41"],
        policy=env.policy,
        phase=Phase.T1,
        related=env.network["41"],
        neighbor_actions={},
        previous_action=None,
        feedback=None,
        seed=1,
        prompt_version="prompt-v3",
        model_version="model-v3",
    )
    enterprise_profiles = enterprise_profiles_by_province(env.enterprise_profiles)["41"]
    arguments = {
        "province_profile": env.profiles["41"],
        "province_action": province_action,
        "enterprise_profiles": enterprise_profiles,
        "enterprise_states": {
            item.enterprise_id: env.enterprise_states[item.enterprise_id]
            for item in enterprise_profiles
        },
        "policy": env.policy,
        "phase": Phase.T2,
        "seed": 1,
        "prompt_version": "prompt-v3",
        "model_version": "model-v3",
    }
    first = await provider.generate_enterprise_actions_batch(**arguments)
    second = await provider.generate_enterprise_actions_batch(**arguments)
    assert first.fallback_used is True
    assert first.fallback_reason == "cache_miss"
    assert second.fallback_used is False
    assert second.run_mode == "cache"
    assert len(second.actions) == 6


async def test_central_review_cache_ignores_only_volatile_lineage_ids(tmp_path) -> None:
    result = await AsyncioSimulationAdapter(
        FakeLLMProvider(), runtime_dir=tmp_path / "runtime"
    ).run_full_demo(ExperimentConfig(objective="测试中央复盘缓存"))
    result.central_review = None
    provider = CachedLLMProvider(tmp_path / "cache", FakeLLMProvider())

    first = await provider.generate_central_review(result)
    same_semantics = result.model_copy(
        update={
            "experiment_id": "exp_other",
            "checkpoint_id": "cp_other",
            "control_branch_id": "control_other",
            "treatment_branch_id": "treatment_other",
        },
        deep=True,
    )
    second = await provider.generate_central_review(same_semantics)

    assert first.public_summary == second.public_summary
    assert first.review_id != second.review_id
    assert len(list((tmp_path / "cache").glob("central_review_v2_*.json"))) == 1
