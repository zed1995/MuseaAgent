import pytest

from backend.services.indexing.contracts import EnrichmentContext, NormalizedSourcePhoto, RetrievalArtifacts, SemanticArtifacts, TextArtifacts


def test_enrichment_context_starts_with_empty_artifact_sections() -> None:
    context = EnrichmentContext(
        source=NormalizedSourcePhoto(
            unsplash_photo_id="photo-1",
            unsplash_user_id="user-1",
            raw_title="Night mountains",
            raw_description=None,
            raw_alt_description="Dark mountain landscape",
            orientation="landscape",
            width=3840,
            height=2160,
            regular_url="https://images.example/photo-1.jpg",
        )
    )

    assert context.text_artifacts.source_text is None
    assert context.semantic_artifacts.ai_caption is None
    assert context.retrieval_artifacts.embedding is None


def test_validation_rejects_missing_search_text() -> None:
    from backend.services.indexing.validation import build_completed_index_entry

    context = EnrichmentContext(
        source=NormalizedSourcePhoto(
            unsplash_photo_id="photo-1",
            unsplash_user_id=None,
            raw_title=None,
            raw_description=None,
            raw_alt_description=None,
            orientation="landscape",
            width=1024,
            height=768,
            regular_url="https://images.example/photo-1.jpg",
        )
    )

    with pytest.raises(ValueError, match="search_text"):
        build_completed_index_entry(context=context, entry_id=1001)
