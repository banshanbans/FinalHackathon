from policyscope_api.dependencies import build_adapter
from policyscope_api.settings import Settings

from simulation.llm.live_provider import LiveLLMProvider


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
