from backend.services.indexing.contracts import RepresentationArtifacts


def _normalize_fragments(values: list[str | None]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        stripped = " ".join(value.split())
        if not stripped:
            continue
        lowered = stripped.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(stripped)
    return normalized


def _join_fragments(values: list[str | None], *, separator: str) -> str:
    return separator.join(_normalize_fragments(values))


def compose_retrieval_representation(
    *,
    search_text: str,
    ai_short_caption: str | None,
    ai_caption: str | None,
    scene_tags: list[str],
    mood_tags: list[str],
    style_tags: list[str],
    composition_tags: list[str],
    lighting_tags: list[str],
    color_tags: list[str],
    subject_tags: list[str],
    use_case_tags: list[str],
) -> RepresentationArtifacts:
    retrieval_caption_text = _join_fragments(
        [ai_short_caption, ai_caption],
        separator=". ",
    )
    retrieval_tag_text = _join_fragments(
        [
            *scene_tags,
            *mood_tags,
            *style_tags,
            *composition_tags,
            *lighting_tags,
            *color_tags,
            *subject_tags,
            *use_case_tags,
        ],
        separator=" ",
    )
    retrieval_document_text = _join_fragments(
        [search_text, retrieval_caption_text, retrieval_tag_text],
        separator=". ",
    )
    return RepresentationArtifacts(
        retrieval_caption_text=retrieval_caption_text,
        retrieval_tag_text=retrieval_tag_text,
        retrieval_document_text=retrieval_document_text,
        embedding_text=retrieval_document_text,
    )
