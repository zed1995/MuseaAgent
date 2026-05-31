from typing import Literal, TypedDict

from backend.agents.contracts import CandidateItem, CriticResult, SearchResult, SearchSpec


class VisualSearchState(TypedDict):
    request_id: str
    conversation_id: str | None
    user_id: str | None
    original_query: str
    conversation_history: list[dict]
    mode: Literal["wallpaper", "reference", "photographer", "auto"]
    topic_action: Literal["new", "refine", "reset"] | None
    hard_constraints: dict
    soft_preferences: dict
    search_specs: list[SearchSpec]
    search_results: list[SearchResult]
    critic_result: CriticResult | None
    retry_count: int
    final_items: list[CandidateItem]
    response_reason: str | None
    errors: list[str]
