from typing import Literal

from pydantic import BaseModel, Field


class SearchSpec(BaseModel):
    spec_id: str
    query_text: str
    query_mode: Literal["strict", "balanced", "exploratory"]
    filters: dict[str, object] = Field(default_factory=dict)
    limit: int = 20


class CandidateItem(BaseModel):
    unsplash_photo_id: str
    orientation: str | None = None
    vector_score: float | None = None
    fts_score: float | None = None
    hybrid_score: float | None = None
    metadata_match_score: float | None = None
    use_case_score: float | None = None
    final_score: float
    matched_constraints: dict[str, object] = Field(default_factory=dict)
    source_spec_id: str


class SearchResult(BaseModel):
    spec_id: str
    total_hits: int
    items: list[CandidateItem] = Field(default_factory=list)
    debug: dict[str, object] = Field(default_factory=dict)


class CriticResult(BaseModel):
    passed: bool
    reason_code: Literal[
        "ok",
        "too_few_results",
        "hard_constraint_violation",
        "low_relevance",
        "overly_narrow_query",
    ]
    retry_strategy: Literal[
        "none",
        "switch_to_balanced",
        "switch_to_exploratory",
        "relax_soft_preferences",
    ]
    preferred_spec_id: str | None = None
    summary: str
