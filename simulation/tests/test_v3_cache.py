import pytest

from simulation.adapters.asyncio_adapter import AsyncioSimulationAdapter
from simulation.llm.cached_provider import CachedLLMProvider
from simulation.llm.fake_provider import FakeLLMProvider
from simulation.models.common import RunMode
from simulation.models.experiment import ExperimentConfig


@pytest.mark.asyncio
async def test_cache_write_through_then_replays_identically(tmp_path):
    cache = tmp_path / "cache"
    first_provider = CachedLLMProvider(cache, FakeLLMProvider())
    first_adapter = AsyncioSimulationAdapter(first_provider, runtime_dir=tmp_path / "r1")
    first = await first_adapter.run_full_demo(
        ExperimentConfig(objective="缓存稳定性", run_mode=RunMode.CACHE)
    )
    first_worlds = [
        await first_adapter.get_state(first.experiment_id, branch_id)
        for branch_id in (first.control_branch_id, first.treatment_branch_id)
    ]
    second_provider = CachedLLMProvider(cache, FakeLLMProvider())
    second_adapter = AsyncioSimulationAdapter(second_provider, runtime_dir=tmp_path / "r2")
    second = await second_adapter.run_full_demo(
        ExperimentConfig(objective="缓存稳定性", run_mode=RunMode.CACHE)
    )
    second_worlds = [
        await second_adapter.get_state(second.experiment_id, branch_id)
        for branch_id in (second.control_branch_id, second.treatment_branch_id)
    ]
    assert first.delta_gap == second.delta_gap
    assert (
        len(first_provider.accessed_cache_files) == len(second_provider.accessed_cache_files) == 281
    )
    assert all(path.exists() for path in second_provider.accessed_cache_files)
    assert second_provider.cache_hits == 281
    assert second_provider.cache_misses == 0
    assert all(
        len(world.fallback_provinces) == 31
        and len(world.fallback_automakers) == 10
        and len(world.fallback_event_provinces) == 31
        for world in first_worlds
    )
    assert all(
        not world.fallback_provinces
        and not world.fallback_automakers
        and not world.fallback_event_provinces
        for world in second_worlds
    )
    assert all(
        action.run_mode is RunMode.CACHE
        for world in second_worlds
        for action in [*world.province_actions.values(), *world.automaker_actions.values()]
    )
