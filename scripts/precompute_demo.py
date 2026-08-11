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
            objective=(
                "在有限财政支持下推动制造业设备升级，提高中小企业参与度，"
                "并兼顾绿色转型、就业稳定和区域可达性。"
            ),
            run_mode=RunMode.CACHE,
            model_version="cache-v2",
        )
    )
    print("Default PolicyScope V2 cache precomputed.")


if __name__ == "__main__":
    asyncio.run(main())
