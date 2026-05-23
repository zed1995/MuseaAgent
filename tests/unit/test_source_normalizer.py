from backend.services.indexing.source_normalizer import normalize_unsplash_photo


def test_normalize_unsplash_photo_extracts_required_fields() -> None:
    payload = {
        "id": "photo-1",
        "user": {"id": "user-1"},
        "description": "Snow mountains at dusk",
        "alt_description": "Snowy mountain landscape",
        "width": 1920,
        "height": 1080,
        "urls": {"regular": "https://images.example/photo-1.jpg"},
    }

    normalized = normalize_unsplash_photo(payload)

    assert normalized.unsplash_photo_id == "photo-1"
    assert normalized.unsplash_user_id == "user-1"
    assert normalized.orientation == "landscape"
    assert normalized.regular_url == "https://images.example/photo-1.jpg"


def test_normalize_unsplash_photo_handles_portrait_orientation() -> None:
    payload = {
        "id": "photo-2",
        "user": {"id": "user-2"},
        "description": "Vertical mountain shot",
        "width": 1080,
        "height": 1920,
        "urls": {"regular": "https://images.example/photo-2.jpg"},
    }

    normalized = normalize_unsplash_photo(payload)

    assert normalized.orientation == "portrait"


def test_normalize_unsplash_photo_handles_missing_optional_fields() -> None:
    payload = {
        "id": "photo-3",
        "user": None,
        "urls": {"regular": "https://images.example/photo-3.jpg"},
    }

    normalized = normalize_unsplash_photo(payload)

    assert normalized.unsplash_photo_id == "photo-3"
    assert normalized.unsplash_user_id is None
    assert normalized.raw_title is None
    assert normalized.orientation is None
    assert normalized.width is None
