from fastapi import APIRouter, Depends

from backend.schemas.internal_ingestion import InternalBatchIngestionRequest, InternalSinglePhotoRequest
from backend.services.indexing.factory import build_indexing_pipeline
from backend.services.indexing.scheduler import run_cold_start_import, run_incremental_sync

router = APIRouter(prefix="/internal/ingestion", tags=["internal-ingestion"])


@router.post("/photo")
def ingest_single_photo(request: InternalSinglePhotoRequest, pipeline=Depends(build_indexing_pipeline)):
    return pipeline.process_photo(request.payload)


@router.post("/cold-start")
def start_cold_start(request: InternalBatchIngestionRequest, pipeline=Depends(build_indexing_pipeline)):
    return run_cold_start_import(payloads=request.payloads, pipeline=pipeline)


@router.post("/incremental-sync")
def start_incremental_sync(request: InternalBatchIngestionRequest, pipeline=Depends(build_indexing_pipeline)):
    return run_incremental_sync(payloads=request.payloads, pipeline=pipeline)
