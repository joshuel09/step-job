"""Application settings, loaded from the environment."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://stepjob:stepjob@localhost:5432/stepjob"
    environment: str = "local"

    # Which model provider to use. "fake" is the default so local work and
    # continuous integration never reach the network (research.md R-004).
    ai_provider: str = "fake"
    openai_api_key: str = ""
    ai_model: str = "gpt-4o-mini"

    # How long an import may run inside the request before it is handed to the
    # worker (research.md R-002). A setting so tests can force the handoff.
    import_deadline_seconds: float = 8.0

    # How many times an unavailable provider is retried before giving up.
    # Bounded deliberately: a user must not be left waiting on a recovery that
    # may never come (FR-017c).
    ai_max_retries: int = 3

    # How long a deleted profile remains recoverable before it is purged.
    # Fixed by FR-025; exposed here so tests can exercise the boundary without
    # waiting, not so that deployments can quietly lengthen retention.
    deletion_recovery_days: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
