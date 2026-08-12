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
            "比较三档中央承担比例变化对地方财政空间、新能源汽车需求与真实头部车企模拟布局的影响。"
        ),
        run_mode=RunMode.CACHE,
        model_version="cache-nev-v1",
    )
    result = await adapter.run_full_demo(config)
    manifest = {
        "schema_version": "demo-cache-manifest-v3",
        "product_version": "PolicyScope V3.0",
        "scenario_id": config.scenario_id,
        "seed": config.seed,
        "data_version": config.data_version,
        "mechanism_version": config.mechanism_version,
        "model_version": config.model_version,
        "prompt_version": config.prompt_version,
        "comparison_schema": result.schema_version,
        "delta_gap": result.delta_gap,
        "artifacts": sorted(path.name for path in provider.accessed_cache_files),
    }
    (provider.cache_dir / "v3_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Default PolicyScope V3.0 cache precomputed: "
        f"{len(provider.accessed_cache_files)} artifacts, ΔGap={result.delta_gap:+.3f}."
    )


if __name__ == "__main__":
    asyncio.run(main())
