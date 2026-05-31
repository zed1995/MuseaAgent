from backend.core.id_generator import IdGenerator
from backend.repositories.photo_index_repository import PhotoIndexRepository
from backend.services.indexing.embedding import build_embedder
from backend.services.indexing.pipeline import IndexingPipeline
from backend.services.indexing.scoring import build_scorer
from backend.services.indexing.semantic_enrichment import build_semantic_enricher
from backend.services.indexing.translation import build_translator


def build_indexing_pipeline(*, session_factory, settings):
    # The producer side is intentionally assembled once per request/sync run so
    # translation, enrichment, scoring, embedding, and persistence share one
    # consistent pipeline boundary.
    session = session_factory()
    repository = PhotoIndexRepository(session)

    return IndexingPipeline(
        id_generator=IdGenerator(machine_id=1),
        translator=build_translator(settings.indexing),
        enricher=build_semantic_enricher(settings.indexing),
        scorer=build_scorer(),
        embedder=build_embedder(settings.indexing),
        repository=repository,
    )
