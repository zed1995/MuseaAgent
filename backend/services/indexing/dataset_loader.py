import csv


def parse_unsplash_dataset(csv_path: str, max_rows: int | None = None) -> list[dict]:
    """Read Unsplash dataset CSV and yield photo payloads for the indexing pipeline.

    CSV columns are tab-separated. Maps CSV fields to the dict format expected
    by ``normalize_unsplash_photo``:

    - ``photo_id`` → ``id``
    - ``photo_image_url`` → ``urls.regular``
    - ``photo_description`` → ``description`` (falls back to ``ai_description``)
    - ``ai_description`` → ``alt_description``
    - ``width``/``height`` → as-is
    - ``photographer_username`` → ``user.id``

    Args:
        csv_path: Path to the ``photos.csv000`` file.
        max_rows: Maximum number of rows to return. ``None`` means all rows.

    Returns:
        List of payload dicts ready for ``normalize_unsplash_photo``.
    """
    payloads: list[dict] = []

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for i, row in enumerate(reader):
            if max_rows is not None and i >= max_rows:
                break

            description = (row.get("photo_description") or "").strip() or None
            alt_description = (row.get("ai_description") or "").strip() or None

            payloads.append(
                {
                    "id": row["photo_id"],
                    "user": {"id": row.get("photographer_username") or ""},
                    "width": _int_or_none(row.get("photo_width")),
                    "height": _int_or_none(row.get("photo_height")),
                    "urls": {"regular": row.get("photo_image_url", "")},
                    "description": description,
                    "alt_description": alt_description,
                }
            )

    return payloads


def _int_or_none(value: str | None) -> int | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return int(stripped)
    except ValueError:
        return None
