from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from simulation.models.common import RunMode


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="POLICYSCOPE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    run_mode: RunMode = RunMode.FAKE
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    central_model: str = Field(default="gpt-5-mini", alias="POLICYSCOPE_CENTRAL_MODEL")
    province_model: str = Field(default="gpt-5-mini", alias="POLICYSCOPE_PROVINCE_MODEL")
    llm_timeout_seconds: float = 12
    llm_max_concurrency: int = 16
    runtime_dir: Path = Path("runtime")
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
