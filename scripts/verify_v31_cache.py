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
    records: list[dict[str, object]] = []
    for iteration in range(1, 4):
        for mode, template, expected_calls in (
            (ComparisonMode.POLICY_INTERVENTION, EventTemplateId.OIL_PRICE_RISE, 281),
            (
                ComparisonMode.EVENT_COUNTERFACTUAL,
                EventTemplateId.BATTERY_NODE_UPGRADE_SICHUAN,
                219,
            ),
        ):
            provider = CachedLLMProvider(
                Path("runtime/cache/v3_1"), FakeLLMProvider(), write_through=False
            )
            adapter = AsyncioSimulationAdapter(
                provider, runtime_dir=Path("runtime/cache-verification")
            )
            result = await adapter.run_full_demo(
                ExperimentConfig(
                    objective=(
                        "比较冻结中央政策与事件情景对地方财政空间、新能源汽车需求"
                        "和产业布局的模拟影响。"
                    ),
                    comparison_mode=mode,
                    run_mode=RunMode.CACHE,
                    model_version="cache-nev-v2",
                ),
                EventScenarioSelection(template_id=template, intensity=EventIntensity.MEDIUM),
            )
            assert provider.cache_misses == 0
            assert provider.cache_hits == expected_calls
            records.append(
                {
                    "iteration": iteration,
                    "comparison_mode": mode.value,
                    "cache_hits": provider.cache_hits,
                    "cache_misses": provider.cache_misses,
                    "delta_gap": result.delta_gap,
                }
            )
    print(json.dumps(records, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
