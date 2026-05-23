from dataclasses import dataclass, field

from backend.services.retrieval.contracts import NormalizedQuery, RetrievalFilters, RetrievalRequest
from backend.services.retrieval.fusion import FusedRetrievalCandidate, reciprocal_rank_fusion
from backend.services.retrieval.query_normalization import QueryNormalizationService
from backend.services.retrieval.rerank import RankedRetrievalItem, RetrievalReranker
from backend.repositories.photo_index_repository import PhotoIndexRepository
from backend.schemas.search import RetrievalScoreBreakdown, RetrievalTrace
from backend.core.settings_models import RetrievalSettings


class RetrievalFailedError(Exception):
    """Both recall paths failed -- not just empty results."""


@dataclass(slots=True)
class RetrievalItem:
    photo_id: int
    unsplash_photo_id: str
    unsplash_user_id: str | None
    orientation: str | None
    search_text: str
    ai_caption: str
    score_breakdown: RetrievalScoreBreakdown


@dataclass(slots=True)
class RetrievalResponse:
    normalized_query: str
    applied_filters: RetrievalFilters
    candidates_considered: int
    items: list[RetrievalItem]
    trace: RetrievalTrace


class RetrievalService:
    def __init__(
        self,
        repository: PhotoIndexRepository,
        normalizer: QueryNormalizationService,
        embedder: callable,  # Callable[[str], list[float]]
        reranker: RetrievalReranker,
        settings: RetrievalSettings,
    ) -> None:
        self._repository = repository
        self._normalizer = normalizer
        self._embedder = embedder
        self._reranker = reranker
        self._settings = settings

    def retrieve(
        self,
        query: str,
        mode: str = "auto",
        limit: int = 20,
        filters: RetrievalFilters | None = None,
        debug: bool = False,
    ) -> RetrievalResponse:
        # 1. Normalize
        normalized = self._normalizer.normalize(query, mode, filters)

        # 2. Vector path (with error isolation)
        vector_candidates: list = []
        vector_failed = False
        try:
            embedding = self._embedder(normalized.normalized_query_text)
            v_limit = self._settings.vector_candidate_limit
            vector_candidates = self._repository.search_vector(
                query_embedding=embedding,
                orientation=normalized.filters.orientation,
                has_human=normalized.filters.has_human,
                limit=v_limit,
            )
        except Exception:
            vector_failed = True

        # 3. FTS path (with error isolation)
        fts_candidates: list = []
        fts_failed = False
        try:
            f_limit = self._settings.fts_candidate_limit
            fts_candidates = self._repository.search_full_text(
                query_text=normalized.normalized_query_text,
                orientation=normalized.filters.orientation,
                has_human=normalized.filters.has_human,
                limit=f_limit,
            )
        except Exception:
            fts_failed = True

        # 4. Dual failure
        if vector_failed and fts_failed:
            raise RetrievalFailedError("Both vector and FTS recall paths failed")

        # 5. Fuse
        fused_limit = self._settings.fused_candidate_limit
        fused = reciprocal_rank_fusion(vector_candidates, fts_candidates, k=fused_limit)

        # 6. Rerank
        final_limit = limit or self._settings.default_result_limit
        ranked = self._reranker.rank(
            candidates=fused,
            mode=mode,
            filters=normalized.filters,
            soft_signals=normalized.soft_signals,
            limit=final_limit,
        )

        # 7. Build response
        return self._build_response(
            query, normalized, ranked, vector_candidates, fts_candidates, fused,
            vector_failed, fts_failed, debug,
        )

    def _build_response(
        self,
        original_query: str,
        normalized: NormalizedQuery,
        ranked: list[RankedRetrievalItem],
        vector_candidates: list,
        fts_candidates: list,
        fused: list[FusedRetrievalCandidate],
        vector_failed: bool,
        fts_failed: bool,
        debug: bool,
    ) -> RetrievalResponse:
        dropped = []
        if vector_failed:
            dropped.append("vector_path_failed")
        if fts_failed:
            dropped.append("fts_path_failed")

        items = [
            RetrievalItem(
                photo_id=r.id,
                unsplash_photo_id=r.unsplash_photo_id,
                unsplash_user_id=r.unsplash_user_id,
                orientation=r.orientation,
                search_text=r.search_text,
                ai_caption=r.ai_caption,
                score_breakdown=r.score_breakdown,
            )
            for r in ranked
        ]

        trace = RetrievalTrace(
            original_query=original_query,
            normalized_query_text=normalized.normalized_query_text,
            normalization_notes=normalized.normalization_notes,
            rewritten_terms=normalized.rewritten_terms,
            applied_filters=normalized.filters,
            vector_candidate_count=len(vector_candidates),
            fts_candidate_count=len(fts_candidates),
            fused_candidate_count=len(fused),
            dropped_candidate_reasons=dropped,
        )

        return RetrievalResponse(
            normalized_query=normalized.normalized_query_text,
            applied_filters=normalized.filters,
            candidates_considered=len(fused),
            items=items,
            trace=trace,
        )
