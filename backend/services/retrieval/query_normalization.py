"""Deterministic rule-based query normalization for Chinese photo-search queries.

Converts Chinese query text into a normalized English representation
with extracted hard filters (orientation, has_human) and soft preference signals.
"""

from __future__ import annotations

import re
from typing import List

from backend.services.retrieval.contracts import NormalizedQuery, RetrievalFilters


# ---------------------------------------------------------------------------
# Translation tables
# ---------------------------------------------------------------------------

# Chinese phrase -> English rewrite term (longer keys must appear first
# so that greedy left-to-right scanning picks the correct match).
_TERM_MAPPINGS: dict[str, str] = {
    "深色": "dark",
    "安静": "calm",
    "极简": "minimal",
    "山景": "mountain",
    "山": "mountain",
    "电影感": "cinematic",
    "城市": "city",
    "夜景": "night",
    "壁纸": "wallpaper",
    "参考图": "reference",
}

# Phrases that signal has_human = False
_FILTER_NO_HUMAN: List[str] = ["不要人物", "无人", "no people"]

# Phrases that signal has_human = True
_FILTER_HAS_HUMAN: List[str] = ["有人", "with people"]

# Mobile/portrait wallpaper orientation triggers
_MOBILE_WALLPAPER_TERMS: List[str] = ["手机壁纸", "锁屏", "竖屏"]

# Explicit landscape orientation trigger
_LANDSCAPE_TERMS: List[str] = ["横屏"]

# Chinese stop patterns / query framing phrases to strip
_STOP_PATTERNS: List[str] = ["我想找", "找一点", "一点", "的"]

# All filter phrases (for removal during term rewriting)
_ALL_FILTER_PHRASES: List[str] = (
    _FILTER_NO_HUMAN
    + _FILTER_HAS_HUMAN
    + _MOBILE_WALLPAPER_TERMS
    + _LANDSCAPE_TERMS
)

# Term-mapping keys ordered longest-first for greedy matching
_TERM_KEYS_SORTED: List[str] = sorted(
    _TERM_MAPPINGS.keys(), key=len, reverse=True
)


class QueryNormalizationService:
    """Chinese-to-English query normalizer with optional model-backed translation.

    When a ``translator`` callable is provided (e.g. via OpenRouter), queries
    containing Chinese characters are first translated to English by the model
    before the deterministic rewrite and filter extraction pass.  Without a
    translator the service falls back to the deterministic mapping table only.
    """

    def __init__(
        self,
        translator: callable | None = None,  # Callable[[str], str] | None
    ) -> None:
        self._translator = translator

    def normalize(
        self,
        query: str,
        mode: str,
        request_filters: RetrievalFilters | None = None,
    ) -> NormalizedQuery:
        """Normalize a Chinese photo-search query.

        Parameters
        ----------
        query:
            Raw user query (may contain Chinese and/or English).
        mode:
            Search mode (``"wallpaper"``, ``"reference"``, ``"auto"``).
        request_filters:
            Optional explicit filters from the HTTP request.  When provided,
            explicit values win over inferred values; inferred values only
            fill gaps.

        Returns
        -------
        NormalizedQuery
        """
        cleaned = self._clean_query(query)

        # Model-backed translation: when Chinese is detected and a translator
        # is available, translate the full query to English first.  This
        # handles Chinese terms not covered by the deterministic mapping.
        has_chinese = bool(re.search(r"[一-鿿]", cleaned))
        if has_chinese and self._translator is not None:
            try:
                translated = self._translator(cleaned)
                cleaned = self._clean_query(translated)
            except Exception:
                # translator failure is non-fatal — fall through to rules
                pass

        extracted_filters = self._extract_filters(cleaned, mode)

        # -- Merge with explicit request filters (explicit wins) ----------
        notes: List[str] = []
        if request_filters is not None:
            final_orientation = (
                request_filters.orientation or extracted_filters.orientation
            )
            final_has_human = (
                request_filters.has_human
                if request_filters.has_human is not None
                else extracted_filters.has_human
            )
            filters = RetrievalFilters(
                orientation=final_orientation, has_human=final_has_human
            )
            if (
                request_filters.orientation
                and extracted_filters.orientation
                and request_filters.orientation != extracted_filters.orientation
            ):
                notes.append(
                    f"orientation overridden: "
                    f"{extracted_filters.orientation} -> "
                    f"{request_filters.orientation}"
                )
        else:
            filters = extracted_filters

        rewritten_terms = self._rewrite_terms(cleaned, mode, filters)
        soft_signals = self._soft_signals(cleaned, rewritten_terms)
        notes.extend(self._notes(cleaned, filters, rewritten_terms))

        return NormalizedQuery(
            original_query=query,
            normalized_query_text=" ".join(rewritten_terms),
            rewritten_terms=rewritten_terms,
            filters=filters,
            soft_signals=soft_signals,
            normalization_notes=notes,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _clean_query(self, query: str) -> str:
        """Strip whitespace and normalise common full-width punctuation."""
        cleaned = query.strip()
        for punc in "，。！？、；：（）【】《》":
            cleaned = cleaned.replace(punc, " ")
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()

    def _extract_filters(self, cleaned: str, mode: str) -> RetrievalFilters:
        """Extract hard filters from cleaned query text and search mode."""
        orientation: str | None = None
        has_human: bool | None = None

        # --- Orientation --------------------------------------------------
        # Explicit landscape terms take highest precedence
        for term in _LANDSCAPE_TERMS:
            if term in cleaned:
                orientation = "landscape"
                break

        if orientation is None:
            for term in _MOBILE_WALLPAPER_TERMS:
                if term in cleaned:
                    orientation = "portrait"
                    break

        if orientation is None and mode == "wallpaper":
            orientation = "portrait"

        # --- Human presence ------------------------------------------------
        for phrase in _FILTER_NO_HUMAN:
            if phrase in cleaned:
                has_human = False
                break
        if has_human is None:
            for phrase in _FILTER_HAS_HUMAN:
                if phrase in cleaned:
                    has_human = True
                    break

        return RetrievalFilters(orientation=orientation, has_human=has_human)

    def _rewrite_terms(
        self, cleaned: str, mode: str, filters: RetrievalFilters
    ) -> list[str]:
        """Translate known Chinese terms and pass through non-Chinese tokens."""
        text = cleaned

        # Strip filter phrases (they were already extracted into filters)
        for phrase in _ALL_FILTER_PHRASES:
            text = text.replace(phrase, "")

        # Strip query framing / stop patterns
        for pattern in _STOP_PATTERNS:
            text = text.replace(pattern, "")

        text = re.sub(r"\s+", " ", text).strip()

        result: List[str] = []
        i = 0
        while i < len(text):
            # 1) Try to match a known Chinese term (longest-first)
            matched = False
            for key in _TERM_KEYS_SORTED:
                if text[i:].startswith(key):
                    result.append(_TERM_MAPPINGS[key])
                    i += len(key)
                    matched = True
                    break
            if matched:
                continue

            ch = text[i]

            # 2) Skip whitespace
            if ch == " ":
                i += 1
                continue

            # 3) Skip unrecognised Chinese characters (not in any mapping)
            if "一" <= ch <= "鿿":
                i += 1
                continue

            # 4) Accumulate a non-Chinese, non-space token (e.g. "OLED")
            j = i
            while j < len(text) and text[j] != " " and not (
                "一" <= text[j] <= "鿿"
            ):
                j += 1

            token = text[i:j].lower()
            if token and token not in result:
                result.append(token)
            i = j

        # Cap at 10-15 terms
        return result[:15]

    def _soft_signals(
        self, cleaned: str, rewritten_terms: list[str]
    ) -> dict[str, bool | float | str]:
        """Derive soft preference signals from rewritten terms."""
        signals: dict[str, bool | float | str] = {}
        if "dark" in rewritten_terms:
            signals["prefer_dark"] = True
        if "minimal" in rewritten_terms:
            signals["prefer_minimal"] = True
        if "cinematic" in rewritten_terms:
            signals["prefer_cinematic"] = True
        return signals

    def _notes(
        self,
        cleaned: str,
        filters: RetrievalFilters,
        rewritten_terms: list[str],
    ) -> list[str]:
        """Generate observation notes about what was extracted."""
        notes: List[str] = []
        if filters.orientation:
            notes.append(f"orientation inferred: {filters.orientation}")
        if filters.has_human is not None:
            notes.append(f"has_human inferred: {filters.has_human}")
        return notes
