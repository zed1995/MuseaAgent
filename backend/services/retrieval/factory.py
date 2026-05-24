from openai import OpenAI
from sqlalchemy.orm import Session

from backend.core.config import Settings
from backend.repositories.photo_index_repository import PhotoIndexRepository
from backend.services.retrieval.rerank import RetrievalReranker
from backend.services.retrieval.service import RetrievalService
from backend.services.retrieval_preparation.rewrite import RetrievalRewriteService
from backend.services.retrieval_preparation.service import RetrievalPreparationService
from backend.services.retrieval_preparation.understanding import QueryUnderstandingService


def build_understanding_model_client(settings: Settings) -> callable:
    client = OpenAI(
        api_key=settings.indexing.openai_api_key,
        base_url=settings.indexing.openai_base_url,
    )
    model = settings.retrieval_preparation.understanding_model

    def _understand(query: str, mode: str) -> str:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a retrieval-understanding model. "
                        "Return exactly one JSON object and nothing else. "
                        "Do not wrap the JSON in markdown or code fences. "
                        "Do not add extra keys. "
                        "The only allowed top-level keys are: "
                        "raw_query, detected_language, inferred_mode, hard_filters, "
                        "negative_constraints, soft_preferences, subject_candidates, "
                        "scene_candidates, style_candidates, mood_candidates, "
                        "color_candidates, understanding_notes. "
                        "Allowed detected_language values: zh, en, mixed, unknown. "
                        "Allowed inferred_mode values: wallpaper, reference, generic. "
                        "Allowed hard_filters keys: orientation, has_human. "
                        "Allowed orientation values: portrait, landscape, squarish, null. "
                        "Allowed has_human values: true, false, null. "
                        "Allowed negative_constraints keys: exclude_people, exclude_faces. "
                        "Allowed soft_preferences keys: moods, styles, scenes, subjects, lighting, colors, qualities. "
                        "All candidate and preference fields must be arrays of short English strings. "
                        "All retrieval-facing semantic fields must be in English, even when the user query is Chinese. "
                        "Do not output Chinese inside soft_preferences, subject_candidates, scene_candidates, style_candidates, mood_candidates, or color_candidates. "
                        "Even when there is only one item, you must still return a JSON array, never a bare string. "
                        "understanding_notes must always be a JSON array of strings, never a bare string. "
                        "If the mode hint is auto, still choose one of wallpaper, reference, generic for inferred_mode."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Return a JSON object matching this schema exactly:\n"
                        "{"
                        "\"raw_query\": string, "
                        "\"detected_language\": \"zh\"|\"en\"|\"mixed\"|\"unknown\", "
                        "\"inferred_mode\": \"wallpaper\"|\"reference\"|\"generic\", "
                        "\"hard_filters\": {\"orientation\": \"portrait\"|\"landscape\"|\"squarish\"|null, \"has_human\": true|false|null}, "
                        "\"negative_constraints\": {\"exclude_people\": boolean, \"exclude_faces\": boolean}, "
                        "\"soft_preferences\": {\"moods\": string[], \"styles\": string[], \"scenes\": string[], \"subjects\": string[], \"lighting\": string[], \"colors\": string[], \"qualities\": string[]}, "
                        "\"subject_candidates\": string[], "
                        "\"scene_candidates\": string[], "
                        "\"style_candidates\": string[], "
                        "\"mood_candidates\": string[], "
                        "\"color_candidates\": string[], "
                        "\"understanding_notes\": string[]"
                        "}\n"
                        "Important formatting rules:\n"
                        "- Any field declared as string[] must always be a JSON array, even when it contains only one item.\n"
                        "- Never return a bare string for subject_candidates, scene_candidates, style_candidates, mood_candidates, color_candidates, or understanding_notes.\n"
                        "- All semantic values except raw_query must be in English.\n"
                        "- Translate Chinese retrieval concepts into concise English retrieval terms.\n"
                        f"Mode hint: {mode}\n"
                        f"Query: {query}"
                    ),
                },
            ],
            temperature=0,
        )
        return resp.choices[0].message.content or "{}"

    return _understand


def build_rewrite_model_client(settings: Settings) -> callable:
    client = OpenAI(
        api_key=settings.indexing.openai_api_key,
        base_url=settings.indexing.openai_base_url,
    )
    model = settings.retrieval_preparation.rewrite_model

    def _rewrite(understanding) -> str:
        resp = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": (
                    "You receive a structured retrieval understanding object. "
                    "Return JSON only with keys rewrite_for_embedding, rewrite_for_fts, "
                    "lexical_terms, user_explicit_terms, expansion_terms, negative_terms, rewrite_notes. "
                    "user_explicit_terms must contain only concepts explicitly requested by the user. "
                    "expansion_terms may contain model-added supporting terms, but they must not repeat user_explicit_terms. "
                    "All retrieval-facing fields must be English-only, even when the user query is Chinese. "
                    "Never output Chinese in rewrite_for_embedding, rewrite_for_fts, lexical_terms, user_explicit_terms, expansion_terms, or negative_terms. "
                    "rewrite_for_fts must be explicit-only lexical text built from user_explicit_terms, "
                    "negative_terms, and hard-filter lexical terms only. "
                    "Do not include expansion_terms in rewrite_for_fts. "
                    "rewrite_for_embedding may include expansion_terms. "
                    "lexical_terms, user_explicit_terms, expansion_terms, negative_terms, and rewrite_notes must always be JSON arrays, "
                    "even when there is only one item. Never return a bare string for those fields.\n"
                    f"{understanding.model_dump_json()}"
                ),
            }],
            temperature=0,
        )
        return resp.choices[0].message.content or "{}"

    return _rewrite


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

    understanding_client = None
    rewrite_client = None
    if (
        not settings.indexing.mock_translation
        and settings.retrieval_preparation.use_model_understanding
    ):
        understanding_client = build_understanding_model_client(settings)
    if (
        not settings.indexing.mock_translation
        and settings.retrieval_preparation.use_model_rewrite
    ):
        rewrite_client = build_rewrite_model_client(settings)

    if settings.retrieval_preparation.use_model_understanding and understanding_client is None:
        raise RuntimeError(
            "model-backed understanding is required but no understanding model client is configured"
        )

    preparation_service = RetrievalPreparationService(
        understanding_service=QueryUnderstandingService(model_client=understanding_client),
        rewrite_service=RetrievalRewriteService(model_client=rewrite_client),
    )

    return RetrievalService(
        repository=PhotoIndexRepository(session),
        preparation_service=preparation_service,
        embedder=embedder,
        reranker=RetrievalReranker(),
        settings=settings.retrieval,
    )
