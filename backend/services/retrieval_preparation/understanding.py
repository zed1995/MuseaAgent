from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from json import JSONDecodeError

from backend.llm.chains.retrieval_understanding_chain import RetrievalUnderstandingChain
from backend.services.retrieval.contracts import RetrievalFilters
from backend.services.retrieval_preparation.contracts import (
    HardFilters,
    NegativeConstraints,
    QueryUnderstandingResult,
    SoftPreferences,
)

logger = logging.getLogger(__name__)


def _strip_markdown_code_fence(payload: str) -> str:
    stripped = payload.strip()
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, flags=re.DOTALL)
    if match is not None:
        return match.group(1).strip()
    return stripped


class QueryUnderstandingService:
    def __init__(
        self,
        model_client: Callable[[str, str], str | dict] | None = None,
        chain: RetrievalUnderstandingChain | None = None,
    ) -> None:
        self._model_client = model_client
        self._chain = chain

    def understand(
        self,
        query: str,
        mode: str,
        explicit_filters: RetrievalFilters | None = None,
    ) -> QueryUnderstandingResult:
        # Understanding is responsible for extracting structured intent and
        # constraints once, before retrieval paths start diverging.
        if self._chain is not None:
            result = self._chain.invoke({"query": query, "mode": mode})
            return self._merge_explicit_filters(result, explicit_filters)
        if self._model_client is None:
            result = self._understand_deterministically(query, mode)
            return self._merge_explicit_filters(result, explicit_filters)
        result = self._understand_with_model(query, mode)
        return self._merge_explicit_filters(result, explicit_filters)

    def _understand_with_model(self, query: str, mode: str) -> QueryUnderstandingResult:
        # Legacy model-client support is kept for compatibility while the
        # LangChain capability layer becomes the primary structured path.
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
        # Explicit API filters win over inferred filters so route-level user
        # intent remains authoritative when it conflicts with model inference.
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

    def _understand_deterministically(self, query: str, mode: str) -> QueryUnderstandingResult:
        lower = query.lower()

        if mode != "auto":
            inferred_mode = mode
        elif "壁纸" in query or "wallpaper" in lower:
            inferred_mode = "wallpaper"
        elif "参考" in query or "reference" in lower:
            inferred_mode = "reference"
        else:
            inferred_mode = "generic"

        has_human = None
        exclude_people = False
        if any(token in query for token in ["不要人物", "无人", "没有人物"]) or "no people" in lower:
            has_human = False
            exclude_people = True

        orientation = None
        if any(token in query for token in ["手机壁纸", "竖屏"]) or "portrait" in lower:
            orientation = "portrait"

        colors: list[str] = []
        if "深色" in query or "dark" in lower:
            colors.append("dark")

        moods: list[str] = []
        if "安静" in query or "calm" in lower:
            moods.append("calm")

        qualities: list[str] = []
        if "oled" in lower:
            qualities.append("oled")

        return QueryUnderstandingResult(
            raw_query=query,
            detected_language="zh" if any("\u4e00" <= char <= "\u9fff" for char in query) else "en",
            inferred_mode=inferred_mode,
            hard_filters=HardFilters(orientation=orientation, has_human=has_human),
            negative_constraints=NegativeConstraints(exclude_people=exclude_people),
            soft_preferences=SoftPreferences(
                moods=moods,
                colors=colors,
                qualities=qualities,
            ),
            understanding_notes=["understanding fallback used"],
        )
