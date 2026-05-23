from backend.services.indexing.logging import IngestionRunResult


def run_cold_start_import(*, payloads: list[dict], pipeline) -> IngestionRunResult:
    succeeded = 0
    failed = 0
    for payload in payloads:
        try:
            pipeline.process_photo(payload)
            succeeded += 1
        except Exception:
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
