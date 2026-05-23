import logging
import math
from dataclasses import dataclass, field

from backend.services.retrieval.contracts import NormalizedQuery, RetrievalFilters, RetrievalRequest
from backend.services.retrieval.fusion import FusedRetrievalCandidate, reciprocal_rank_fusion
from backend.services.retrieval.query_normalization import QueryNormalizationService
from backend.services.retrieval.rerank import RankedRetrievalItem, RetrievalReranker
from backend.repositories.photo_index_repository import PhotoIndexRepository
from backend.schemas.search import RetrievalScoreBreakdown, RetrievalTrace
from backend.core.settings_models import RetrievalSettings

logger = logging.getLogger(__name__)


class RetrievalFailedError(Exception):
    """Both recall paths failed -- not just empty results."""


@dataclass(slots=True)
class RetrievalItem:
    photo_id: int
    unsplash_photo_id: str
    unsplash_user_id: str | None
    orientation: str | None
    has_human: bool
    search_text: str
    ai_caption: str
    wallpaper_score: float
    photography_reference_score: float
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
        logger.info("[retrieval] request: query=%r mode=%s limit=%d filters=%s", query, mode, limit, filters)

        # 1. Normalize
        normalized = self._normalizer.normalize(query, mode, filters)
        logger.info(
            "[normalize] input=%r output=%r terms=%s filters=(orientation=%s has_human=%s)",
            query,
            normalized.normalized_query_text,
            normalized.rewritten_terms,
            normalized.filters.orientation,
            normalized.filters.has_human,
        )

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
            # Treat all-NaN / all-zero scores as a failed vector path
            # (e.g. when a mock embedder returns a zero embedding).
            has_real_scores = any(
                hasattr(c, "vector_score")
                and not math.isnan(c.vector_score)
                and c.vector_score != 0.0
                for c in vector_candidates
            )
            if not has_real_scores:
                logger.info("[vector] all scores are zero/NaN — treating as failed path")
                vector_failed = True
                vector_candidates = []
            else:
                logger.info(
                    "[vector] embed=%s… limit=%s candidates=%d",
                    str(embedding[:3]),
                    v_limit,
                    len(vector_candidates),
                )
        except Exception as exc:
            vector_failed = True
            logger.warning("[vector] failed: %s: %s", type(exc).__name__, exc)

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
            logger.info(
                "[fts] query=%r limit=%s candidates=%d (filters: orientation=%s has_human=%s)",
                normalized.normalized_query_text,
                f_limit,
                len(fts_candidates),
                normalized.filters.orientation,
                normalized.filters.has_human,
            )
        except Exception as exc:
            fts_failed = True
            logger.warning("[fts] failed: %s: %s", type(exc).__name__, exc)

        # 4. Dual failure
        if vector_failed and fts_failed:
            logger.error("[retrieval] both recall paths failed; raising RetrievalFailedError")
            raise RetrievalFailedError("Both vector and FTS recall paths failed")

        # 5. Fuse
        fused_limit = self._settings.fused_candidate_limit
        fused = reciprocal_rank_fusion(vector_candidates, fts_candidates, k=fused_limit)
        vector_ids = {c.unsplash_photo_id for c in vector_candidates}
        fts_ids = {c.unsplash_photo_id for c in fts_candidates}
        logger.info(
            "[fusion] vector=%d fts=%d fused=%d (k=%s) overlap=%d",
            len(vector_candidates),
            len(fts_candidates),
            len(fused),
            fused_limit,
            len(vector_ids & fts_ids),
        )

        # 6. Rerank
        final_limit = limit or self._settings.default_result_limit
        ranked = self._reranker.rank(
            candidates=fused,
            mode=mode,
            filters=normalized.filters,
            soft_signals=normalized.soft_signals,
            limit=final_limit,
        )
        logger.info(
            "[rerank] input=%d candidates output=%d mode=%s top=%s final=%.4f",
            len(fused),
            len(ranked),
            mode,
            ranked[0].unsplash_photo_id if ranked else "—",
            ranked[0].score_breakdown.final_score if ranked else 0,
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
                has_human=r.has_human,
                search_text=r.search_text,
                ai_caption=r.ai_caption,
                wallpaper_score=r.wallpaper_score,
                photography_reference_score=r.photography_reference_score,
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
