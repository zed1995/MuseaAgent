from backend.services.retrieval_preparation.contracts import (
    QueryUnderstandingResult,
    RetrievalRewriteResult,
)
from backend.services.retrieval_preparation.rewrite import RetrievalRewriteService


def build_rewrite_fallback(
    understanding: QueryUnderstandingResult,
) -> RetrievalRewriteResult:
    # Fallback intentionally reuses the deterministic rewrite service so the
    # fallback behavior stays identical to the non-LLM baseline path.
    result = RetrievalRewriteService().rewrite(understanding)
    return result.model_copy(
        update={
            "rewrite_notes": [*result.rewrite_notes, "rewrite fallback used"],
        }
    )
