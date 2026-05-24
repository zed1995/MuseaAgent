from backend.services.retrieval_preparation.contracts import (
    HardFilters,
    NegativeConstraints,
    QueryUnderstandingResult,
    RetrievalRewriteResult,
    SoftPreferences,
)
from backend.services.retrieval_preparation.rewrite import RetrievalRewriteService


def _understanding() -> QueryUnderstandingResult:
    return QueryUnderstandingResult(
        raw_query="我想找深色安静的 OLED 壁纸，不要人物",
        detected_language="zh",
        inferred_mode="wallpaper",
        hard_filters=HardFilters(orientation=None, has_human=False),
        negative_constraints=NegativeConstraints(exclude_people=True),
        soft_preferences=SoftPreferences(
            moods=["calm"],
            styles=["minimal"],
            colors=["dark"],
            qualities=["oled"],
        ),
        understanding_notes=["wallpaper use case inferred"],
    )


def test_rewrite_generates_distinct_embedding_and_fts_outputs() -> None:
    service = RetrievalRewriteService()
    result = service.rewrite(_understanding())

    assert result.rewrite_for_embedding
    assert result.rewrite_for_fts
    assert result.lexical_terms
    assert result.user_explicit_terms


def test_rewrite_preserves_negative_people_constraint() -> None:
    service = RetrievalRewriteService()
    result = service.rewrite(_understanding())

    assert "people" in result.negative_terms
    assert "no people" in result.rewrite_for_embedding
    assert "people" not in result.rewrite_for_fts


def test_rewrite_lexical_terms_are_english_and_deduplicated() -> None:
    service = RetrievalRewriteService()
    result = service.rewrite(_understanding())

    assert result.lexical_terms == list(dict.fromkeys(result.lexical_terms))
    assert all(term.isascii() for term in result.lexical_terms)
    assert result.user_explicit_terms == list(dict.fromkeys(result.user_explicit_terms))
    assert result.expansion_terms == []
    assert result.rewrite_for_fts == " ".join(dict.fromkeys(result.user_explicit_terms))


def test_rewrite_result_rejects_empty_rewrites() -> None:
    try:
        RetrievalRewriteResult(
            rewrite_for_embedding="",
            rewrite_for_fts="",
            lexical_terms=[],
            user_explicit_terms=[],
            expansion_terms=[],
            negative_terms=[],
        )
    except Exception:
        pass
    else:
        raise AssertionError("empty rewrite strings should be rejected")


def test_rewrite_does_not_infer_terms_from_raw_query_when_understanding_is_empty() -> None:
    service = RetrievalRewriteService()
    understanding = QueryUnderstandingResult(
        raw_query="黑白森林树木图片",
        detected_language="zh",
        inferred_mode="generic",
        hard_filters=HardFilters(),
        negative_constraints=NegativeConstraints(),
        soft_preferences=SoftPreferences(),
    )

    try:
        service.rewrite(understanding)
    except Exception as exc:
        assert "rewrite" in str(exc).lower() or "character" in str(exc).lower()
    else:
        raise AssertionError("rewrite should fail without structured understanding terms")


def test_rewrite_accepts_json_wrapped_in_markdown_fence() -> None:
    service = RetrievalRewriteService(
        model_client=lambda understanding: """```json
{
  "rewrite_for_embedding": "beach sunset no people",
  "rewrite_for_fts": "beach sunset",
  "lexical_terms": ["beach", "sunset"],
  "user_explicit_terms": ["beach", "sunset"],
  "expansion_terms": [],
  "negative_terms": ["people"],
  "rewrite_notes": ["parsed from fenced json"]
}
```"""
    )

    result = service.rewrite(_understanding())

    assert result.user_explicit_terms == ["beach", "sunset"]
    assert result.negative_terms == ["people"]


def test_rewrite_logs_invalid_json_payload(caplog) -> None:
    service = RetrievalRewriteService(model_client=lambda understanding: "not json")

    try:
        service.rewrite(_understanding())
    except Exception:
        pass
    else:
        raise AssertionError("invalid model json should fail")

    assert "invalid json" in caplog.text.lower()


def test_rewrite_result_coerces_string_notes_to_list() -> None:
    result = RetrievalRewriteResult(
        rewrite_for_embedding="beach sunset",
        rewrite_for_fts="beach sunset",
        lexical_terms=["beach", "sunset"],
        user_explicit_terms=["beach", "sunset"],
        expansion_terms=[],
        negative_terms=[],
        rewrite_notes="single note string",
    )

    assert result.rewrite_notes == ["single note string"]
