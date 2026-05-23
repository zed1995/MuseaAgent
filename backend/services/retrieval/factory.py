from openai import OpenAI
from sqlalchemy.orm import Session

from backend.core.config import Settings
from backend.repositories.photo_index_repository import PhotoIndexRepository
from backend.services.retrieval.query_normalization import QueryNormalizationService
from backend.services.retrieval.rerank import RetrievalReranker
from backend.services.retrieval.service import RetrievalService


def build_query_translator(settings: Settings) -> callable:
    """Build a search-time query translator backed by OpenRouter.

    Returns a ``Callable[[str], str]`` that translates Chinese search
    queries into English keywords.  Uses the same model and API connection
    as the indexing-stage translation.
    """
    client = OpenAI(
        api_key=settings.indexing.openai_api_key,
        base_url=settings.indexing.openai_base_url,
    )
    model = settings.indexing.translation_model

    def _translate(text: str) -> str:
        resp = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": (
                    "Extract core search keywords from this Chinese photo query. "
                    "Output 1-3 space-separated English keywords only. "
                    "Do NOT include: photo, picture, image, wallpaper, "
                    "find, search, look, some, a, the, of, for, with.\n\n"
                    "Examples:\n"
                    "  海滩的图片  -> beach\n"
                    "  深色安静的壁纸 -> dark calm\n"
                    "  电影感城市夜景 -> city night cinematic\n"
                    "  极简山景锁屏 -> minimal mountain\n\n"
                    f"{text}"
                ),
            }],
            temperature=0,
        )
        return resp.choices[0].message.content or text

    return _translate


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
    translator = None
    if not settings.indexing.mock_translation:
        translator = build_query_translator(settings)

    if embedder is None:
        embedder = build_query_embedder(settings)

    return RetrievalService(
        repository=PhotoIndexRepository(session),
        normalizer=QueryNormalizationService(translator=translator),
        embedder=embedder,
        reranker=RetrievalReranker(),
        settings=settings.retrieval,
    )
