#!/usr/bin/env python3
import asyncio
import json
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
    config = ExperimentConfig(
        objective=(
            "在有限财政支持下推动制造业设备升级，提高中小企业参与度，"
            "并兼顾绿色转型、就业稳定和区域可达性。"
        ),
        run_mode=RunMode.CACHE,
        model_version="cache-v3",
    )
    await adapter.run_full_demo(config)
    manifest = {
        "schema_version": "demo-cache-manifest-v1",
        "product_version": "PolicyScope V2.1",
        "scenario_id": config.scenario_id,
        "seed": config.seed,
        "model_version": config.model_version,
        "prompt_version": config.prompt_version,
        "artifacts": sorted(path.name for path in provider.accessed_cache_files),
    }
    (provider.cache_dir / "v21_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("Default PolicyScope V2.1 cache precomputed.")


if __name__ == "__main__":
    asyncio.run(main())
