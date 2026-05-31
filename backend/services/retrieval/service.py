import logging
from dataclasses import dataclass

from backend.services.retrieval.contracts import RetrievalFilters
from backend.services.retrieval.fusion import FusedRetrievalCandidate, reciprocal_rank_fusion
from backend.services.retrieval.rerank import RankedRetrievalItem, RetrievalReranker
from backend.repositories.photo_index_repository import PhotoIndexRepository
from backend.schemas.search import RetrievalScoreBreakdown, RetrievalTrace
from backend.core.settings_models import RetrievalSettings
from backend.services.retrieval_preparation.contracts import PreparedRetrievalRequest

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
    retrieval_caption_text: str = ""
    retrieval_tag_text: str = ""


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
        preparation_service,
        embedder: callable,  # Callable[[str], list[float]]
        reranker: RetrievalReranker,
        settings: RetrievalSettings,
    ) -> None:
        self._repository = repository
        self._preparation_service = preparation_service
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

        # Consumer flow: normalize once, run vector + FTS independently, fuse,
        # rerank, then return both user-facing items and a trace for debugging.
        # Each recall path is isolated so one failure can degrade gracefully.
        # 1. Normalize
        prepared = self._preparation_service.prepare(query, mode, filters)
        hard_filters = RetrievalFilters(
            orientation=prepared.understanding.hard_filters.orientation,
            has_human=prepared.understanding.hard_filters.has_human,
        )
        logger.info(
            "[prepare] input=%r embedding=%r fts=%r filters=(orientation=%s has_human=%s)",
            query,
            prepared.rewrite.rewrite_for_embedding,
            prepared.rewrite.rewrite_for_fts,
            hard_filters.orientation,
            hard_filters.has_human,
        )

        # 2. Vector path (with error isolation)
        vector_candidates: list = []
        vector_failed = False
        try:
            embedding = self._embedder(prepared.rewrite.rewrite_for_embedding)
            v_limit = self._settings.vector_candidate_limit
            vector_candidates = self._repository.search_vector(
                query_embedding=embedding,
                orientation=hard_filters.orientation,
                has_human=hard_filters.has_human,
                limit=v_limit,
            )
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
                query_text=prepared.rewrite.rewrite_for_fts,
                orientation=hard_filters.orientation,
                has_human=hard_filters.has_human,
                limit=f_limit,
            )
            logger.info(
                "[fts] query=%r limit=%s candidates=%d (filters: orientation=%s has_human=%s)",
                prepared.rewrite.rewrite_for_fts,
                f_limit,
                len(fts_candidates),
                hard_filters.orientation,
                hard_filters.has_human,
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
            filters=hard_filters,
            soft_signals=self._soft_signals(prepared),
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
            query, prepared, ranked, vector_candidates, fts_candidates, fused,
            vector_failed, fts_failed, debug,
        )

    def _build_response(
        self,
        original_query: str,
        prepared: PreparedRetrievalRequest,
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
                retrieval_caption_text=r.retrieval_caption_text,
                retrieval_tag_text=r.retrieval_tag_text,
                wallpaper_score=r.wallpaper_score,
                photography_reference_score=r.photography_reference_score,
                score_breakdown=r.score_breakdown,
            )
            for r in ranked
        ]

        trace = RetrievalTrace(
            # The trace keeps the consumer pipeline inspectable end-to-end,
            # which is what powers `/api/search/debug` and agent diagnostics.
            original_query=original_query,
            normalized_query_text=prepared.rewrite.rewrite_for_fts,
            normalization_notes=prepared.understanding.understanding_notes,
            rewritten_terms=prepared.rewrite.lexical_terms,
            applied_filters=RetrievalFilters(
                orientation=prepared.understanding.hard_filters.orientation,
                has_human=prepared.understanding.hard_filters.has_human,
            ),
            understanding_notes=prepared.understanding.understanding_notes,
            rewrite_notes=prepared.rewrite.rewrite_notes,
            rewrite_for_embedding=prepared.rewrite.rewrite_for_embedding,
            rewrite_for_fts=prepared.rewrite.rewrite_for_fts,
            user_explicit_terms=prepared.rewrite.user_explicit_terms,
            expansion_terms=prepared.rewrite.expansion_terms,
            fallback_path=self._fallback_path(prepared),
            vector_candidate_count=len(vector_candidates),
            fts_candidate_count=len(fts_candidates),
            fused_candidate_count=len(fused),
            dropped_candidate_reasons=dropped,
            representation_bundle_used=True,
            fts_document_version="multi_field_weighted_v1",
            rerank_features_used=[
                "multi_field_alignment",
                "structured_phase_3_signals",
            ],
        )

        return RetrievalResponse(
            normalized_query=prepared.rewrite.rewrite_for_fts,
            applied_filters=RetrievalFilters(
                orientation=prepared.understanding.hard_filters.orientation,
                has_human=prepared.understanding.hard_filters.has_human,
            ),
            candidates_considered=len(fused),
            items=items,
            trace=trace,
        )

    def _soft_signals(
        self,
        prepared: PreparedRetrievalRequest,
    ) -> dict[str, list[str]]:
        preferences = prepared.understanding.soft_preferences
        supporting_terms: list[str] = []
        for values in (
            prepared.rewrite.expansion_terms,
            preferences.moods,
            preferences.styles,
            preferences.scenes,
            preferences.subjects,
            preferences.colors,
            preferences.qualities,
        ):
            for value in values:
                if value not in supporting_terms and value not in prepared.rewrite.user_explicit_terms:
                    supporting_terms.append(value)
        return {
            "user_explicit_terms": prepared.rewrite.user_explicit_terms,
            "supporting_terms": supporting_terms,
            "exclude_faces": prepared.understanding.negative_constraints.exclude_faces,
        }

    def _fallback_path(self, prepared: PreparedRetrievalRequest) -> str | None:
        notes = set(prepared.understanding.understanding_notes + prepared.rewrite.rewrite_notes)
        if "understanding fallback used" in notes:
            return "full"
        if "rewrite fallback used" in notes:
            return "rewrite"
        return None
