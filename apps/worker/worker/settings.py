"""Worker configuration."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    redis_url: str = "redis://localhost:6379/0"
    # How often the purge sweep runs. It only needs to be well under a day for a
    # 30-day window, so hourly is ample and keeps the load trivial.
    purge_interval_seconds: int = 3600


@lru_cache
def get_worker_settings() -> WorkerSettings:
    return WorkerSettings()
