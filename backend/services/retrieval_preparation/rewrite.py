from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from json import JSONDecodeError

from backend.services.retrieval_preparation.contracts import (
    QueryUnderstandingResult,
    RetrievalRewriteResult,
)

logger = logging.getLogger(__name__)


def _strip_markdown_code_fence(payload: str) -> str:
    stripped = payload.strip()
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, flags=re.DOTALL)
    if match is not None:
        return match.group(1).strip()
    return stripped


class RetrievalRewriteService:
    def __init__(self, model_client: Callable[[QueryUnderstandingResult], str | dict] | None = None) -> None:
        self._model_client = model_client

    def rewrite(self, understanding: QueryUnderstandingResult) -> RetrievalRewriteResult:
        if self._model_client is not None:
            payload = self._model_client(understanding)
            if isinstance(payload, str):
                normalized_payload = _strip_markdown_code_fence(payload)
                if not normalized_payload:
                    logger.error(
                        "[rewrite] model returned blank payload for query=%r mode=%s",
                        understanding.raw_query,
                        understanding.inferred_mode,
                    )
                else:
                    logger.info(
                        "[rewrite] model payload received for query=%r mode=%s preview=%r",
                        understanding.raw_query,
                        understanding.inferred_mode,
                        normalized_payload[:240],
                    )
                try:
                    payload = json.loads(normalized_payload)
                except JSONDecodeError:
                    logger.error(
                        "[rewrite] model returned invalid json for query=%r mode=%s preview=%r",
                        understanding.raw_query,
                        understanding.inferred_mode,
                        normalized_payload[:240],
                    )
                    raise
            return RetrievalRewriteResult.model_validate(payload)
        return self._rewrite_deterministically(understanding)

    def _rewrite_deterministically(
        self,
        understanding: QueryUnderstandingResult,
    ) -> RetrievalRewriteResult:
        user_explicit_terms: list[str] = []
        for values in (
            understanding.soft_preferences.colors,
            understanding.soft_preferences.moods,
            understanding.soft_preferences.styles,
            understanding.soft_preferences.scenes,
            understanding.soft_preferences.subjects,
            understanding.soft_preferences.qualities,
            understanding.subject_candidates,
            understanding.scene_candidates,
            understanding.style_candidates,
            understanding.mood_candidates,
            understanding.color_candidates,
        ):
            for value in values:
                if value not in user_explicit_terms:
                    user_explicit_terms.append(value)

        use_case = understanding.inferred_mode
        if use_case == "wallpaper" and "wallpaper" not in user_explicit_terms:
            user_explicit_terms.append("wallpaper")
        elif use_case == "reference" and "reference" not in user_explicit_terms:
            user_explicit_terms.append("reference")

        negative_terms: list[str] = []
        if understanding.negative_constraints.exclude_people:
            negative_terms.append("people")
        if understanding.negative_constraints.exclude_faces:
            negative_terms.append("faces")

        expansion_terms: list[str] = []
        lexical_terms = list(user_explicit_terms)
        embedding_terms = list(user_explicit_terms) + expansion_terms
        if understanding.negative_constraints.exclude_people:
            embedding_terms.extend(["with", "no", "people"])
        if understanding.negative_constraints.exclude_faces:
            embedding_terms.extend(["with", "no", "faces"])

        fts_terms = list(user_explicit_terms)
        if understanding.hard_filters.orientation is not None:
            fts_terms.append(understanding.hard_filters.orientation)

        return RetrievalRewriteResult(
            rewrite_for_embedding=" ".join(dict.fromkeys(embedding_terms)),
            rewrite_for_fts=" ".join(dict.fromkeys(fts_terms)),
            lexical_terms=lexical_terms,
            user_explicit_terms=user_explicit_terms,
            expansion_terms=expansion_terms,
            negative_terms=negative_terms,
            rewrite_notes=[
                "embedding rewrite kept compact semantic phrasing",
                "fts rewrite prioritized user-explicit lexical terms",
            ],
        )
