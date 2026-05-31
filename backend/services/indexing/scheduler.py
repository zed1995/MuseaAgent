import logging

from backend.services.indexing.logging import IngestionRunResult

logger = logging.getLogger(__name__)


def run_cold_start_import(*, payloads: list[dict], pipeline) -> IngestionRunResult:
    # Cold start favors observability over throughput because it is primarily
    # used to bootstrap and verify a large corpus import from scratch.
    succeeded = 0
    failed = 0
    for i, payload in enumerate(payloads):
        photo_id = payload.get("id", f"<index {i}>")
        try:
            entry = pipeline.process_photo(payload)
            succeeded += 1
            logger.info(
                "[cold-start] [%d/%d] photo %s indexed — search_text=%r orientation=%s",
                i + 1, len(payloads), photo_id,
                getattr(entry, "search_text", ""),
                getattr(entry, "orientation", "?"),
            )
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
    # Incremental sync reuses the same producer pipeline but reports only the
    # coarse sync outcome so it can be driven as a lightweight background job.
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
