from fastapi import Request

from policyscope_api.settings import Settings
from simulation.adapters.asyncio_adapter import AsyncioSimulationAdapter
from simulation.llm.cached_provider import CachedLLMProvider
from simulation.llm.fake_provider import FakeLLMProvider
from simulation.llm.live_provider import LiveLLMProvider
from simulation.models.common import RunMode


def build_adapter(settings: Settings) -> AsyncioSimulationAdapter:
    fallback = FakeLLMProvider()

    def live_provider() -> LiveLLMProvider:
        if not settings.llm_api_key.get_secret_value():
            raise RuntimeError(
                "POLICYSCOPE_LLM_API_KEY is required when live generation is enabled"
            )
        return LiveLLMProvider(
            api_key=settings.llm_api_key.get_secret_value(),
            base_url=settings.llm_base_url,
            central_model=settings.central_model,
            province_model=settings.province_model,
            automaker_model=settings.automaker_model,
            fallback=fallback,
            timeout_seconds=settings.llm_timeout_seconds,
            max_concurrency=settings.llm_max_concurrency,
            max_tokens=settings.llm_max_tokens,
            thinking_enabled=settings.llm_thinking == "enabled",
        )

    if settings.run_mode == RunMode.LIVE:
        provider = live_provider()
    elif settings.run_mode == RunMode.CACHE:
        miss_provider = live_provider() if settings.cache_miss_mode == "live" else fallback
        provider = CachedLLMProvider(
            settings.runtime_dir / "cache" / "default",
            miss_provider,
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
