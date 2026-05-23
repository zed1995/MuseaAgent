"""Failing tests for QueryNormalizationService contract.

These tests validate the interface and contract of the normalization service
before it is implemented. They will fail until Task 3 is completed.
"""

from backend.services.retrieval.query_normalization import QueryNormalizationService


def test_normalization_extracts_supported_filters_from_chinese_wallpaper_query() -> None:
    service = QueryNormalizationService()

    result = service.normalize(
        query="我想找深色安静的 OLED 壁纸，不要人物",
        mode="wallpaper",
    )

    assert result.normalized_query_text == "dark calm oled wallpaper"
    assert result.filters.orientation == "portrait"
    assert result.filters.has_human is False
    assert "dark" in result.rewritten_terms


def test_normalization_infers_portrait_for_mobile_wallpaper_terms() -> None:
    service = QueryNormalizationService()
    result = service.normalize(query="手机壁纸 极简山景", mode="wallpaper")
    assert result.filters.orientation == "portrait"
    assert "minimal" in result.rewritten_terms
    assert "mountain" in result.rewritten_terms


def test_normalization_extracts_has_human_false_from_no_people_phrase() -> None:
    service = QueryNormalizationService()
    result = service.normalize(query="深色壁纸 不要人物", mode="wallpaper")
    assert result.filters.has_human is False
    assert "dark" in result.rewritten_terms


def test_normalization_keeps_reference_mode_without_forcing_orientation() -> None:
    service = QueryNormalizationService()
    result = service.normalize(query="找一点电影感的城市夜景参考图", mode="reference")
    assert result.filters.orientation is None
    assert "cinematic" in result.rewritten_terms
    assert "city" in result.rewritten_terms
    assert "night" in result.rewritten_terms
