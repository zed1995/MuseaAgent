import logging

from backend.services.indexing.logging import IngestionRunResult

logger = logging.getLogger(__name__)


def run_cold_start_import(*, payloads: list[dict], pipeline) -> IngestionRunResult:
    succeeded = 0
    failed = 0
    for i, payload in enumerate(payloads):
        photo_id = payload.get("id", f"<index {i}>")
        try:
            pipeline.process_photo(payload)
            succeeded += 1
        except Exception as exc:
            logger.error("[cold-start] photo %s failed: %s", photo_id, exc)
            failed += 1
    return IngestionRunResult(
        trigger_type="cold_start",
        total_candidates=len(payloads),
        succeeded=succeeded,
        failed=failed,
    )


def run_incremental_sync(*, payloads: list[dict], pipeline) -> IngestionRunResult:
    succeeded = 0
    failed = 0
    for payload in payloads:
        try:
            pipeline.process_photo(payload)
            succeeded += 1
        except Exception:
            failed += 1
    return IngestionRunResult(
        trigger_type="incremental_sync",
        total_candidates=len(payloads),
        succeeded=succeeded,
        failed=failed,
    )
