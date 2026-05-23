"""Cold start: import Unsplash dataset photos into the index at app startup."""

_DATASET_PATH = "data/unsplash-research-dataset-lite-latest/photos.csv000"
_MAX_ROWS = 5  # bump or set to None after testing


def run_cold_start() -> None:
    """Load the Unsplash dataset and run the indexing pipeline.

    Call this at application startup.  Increase ``_MAX_ROWS`` once verified,
    or set to ``None`` to process the full 25k dataset.  Remove the call
    entirely once cold start is complete.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from backend.core.config import get_settings
    from backend.services.indexing.dataset_loader import parse_unsplash_dataset
    from backend.services.indexing.factory import build_indexing_pipeline
    from backend.services.indexing.scheduler import run_cold_start_import

    payloads = parse_unsplash_dataset(_DATASET_PATH, max_rows=_MAX_ROWS)
    if not payloads:
        return

    settings = get_settings()
    engine = create_engine(settings.database.url)
    sf = sessionmaker(bind=engine)
    pipeline = build_indexing_pipeline(session_factory=sf, settings=settings)
    result = run_cold_start_import(payloads=payloads, pipeline=pipeline)
    pipeline.commit()
    print(f"[cold-start] imported {result.succeeded}/{result.total_candidates} photos "
          f"({result.failed} failed)")
    engine.dispose()
