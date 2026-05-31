from pydantic import BaseModel

from backend.services.retrieval.contracts import RetrievalFilters


class RetrievalScoreBreakdown(BaseModel):
    vector_score: float = 0.0
    fts_score: float = 0.0
    hybrid_score: float = 0.0
    metadata_match_score: float = 0.0
    use_case_score: float = 0.0
    explicit_term_match_score: float = 0.0
    supporting_term_match_score: float = 0.0
    final_score: float = 0.0


class RetrievalTrace(BaseModel):
    original_query: str
    normalized_query_text: str
    normalization_notes: list[str]
    rewritten_terms: list[str]
    applied_filters: RetrievalFilters
    understanding_notes: list[str] = []
    rewrite_notes: list[str] = []
    rewrite_for_embedding: str = ""
    rewrite_for_fts: str = ""
    user_explicit_terms: list[str] = []
    expansion_terms: list[str] = []
    fallback_path: str | None = None
    vector_candidate_count: int = 0
    fts_candidate_count: int = 0
    fused_candidate_count: int = 0
    dropped_candidate_reasons: list[str] = []
    representation_bundle_used: bool = False
    fts_document_version: str = ""
    rerank_features_used: list[str] = []


class AgentSearchDebugSummary(BaseModel):
    mode: str
    topic_action: str | None = None
    search_spec_ids: list[str] = []
    critic_reason_code: str | None = None
    retry_count: int = 0


class AgentSearchResponse(BaseModel):
    request_id: str
    final_items: list[dict]
    response_reason: str | None = None
    debug: AgentSearchDebugSummary | None = None
