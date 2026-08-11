from fastapi import Request

from policyscope_api.settings import Settings
from simulation.adapters.asyncio_adapter import AsyncioSimulationAdapter
from simulation.llm.cached_provider import CachedLLMProvider
from simulation.llm.fake_provider import FakeLLMProvider
from simulation.llm.live_provider import LiveLLMProvider
from simulation.models.common import RunMode


def build_adapter(settings: Settings) -> AsyncioSimulationAdapter:
    fallback = FakeLLMProvider()
    if settings.run_mode == RunMode.LIVE:
        if not settings.llm_api_key:
            raise RuntimeError("POLICYSCOPE_LLM_API_KEY is required in live mode")
        provider = LiveLLMProvider(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            central_model=settings.central_model,
            province_model=settings.province_model,
            fallback=fallback,
            timeout_seconds=settings.llm_timeout_seconds,
            max_concurrency=settings.llm_max_concurrency,
        )
    elif settings.run_mode == RunMode.CACHE:
        provider = CachedLLMProvider(
            settings.runtime_dir / "cache" / "default",
            fallback,
            write_through=True,
        )
    else:
        provider = fallback
    return AsyncioSimulationAdapter(
        provider=provider,
        runtime_dir=settings.runtime_dir,
        agent_timeout_seconds=settings.llm_timeout_seconds,
    )


def get_adapter(request: Request) -> AsyncioSimulationAdapter:
    return request.app.state.adapter
