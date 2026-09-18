"""Application settings, loaded from the environment."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://stepjob:stepjob@localhost:5432/stepjob"
    environment: str = "local"

    # How long a deleted profile remains recoverable before it is purged.
    # Fixed by FR-025; exposed here so tests can exercise the boundary without
    # waiting, not so that deployments can quietly lengthen retention.
    deletion_recovery_days: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
