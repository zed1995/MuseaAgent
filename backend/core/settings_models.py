from pydantic import BaseModel


class DatabaseSettings(BaseModel):
    url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/musea_agent"
    echo: bool = False


class RetrievalSettings(BaseModel):
    vector_candidate_limit: int = 100
    fts_candidate_limit: int = 60
    fused_candidate_limit: int = 80
    default_result_limit: int = 20
    enable_debug_endpoint: bool = False


class RetrievalPreparationSettings(BaseModel):
    enabled: bool = True
    understanding_model: str = "google/gemini-2.5-flash-lite"
    rewrite_model: str = "google/gemini-2.5-flash-lite"
    use_model_understanding: bool = True
    use_model_rewrite: bool = True


class AgentWorkflowSettings(BaseModel):
    enabled: bool = True
    max_retry_count: int = 1
    min_acceptable_results: int = 6
    hard_constraint_min_match_ratio: float = 0.85


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
