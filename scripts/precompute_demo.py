#!/usr/bin/env python3
import asyncio
import json
from pathlib import Path

from simulation.adapters.asyncio_adapter import AsyncioSimulationAdapter
from simulation.llm.cached_provider import CachedLLMProvider
from simulation.llm.fake_provider import FakeLLMProvider
from simulation.models.common import ComparisonMode, EventIntensity, EventTemplateId, RunMode
from simulation.models.experiment import ExperimentConfig
from simulation.models.scenario import EventScenarioSelection


async def main() -> None:
    cache_dir = Path("runtime/cache/v3_1")
    provider = CachedLLMProvider(cache_dir, FakeLLMProvider(), write_through=True)
    cases: list[dict[str, object]] = []
    for comparison_mode in ComparisonMode:
        for template_id in EventTemplateId:
            for intensity in EventIntensity:
                before_hits = provider.cache_hits
                before_misses = provider.cache_misses
                adapter = AsyncioSimulationAdapter(provider, runtime_dir=Path("runtime"))
                config = ExperimentConfig(
                    objective=(
                        "比较冻结中央政策与事件情景对地方财政空间、新能源汽车需求"
                        "和产业布局的模拟影响。"
                    ),
                    comparison_mode=comparison_mode,
                    run_mode=RunMode.CACHE,
                    model_version="cache-nev-v2",
                )
                selection = EventScenarioSelection(
                    template_id=template_id,
                    intensity=intensity,
                )
                result = await adapter.run_full_demo(config, selection)
                cases.append(
                    {
                        "comparison_mode": comparison_mode.value,
                        "template_id": template_id.value,
                        "intensity": intensity.value,
                        "cache_hits": provider.cache_hits - before_hits,
                        "cache_misses": provider.cache_misses - before_misses,
                        "delta_gap": result.delta_gap,
                        "active_difference": result.active_difference_proof.active_difference,
                    }
                )
    manifest = {
        "schema_version": "demo-cache-manifest-v4",
        "product_version": "PolicyScope V3.1",
        "matrix": {
            "comparison_modes": [item.value for item in ComparisonMode],
            "templates": [item.value for item in EventTemplateId],
            "intensities": [item.value for item in EventIntensity],
            "case_count": len(cases),
        },
        "versions": {
            "mechanism": "nev-policy-env-v2",
            "world": "world-state-v5",
            "comparison": "comparison-v5",
            "event": "event-v5",
            "prompt": "nev-policy-agents-v2",
            "model": "cache-nev-v2",
        },
        "total_cache_hits_during_generation": provider.cache_hits,
        "total_cache_misses_during_generation": provider.cache_misses,
        "artifact_count": len(provider.accessed_cache_files),
        "cases": cases,
        "artifacts": sorted(path.name for path in provider.accessed_cache_files),
    }
    (cache_dir / "v3_1_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        "PolicyScope V3.1 cache matrix precomputed: "
        f"{len(cases)} cases, {len(provider.accessed_cache_files)} artifacts."
    )


if __name__ == "__main__":
    asyncio.run(main())
