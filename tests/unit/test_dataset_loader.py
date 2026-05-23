from backend.services.indexing.dataset_loader import parse_unsplash_dataset


def test_parse_unsplash_dataset_reads_csv(tmp_path) -> None:
    csv_file = tmp_path / "photos.csv"
    csv_file.write_text(
        "photo_id\tphoto_image_url\tphoto_width\tphoto_height\tphoto_description\tai_description\tphotographer_username\n"
        "abc123\thttps://example.com/1.jpg\t1920\t1080\tMountain view\tSnowy mountain\tphotog1\n"
        "def456\thttps://example.com/2.jpg\t800\t600\t\tCity street\tphotog2\n"
    )

    payloads = parse_unsplash_dataset(str(csv_file))

    assert len(payloads) == 2

    assert payloads[0]["id"] == "abc123"
    assert payloads[0]["urls"]["regular"] == "https://example.com/1.jpg"
    assert payloads[0]["width"] == 1920
    assert payloads[0]["height"] == 1080
    assert payloads[0]["description"] == "Mountain view"
    assert payloads[0]["alt_description"] == "Snowy mountain"
    assert payloads[0]["user"]["id"] == "photog1"

    assert payloads[1]["id"] == "def456"
    assert payloads[1]["description"] is None
    assert payloads[1]["alt_description"] == "City street"


def test_parse_unsplash_dataset_respects_max_rows(tmp_path) -> None:
    csv_file = tmp_path / "photos.csv"
    lines = ["photo_id\tphoto_image_url\tphoto_width\tphoto_height"]
    lines.extend(f"photo-{i}\thttps://example.com/{i}.jpg\t100\t100" for i in range(10))
    csv_file.write_text("\n".join(lines))

    payloads = parse_unsplash_dataset(str(csv_file), max_rows=3)

    assert len(payloads) == 3
    assert payloads[0]["id"] == "photo-0"
    assert payloads[2]["id"] == "photo-2"
