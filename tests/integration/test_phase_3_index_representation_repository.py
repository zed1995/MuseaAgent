from datetime import UTC, datetime

from backend.repositories.photo_index_repository import PhotoIndexRepository
from backend.repositories.write_models import PhotoIndexWriteModel


def test_repository_persists_phase_3_representation_fields(session) -> None:
    repository = PhotoIndexRepository(session)

    repository.upsert_index_entry(
        PhotoIndexWriteModel(
            id=3101,
            unsplash_photo_id="rep-photo-1",
            unsplash_user_id="user-1",
            orientation="portrait",
            source_text="quiet dark mountain wallpaper",
            search_text="dark mountain wallpaper quiet minimal",
            ai_caption="A quiet dark mountain wallpaper with minimal composition.",
            ai_short_caption="Dark mountain wallpaper",
            retrieval_caption_text=(
                "Dark mountain wallpaper. A quiet dark mountain wallpaper with minimal composition."
            ),
            retrieval_tag_text="mountain quiet minimal negative space low light dark blue wallpaper",
            retrieval_document_text=(
                "Dark mountain wallpaper. A quiet dark mountain wallpaper with minimal composition. "
                "mountain quiet minimal negative space low light dark blue wallpaper."
            ),
            embedding_text=(
                "Dark mountain wallpaper. A quiet dark mountain wallpaper with minimal composition. "
                "mountain quiet minimal negative space low light dark blue wallpaper."
            ),
            scene_tags=["mountain"],
            mood_tags=["quiet"],
            style_tags=["minimal"],
            composition_tags=["negative space"],
            lighting_tags=["low light"],
            color_tags=["dark blue"],
            subject_tags=["mountain"],
            use_case_tags=["wallpaper"],
            dominant_colors=["#111111", "#203040"],
            has_human=False,
            has_face=False,
            is_abstract=False,
            is_minimal=True,
            is_dark=True,
            wallpaper_score=0.95,
            photography_reference_score=0.42,
            embedding=[0.1] * 1536,
            indexed_at=datetime.now(UTC),
        )
    )
    session.commit()

    stored = repository.get_by_unsplash_photo_id("rep-photo-1")

    assert stored is not None
    assert stored.retrieval_caption_text.startswith("Dark mountain wallpaper")
    assert "negative space" in stored.retrieval_tag_text
    assert stored.embedding_text == stored.retrieval_document_text
