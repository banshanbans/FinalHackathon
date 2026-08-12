from policyscope_api.dependencies import build_adapter
from policyscope_api.settings import Settings

from simulation.llm.live_provider import LiveLLMProvider


def test_deepseek_role_defaults_and_secret_redaction() -> None:
    settings = Settings(_env_file=None, run_mode="live", llm_api_key="sensitive-test-key")

    assert settings.llm_base_url == "https://api.deepseek.com"
    assert settings.central_model == "deepseek-v4-flash"
    assert settings.province_model == "deepseek-v4-flash"
    assert settings.enterprise_model == "deepseek-v4-flash"
    assert settings.llm_timeout_seconds == 60
    assert settings.llm_max_concurrency == 8
    assert "sensitive-test-key" not in repr(settings)

    adapter = build_adapter(settings)
    assert isinstance(adapter.provider, LiveLLMProvider)
    assert adapter.provider.central_model == "deepseek-v4-flash"
    assert adapter.provider.province_model == "deepseek-v4-flash"
    assert adapter.provider.enterprise_model == "deepseek-v4-flash"
    assert adapter.provider.thinking_enabled is False
