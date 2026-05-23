from backend.services.indexing.contracts import NormalizedSourcePhoto
from backend.services.indexing.text_assembly import assemble_text_artifacts


def test_assemble_text_artifacts_combines_available_source_fields() -> None:
    normalized = NormalizedSourcePhoto(
        unsplash_photo_id="photo-1",
        unsplash_user_id="user-1",
        raw_title="Night peak",
        raw_description="A dark mountain under the stars",
        raw_alt_description="Dark mountain wallpaper",
        orientation="landscape",
        width=1920,
        height=1080,
        regular_url="https://images.example/photo-1.jpg",
    )

    artifacts = assemble_text_artifacts(normalized)

    assert artifacts.source_text == "Night peak\nA dark mountain under the stars\nDark mountain wallpaper"
    assert artifacts.analysis_text is not None


def test_assemble_text_artifacts_handles_missing_all_fields() -> None:
    normalized = NormalizedSourcePhoto(
        unsplash_photo_id="photo-2",
        unsplash_user_id=None,
        raw_title=None,
        raw_description=None,
        raw_alt_description=None,
        orientation="landscape",
        width=1920,
        height=1080,
        regular_url="https://images.example/photo-2.jpg",
    )

    artifacts = assemble_text_artifacts(normalized)

    assert artifacts.source_text == "unsplash:photo-2"
    assert artifacts.analysis_text == "unsplash:photo-2"


def test_assemble_text_artifacts_skips_empty_fragments() -> None:
    normalized = NormalizedSourcePhoto(
        unsplash_photo_id="photo-3",
        unsplash_user_id=None,
        raw_title=None,
        raw_description="  ",
        raw_alt_description="Valid alt text",
        orientation="landscape",
        width=1920,
        height=1080,
        regular_url="https://images.example/photo-3.jpg",
    )

    artifacts = assemble_text_artifacts(normalized)

    assert artifacts.source_text == "Valid alt text"
