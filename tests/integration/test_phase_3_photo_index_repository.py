from datetime import UTC, datetime

from backend.repositories.photo_index_repository import PhotoIndexRepository
from backend.repositories.write_models import PhotoIndexWriteModel


def test_upsert_index_entry_persists_phase_3_completed_fields(session) -> None:
    repository = PhotoIndexRepository(session)

    repository.upsert_index_entry(
        PhotoIndexWriteModel(
            id=1001,
            unsplash_photo_id="photo-1",
            unsplash_user_id="user-1",
            orientation="landscape",
            source_text="raw source text",
            search_text="dark minimal wallpaper",
            ai_caption="A dark and minimal mountain wallpaper.",
            ai_short_caption="Dark mountain wallpaper",
            scene_tags=["mountain", "night"],
            mood_tags=["calm"],
            style_tags=["minimal"],
            composition_tags=["wide"],
            lighting_tags=["low-light"],
            color_tags=["black", "blue"],
            subject_tags=["mountain"],
            use_case_tags=["wallpaper"],
            dominant_colors=["#000000", "#1d3557"],
            has_human=False,
            has_face=False,
            is_abstract=False,
            is_minimal=True,
            is_dark=True,
            wallpaper_score=0.94,
            photography_reference_score=0.51,
            embedding=[0.1] * 1536,
            indexed_at=datetime.now(UTC),
        )
    )
    session.commit()

    stored = repository.get_by_unsplash_photo_id("photo-1")

    assert stored is not None
    assert stored.ai_caption == "A dark and minimal mountain wallpaper."
    assert stored.scene_tags == ["mountain", "night"]
    assert stored.wallpaper_score == 0.94
    assert stored.indexed_at is not None
