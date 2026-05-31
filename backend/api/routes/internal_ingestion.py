from fastapi import APIRouter, Depends

from backend.schemas.internal_ingestion import InternalBatchIngestionRequest, InternalSinglePhotoRequest
from backend.services.indexing.factory import build_indexing_pipeline
from backend.services.indexing.scheduler import run_incremental_sync

router = APIRouter(prefix="/internal/ingestion", tags=["internal-ingestion"])


@router.post("/photo")
def ingest_single_photo(request: InternalSinglePhotoRequest, pipeline=Depends(build_indexing_pipeline)):
    # Single-photo ingestion is the narrowest producer entrypoint and is useful
    # for verifying the full indexing pipeline against one raw upstream payload.
    return pipeline.process_photo(request.payload)


@router.post("/incremental-sync")
def start_incremental_sync(request: InternalBatchIngestionRequest, pipeline=Depends(build_indexing_pipeline)):
    # Batch sync reuses the same producer pipeline but keeps commit control in
    # the scheduler so a whole sync run can be processed as one ingestion job.
    return run_incremental_sync(payloads=request.payloads, pipeline=pipeline)
