from backend.services.indexing.contracts import NormalizedSourcePhoto


def normalize_unsplash_photo(payload: dict) -> NormalizedSourcePhoto:
    width = payload.get("width")
    height = payload.get("height")
    orientation = None
    if width and height:
        orientation = "landscape" if width >= height else "portrait"

    user = payload.get("user") or {}

    return NormalizedSourcePhoto(
        unsplash_photo_id=payload["id"],
        unsplash_user_id=user.get("id") if user else None,
        raw_title=payload.get("title"),
        raw_description=payload.get("description"),
        raw_alt_description=payload.get("alt_description"),
        orientation=orientation,
        width=width,
        height=height,
        regular_url=payload["urls"]["regular"],
    )
