from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from simulation.models.common import RunMode


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="POLICYSCOPE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    run_mode: RunMode = RunMode.CACHE
    llm_base_url: str = "https://api.deepseek.com"
    llm_api_key: SecretStr = SecretStr("")
    central_model: str = Field(default="deepseek-v4-flash", alias="POLICYSCOPE_CENTRAL_MODEL")
    province_model: str = Field(default="deepseek-v4-flash", alias="POLICYSCOPE_PROVINCE_MODEL")
    enterprise_model: str = Field(default="deepseek-v4-flash", alias="POLICYSCOPE_ENTERPRISE_MODEL")
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
