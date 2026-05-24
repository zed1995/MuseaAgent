from backend.services.retrieval_preparation.contracts import (
    HardFilters,
    NegativeConstraints,
    QueryUnderstandingResult,
    SoftPreferences,
)
from backend.services.retrieval_preparation.fallback import (
    build_rewrite_fallback,
)


def test_fallback_can_build_rewrites_from_understanding_result() -> None:
    understanding = QueryUnderstandingResult(
        raw_query="深色壁纸 不要人物",
        detected_language="zh",
        inferred_mode="wallpaper",
        hard_filters=HardFilters(has_human=False),
        negative_constraints=NegativeConstraints(exclude_people=True),
        soft_preferences=SoftPreferences(colors=["dark"]),
    )

    rewrite = build_rewrite_fallback(understanding)

    assert rewrite.rewrite_for_embedding
    assert "rewrite fallback used" in rewrite.rewrite_notes


def test_rewrite_fallback_requires_structured_terms_from_understanding() -> None:
    understanding = QueryUnderstandingResult(
        raw_query="ignored by rewrite fallback",
        detected_language="zh",
        inferred_mode="generic",
        hard_filters=HardFilters(),
        negative_constraints=NegativeConstraints(),
        soft_preferences=SoftPreferences(colors=["monochrome"], scenes=["forest"], subjects=["trees"]),
    )

    rewrite = build_rewrite_fallback(understanding)

    assert "monochrome" in rewrite.rewrite_for_fts
    assert "forest" in rewrite.rewrite_for_fts


def test_rewrite_fallback_does_not_recover_terms_from_raw_query() -> None:
    understanding = QueryUnderstandingResult(
        raw_query="黑白森林树木图片",
        detected_language="zh",
        inferred_mode="generic",
        hard_filters=HardFilters(),
        negative_constraints=NegativeConstraints(),
        soft_preferences=SoftPreferences(),
    )

    try:
        build_rewrite_fallback(understanding)
    except Exception as exc:
        assert "rewrite" in str(exc).lower() or "character" in str(exc).lower()
    else:
        raise AssertionError("rewrite fallback should fail without structured terms")
