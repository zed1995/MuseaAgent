"""Temporary debug endpoint for Phase 4 retrieval verification.

This is NOT the final /api/search/photos endpoint. It exists only to
let developers verify the retrieval core against real database content
before the proper API route is built in a later phase.
"""

import math

from fastapi import APIRouter, Query
from sqlalchemy import create_engine

from backend.core.config import get_settings
from backend.services.retrieval.contracts import RetrievalFilters
from backend.services.retrieval.factory import build_retrieval_service

router = APIRouter(tags=["search-debug"])


@router.get("/search/debug")
def search_debug(
    query: str = Query(..., description="Chinese or English search query"),
    mode: str = Query("auto", description="wallpaper | reference | auto"),
    limit: int = Query(10, ge=1, le=100),
    has_human: bool | None = Query(None, description="Filter: has_human"),
    orientation: str | None = Query(None, description="Filter: portrait | landscape | squarish"),
):
    settings = get_settings()
    engine = create_engine(settings.database.url)
    session = engine.connect()

    try:
        from sqlalchemy.orm import Session as ORMSession

        orm_session = ORMSession(bind=session)
        service = build_retrieval_service(
            session=orm_session,
            settings=settings,
        )

        filters = RetrievalFilters(orientation=orientation, has_human=has_human)
        response = service.retrieve(query=query, mode=mode, limit=limit, filters=filters)

        return {
            "query": query,
            "normalized_query": response.normalized_query,
            "mode": mode,
            "applied_filters": {
                "orientation": response.applied_filters.orientation,
                "has_human": response.applied_filters.has_human,
            },
            "soft_signals": response.trace.normalization_notes,
            "path_status": {
                "vector": "failed" if "vector_path_failed" in response.trace.dropped_candidate_reasons else "ok",
                "fts": "failed" if "fts_path_failed" in response.trace.dropped_candidate_reasons else "ok",
            },
            "candidate_counts": {
                "vector": response.trace.vector_candidate_count,
                "fts": response.trace.fts_candidate_count,
                "fused": response.trace.fused_candidate_count,
            },
            "results": [
                {
                    "photo_id": item.unsplash_photo_id,
                    "orientation": item.orientation,
                    "has_human": item.has_human,
                    "search_text": item.search_text,
                    "wallpaper_score": item.wallpaper_score,
                    "photography_reference_score": item.photography_reference_score,
                    "scores": {
                        "vector": 0.0 if math.isnan(item.score_breakdown.vector_score) else item.score_breakdown.vector_score,
                        "fts": 0.0 if math.isnan(item.score_breakdown.fts_score) else item.score_breakdown.fts_score,
                        "hybrid": 0.0 if math.isnan(item.score_breakdown.hybrid_score) else item.score_breakdown.hybrid_score,
                        "metadata_match": 0.0 if math.isnan(item.score_breakdown.metadata_match_score) else item.score_breakdown.metadata_match_score,
                        "use_case": 0.0 if math.isnan(item.score_breakdown.use_case_score) else item.score_breakdown.use_case_score,
                        "final": 0.0 if math.isnan(item.score_breakdown.final_score) else item.score_breakdown.final_score,
                    },
                }
                for item in response.items
            ],
        }
    finally:
        session.close()
        engine.dispose()
