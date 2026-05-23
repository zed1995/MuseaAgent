from datetime import UTC, datetime

import pytest

from backend.services.indexing.contracts import EnrichmentContext, NormalizedSourcePhoto, RetrievalArtifacts, SemanticArtifacts, TextArtifacts
from backend.services.indexing.validation import build_completed_index_entry


def test_validation_rejects_missing_search_text() -> None:
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


def test_validation_rejects_missing_ai_caption() -> None:
    context = EnrichmentContext(
        source=NormalizedSourcePhoto(
            unsplash_photo_id="photo-2",
            unsplash_user_id=None,
            raw_title=None,
            raw_description=None,
            raw_alt_description=None,
            orientation="landscape",
            width=1024,
            height=768,
            regular_url="https://images.example/photo-2.jpg",
        )
    )
    context.text_artifacts.search_text = "mountain wallpaper"

    with pytest.raises(ValueError, match="ai_caption"):
        build_completed_index_entry(context=context, entry_id=1002)


def test_validation_rejects_missing_embedding() -> None:
    context = EnrichmentContext(
        source=NormalizedSourcePhoto(
            unsplash_photo_id="photo-3",
            unsplash_user_id=None,
            raw_title=None,
            raw_description=None,
            raw_alt_description=None,
            orientation="landscape",
            width=1024,
            height=768,
            regular_url="https://images.example/photo-3.jpg",
        )
    )
    context.text_artifacts.search_text = "mountain wallpaper"
    context.semantic_artifacts.ai_caption = "A mountain wallpaper."

    with pytest.raises(ValueError, match="embedding"):
        build_completed_index_entry(context=context, entry_id=1003)


def test_validation_builds_completed_entry() -> None:
    context = EnrichmentContext(
        source=NormalizedSourcePhoto(
            unsplash_photo_id="photo-4",
            unsplash_user_id="user-1",
            raw_title="Night peak",
            raw_description="A dark mountain under the stars",
            raw_alt_description="Dark mountain wallpaper",
            orientation="landscape",
            width=1920,
            height=1080,
            regular_url="https://images.example/photo-4.jpg",
        )
    )
    context.text_artifacts.source_text = "Night peak\nA dark mountain under the stars\nDark mountain wallpaper"
    context.text_artifacts.search_text = "night peak dark mountain stars wallpaper"
    context.semantic_artifacts.ai_caption = "A dark mountain under the stars, ideal for wallpaper."
    context.semantic_artifacts.ai_short_caption = "Dark mountain wallpaper"
    context.semantic_artifacts.scene_tags = ["mountain", "night"]
    context.semantic_artifacts.mood_tags = ["calm"]
    context.semantic_artifacts.has_human = False
    context.semantic_artifacts.wallpaper_score = 0.94
    context.retrieval_artifacts.embedding = [0.1] * 1536

    entry = build_completed_index_entry(context=context, entry_id=1004)

    assert entry.unsplash_photo_id == "photo-4"
    assert entry.search_text == "night peak dark mountain stars wallpaper"
    assert entry.ai_caption == "A dark mountain under the stars, ideal for wallpaper."
    assert entry.wallpaper_score == 0.94
    assert entry.indexed_at is not None
