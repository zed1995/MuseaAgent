from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.core.settings_models import (
    DatabaseSettings,
    IndexingSettings,
    RetrievalPreparationSettings,
    RetrievalSettings,
)


class Settings(BaseSettings):
    app_name: str = "MuseaAgent API"
    app_version: str = "0.1.0"
    environment: str = "development"
    api_prefix: str = "/api"
    database: DatabaseSettings = DatabaseSettings()
    indexing: IndexingSettings = IndexingSettings()
    retrieval: RetrievalSettings = RetrievalSettings()
    retrieval_preparation: RetrievalPreparationSettings = RetrievalPreparationSettings()

    model_config = SettingsConfigDict(
        env_prefix="MUSEA_AGENT_",
        env_nested_delimiter="__",
        env_file=".env",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
