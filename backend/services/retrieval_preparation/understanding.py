from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from json import JSONDecodeError

from backend.services.retrieval.contracts import RetrievalFilters
from backend.services.retrieval_preparation.contracts import (
    HardFilters,
    QueryUnderstandingResult,
)

logger = logging.getLogger(__name__)


def _strip_markdown_code_fence(payload: str) -> str:
    stripped = payload.strip()
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, flags=re.DOTALL)
    if match is not None:
        return match.group(1).strip()
    return stripped


class QueryUnderstandingService:
    def __init__(self, model_client: Callable[[str, str], str | dict] | None = None) -> None:
        self._model_client = model_client

    def understand(
        self,
        query: str,
        mode: str,
        explicit_filters: RetrievalFilters | None = None,
    ) -> QueryUnderstandingResult:
        if self._model_client is None:
            raise RuntimeError("model-backed understanding is required")
        result = self._understand_with_model(query, mode)
        return self._merge_explicit_filters(result, explicit_filters)

    def _understand_with_model(self, query: str, mode: str) -> QueryUnderstandingResult:
        payload = self._model_client(query, mode)
        if isinstance(payload, str):
            normalized_payload = _strip_markdown_code_fence(payload)
            if not normalized_payload:
                logger.error(
                    "[understanding] model returned blank payload for query=%r mode=%s",
                    query,
                    mode,
                )
            else:
                logger.info(
                    "[understanding] model payload received for query=%r mode=%s preview=%r",
                    query,
                    mode,
                    normalized_payload[:240],
                )
            try:
                payload = json.loads(normalized_payload)
            except JSONDecodeError:
                logger.error(
                    "[understanding] model returned invalid json for query=%r mode=%s preview=%r",
                    query,
                    mode,
                    normalized_payload[:240],
                )
                raise
        return QueryUnderstandingResult.model_validate(payload)

    def _merge_explicit_filters(
        self,
        result: QueryUnderstandingResult,
        explicit_filters: RetrievalFilters | None,
    ) -> QueryUnderstandingResult:
        if explicit_filters is None:
            return result

        notes = list(result.understanding_notes)
        orientation = result.hard_filters.orientation
        if explicit_filters.orientation is not None:
            if orientation is not None and orientation != explicit_filters.orientation:
                notes.append(
                    f"orientation overridden: {orientation} -> {explicit_filters.orientation}"
                )
            orientation = explicit_filters.orientation

        has_human = result.hard_filters.has_human
        if explicit_filters.has_human is not None:
            if has_human is not None and has_human != explicit_filters.has_human:
                notes.append(
                    f"has_human overridden: {has_human} -> {explicit_filters.has_human}"
                )
            has_human = explicit_filters.has_human

        return result.model_copy(
            update={
                "hard_filters": HardFilters(orientation=orientation, has_human=has_human),
                "understanding_notes": notes,
            }
        )
