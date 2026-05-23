from backend.repositories.records import PhotoIndexRecord


def test_photo_index_record_keeps_persistence_boundary_clean() -> None:
    record = PhotoIndexRecord(
        id=123,
        source="unsplash",
        unsplash_photo_id="abc",
        unsplash_user_id=None,
        orientation="portrait",
        source_text="原始文本",
        search_text="calm dark wallpaper",
        index_status="indexed",
    )

    assert record.unsplash_photo_id == "abc"
    assert record.search_text == "calm dark wallpaper"
