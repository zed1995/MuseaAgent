from pydantic import BaseModel

from backend.services.retrieval.contracts import RetrievalFilters


class RetrievalScoreBreakdown(BaseModel):
    vector_score: float = 0.0
    fts_score: float = 0.0
    hybrid_score: float = 0.0
    metadata_match_score: float = 0.0
    use_case_score: float = 0.0
    final_score: float = 0.0


class RetrievalTrace(BaseModel):
    original_query: str
    normalized_query_text: str
    normalization_notes: list[str]
    rewritten_terms: list[str]
    applied_filters: RetrievalFilters
    vector_candidate_count: int = 0
    fts_candidate_count: int = 0
    fused_candidate_count: int = 0
    dropped_candidate_reasons: list[str] = []
