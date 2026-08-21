from policyscope_api.dependencies import build_adapter
from policyscope_api.settings import Settings

from simulation.llm.cached_provider import CachedLLMProvider
from simulation.llm.live_provider import LiveLLMProvider
from simulation.llm.m34_provider import M34CachedAgentProvider, build_m34_agent_provider


def test_local_default_uses_fake_mode() -> None:
    settings = Settings(_env_file=None)

    assert settings.run_mode.value == "fake"


def test_luna_role_defaults_and_secret_redaction() -> None:
    settings = Settings(_env_file=None, run_mode="live", llm_api_key="sensitive-test-key")

    assert settings.llm_base_url == "https://api.openai.com/v1"
    assert settings.central_model == "gpt-5.6-luna"
    assert settings.province_model == "gpt-5.6-luna"
    assert settings.automaker_model == "gpt-5.6-luna"
    assert settings.llm_timeout_seconds == 60
    assert settings.llm_max_concurrency == 8
    assert "sensitive-test-key" not in repr(settings)

    adapter = build_adapter(settings)
    assert isinstance(adapter.provider, LiveLLMProvider)
    assert adapter.provider.central_model == "gpt-5.6-luna"
    assert adapter.provider.province_model == "gpt-5.6-luna"
    assert adapter.provider.automaker_model == "gpt-5.6-luna"
    assert adapter.provider.thinking_enabled is False


def test_cache_mode_can_use_deepseek_for_misses_without_exposing_secret(tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        run_mode="cache",
        cache_miss_mode="live",
        llm_base_url="https://api.deepseek.com",
        llm_api_key="deepseek-sensitive-test-key",
        central_model="deepseek-v4-flash",
        province_model="deepseek-v4-flash",
        POLICYSCOPE_ENTERPRISE_MODEL="deepseek-v4-flash",
        runtime_dir=tmp_path,
    )

    adapter = build_adapter(settings)

    assert isinstance(adapter.provider, CachedLLMProvider)
    assert isinstance(adapter.provider.fallback, LiveLLMProvider)
    assert settings.automaker_model == "deepseek-v4-flash"
    assert "deepseek-sensitive-test-key" not in repr(settings)

    m34_provider = build_m34_agent_provider(adapter.provider, tmp_path / "m34-cache")
    assert isinstance(m34_provider, M34CachedAgentProvider)
    assert m34_provider.miss_mode == "live"
    assert m34_provider.model_name_for("automaker_tick") == "cache-first:deepseek-v4-flash"
