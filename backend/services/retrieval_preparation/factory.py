from backend.core.config import Settings
from backend.services.retrieval.factory import (
    build_rewrite_model_client,
    build_understanding_model_client,
)
from backend.services.retrieval_preparation.rewrite import RetrievalRewriteService
from backend.services.retrieval_preparation.service import RetrievalPreparationService
from backend.services.retrieval_preparation.understanding import QueryUnderstandingService


def build_retrieval_preparation_service(settings: Settings) -> RetrievalPreparationService:
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

    return RetrievalPreparationService(
        understanding_service=QueryUnderstandingService(model_client=understanding_client),
        rewrite_service=RetrievalRewriteService(model_client=rewrite_client),
    )
