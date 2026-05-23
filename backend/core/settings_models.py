from pydantic import BaseModel


class DatabaseSettings(BaseModel):
    url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/musea_agent"
    echo: bool = False


class IndexingSettings(BaseModel):
    translation_provider: str = "stub"
    enrichment_provider: str = "stub"
    embedding_provider: str = "stub"
    translation_model: str = "stub-translation"
    enrichment_model: str = "stub-vision"
    embedding_model: str = "stub-embedding"
    translation_timeout_seconds: float = 10.0
    enrichment_timeout_seconds: float = 20.0
    embedding_timeout_seconds: float = 10.0
