from pydantic import BaseModel


class DatabaseSettings(BaseModel):
    url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/musea_agent"
    echo: bool = False


class IndexingSettings(BaseModel):
    # Mock flags — when True, use stub implementations (no real API calls)
    mock_translation: bool = True
    mock_enrichment: bool = True
    mock_embedding: bool = True

    # Model selection (used when mock_* is False)
    translation_model: str = "gpt-4o-mini"
    enrichment_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"

    # Timeout per capability (seconds)
    translation_timeout_seconds: float = 10.0
    enrichment_timeout_seconds: float = 20.0
    embedding_timeout_seconds: float = 10.0

    # OpenAI / OpenAI-compatible API connection
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"

    # Separate config for embedding (OpenRouter doesn't offer embeddings,
    # so this can point to OpenAI API directly while enrichment uses OpenRouter)
    embedding_api_key: str = ""
    embedding_base_url: str = ""
