#!/usr/bin/env python3
import asyncio
from pathlib import Path

from simulation.adapters.asyncio_adapter import AsyncioSimulationAdapter
from simulation.llm.cached_provider import CachedLLMProvider
from simulation.llm.fake_provider import FakeLLMProvider
from simulation.models.common import RunMode
from simulation.models.experiment import ExperimentConfig


async def main() -> None:
    provider = CachedLLMProvider(
        Path("runtime/cache/default"), FakeLLMProvider(), write_through=True
    )
    adapter = AsyncioSimulationAdapter(provider, runtime_dir=Path("runtime"))
    await adapter.run_full_demo(
        ExperimentConfig(
            objective="促进战略性新兴产业创新，同时兼顾区域均衡与财政效率。",
            run_mode=RunMode.CACHE,
            model_version="cache-v1",
        )
    )
    print("Default PolicyScope cache precomputed.")


if __name__ == "__main__":
    asyncio.run(main())
