from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from simulation.models.common import RunMode


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="POLICYSCOPE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Safe default for local/direct starts. Production explicitly opts into
    # cache-first mode and a live miss provider through deployment settings.
    run_mode: RunMode = RunMode.FAKE
    cache_miss_mode: Literal["fake", "live"] = "fake"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: SecretStr = SecretStr("")
    central_model: str = Field(default="gpt-5.6-luna", alias="POLICYSCOPE_CENTRAL_MODEL")
    province_model: str = Field(default="gpt-5.6-luna", alias="POLICYSCOPE_PROVINCE_MODEL")
    automaker_model: str = Field(
        default="gpt-5.6-luna",
        validation_alias=AliasChoices(
            "POLICYSCOPE_AUTOMAKER_MODEL",
            "POLICYSCOPE_ENTERPRISE_MODEL",
        ),
    )

    @property
    def enterprise_model(self) -> str:
        """Backward-compatible environment alias used by older deployments."""
        return self.automaker_model

    llm_timeout_seconds: float = 60
    llm_max_concurrency: int = 8
    llm_max_tokens: int = 4096
    llm_thinking: Literal["enabled", "disabled"] = "disabled"
    runtime_dir: Path = Path("runtime")
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
