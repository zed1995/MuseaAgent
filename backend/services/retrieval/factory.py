from openai import OpenAI
from sqlalchemy.orm import Session

from backend.core.config import Settings
from backend.repositories.photo_index_repository import PhotoIndexRepository
from backend.services.retrieval.rerank import RetrievalReranker
from backend.services.retrieval.service import RetrievalService
from backend.services.retrieval_preparation.factory import build_retrieval_preparation_service


def build_query_embedder(settings: Settings) -> callable:
    """Build a search-time query embedder from application settings.

    Returns a ``Callable[[str], list[float]]`` that embeds arbitrary text
    into a 1536-dimensional vector.  Uses the same model and API connection
    as the indexing-stage embedder.
    """
    if settings.indexing.mock_embedding:
        return lambda text: [0.0] * 1536

    api_key = settings.indexing.embedding_api_key or settings.indexing.openai_api_key
    base_url = settings.indexing.embedding_base_url or settings.indexing.openai_base_url
    client = OpenAI(api_key=api_key, base_url=base_url)
    model = settings.indexing.embedding_model

    def _embed(text: str) -> list[float]:
        resp = client.embeddings.create(model=model, input=text)
        return resp.data[0].embedding

    return _embed


def build_retrieval_service(
    session: Session,
    settings: Settings,
    embedder: callable | None = None,
) -> RetrievalService:
    """Build a fully wired RetrievalService.

    Parameters
    ----------
    session:
        Active SQLAlchemy session.
    settings:
        Application settings (reads retrieval + indexing config).
    embedder:
        Optional ``Callable[[str], list[float]]``.  When omitted
        (or ``None``) the embedder is auto-built from
        ``settings.indexing`` (respecting ``mock_embedding``).
    """
    if embedder is None:
        embedder = build_query_embedder(settings)
    # Retrieval is assembled from three concerns: preparation, repository
    # access, and deterministic reranking. The agent graph consumes this as an
    # execution capability rather than reimplementing retrieval internally.
    preparation_service = build_retrieval_preparation_service(settings)

    return RetrievalService(
        repository=PhotoIndexRepository(session),
        preparation_service=preparation_service,
        embedder=embedder,
        reranker=RetrievalReranker(),
        settings=settings.retrieval,
    )
