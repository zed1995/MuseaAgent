from dataclasses import dataclass, field

import pytest

from backend.services.indexing.scheduler import run_cold_start_import, run_incremental_sync


class FakePipeline:
    def __init__(self) -> None:
        self.processed_ids: list[str] = []
        self._raise_on: set[str] = set()

    def process_photo(self, payload: dict):
        photo_id = payload.get("id", "unknown")
        if photo_id in self._raise_on:
            raise RuntimeError(f"Fake error for {photo_id}")
        self.processed_ids.append(photo_id)


@pytest.fixture
def fake_pipeline():
    return FakePipeline()


def test_run_cold_start_import_processes_each_candidate_once(fake_pipeline) -> None:
    payloads = [{"id": "photo-1"}, {"id": "photo-2"}]

    result = run_cold_start_import(payloads=payloads, pipeline=fake_pipeline)

    assert result.total_candidates == 2
    assert result.succeeded == 2
    assert fake_pipeline.processed_ids == ["photo-1", "photo-2"]


def test_run_cold_start_import_counts_failures(fake_pipeline) -> None:
    fake_pipeline._raise_on.add("photo-2")
    payloads = [{"id": "photo-1"}, {"id": "photo-2"}, {"id": "photo-3"}]

    result = run_cold_start_import(payloads=payloads, pipeline=fake_pipeline)

    assert result.total_candidates == 3
    assert result.succeeded == 2
    assert result.failed == 1


def test_run_incremental_sync_processes_each_candidate_once(fake_pipeline) -> None:
    payloads = [{"id": "photo-1"}, {"id": "photo-2"}]

    result = run_incremental_sync(payloads=payloads, pipeline=fake_pipeline)

    assert result.total_candidates == 2
    assert result.succeeded == 2
    assert fake_pipeline.processed_ids == ["photo-1", "photo-2"]
