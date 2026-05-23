from sqlalchemy.orm import Session

from backend.core.config import Settings
from backend.repositories.photo_index_repository import PhotoIndexRepository
from backend.services.retrieval.query_normalization import QueryNormalizationService
from backend.services.retrieval.rerank import RetrievalReranker
from backend.services.retrieval.service import RetrievalService


def build_retrieval_service(
    session: Session,
    settings: Settings,
    embedder: callable,
) -> RetrievalService:
    """Build a fully wired RetrievalService.

    The embedder callable must accept a text string and return
    a 1536-dimensional embedding vector. The caller is responsible
    for providing this since Phase 4 does not own the embedding
    infrastructure.
    """
    return RetrievalService(
        repository=PhotoIndexRepository(session),
        normalizer=QueryNormalizationService(),
        embedder=embedder,
        reranker=RetrievalReranker(),
        settings=settings.retrieval,
    )
