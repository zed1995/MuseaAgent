from backend.services.indexing.semantic_enrichment import _extract_json


def test_extract_json_plain() -> None:
    assert _extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_with_markdown_fence() -> None:
    raw = "```json\n{\"a\": 1}\n```"
    assert _extract_json(raw) == {"a": 1}


def test_extract_json_with_fence_no_lang() -> None:
    raw = "```\n{\"a\": 1}\n```"
    assert _extract_json(raw) == {"a": 1}


def test_extract_json_raises_on_empty() -> None:
    import pytest
    with pytest.raises(ValueError, match="empty response"):
        _extract_json("")
