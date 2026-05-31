from backend.core.config import Settings
from backend.llm.chains.retrieval_rewrite_chain import RetrievalRewriteChain
from backend.llm.chains.retrieval_understanding_chain import RetrievalUnderstandingChain
from backend.llm.providers.factory import build_chat_model
from backend.services.retrieval_preparation.rewrite import RetrievalRewriteService
from backend.services.retrieval_preparation.service import RetrievalPreparationService
from backend.services.retrieval_preparation.understanding import QueryUnderstandingService


def build_retrieval_preparation_service(settings: Settings) -> RetrievalPreparationService:
    understanding_chain = None
    rewrite_chain = None

    if (
        not settings.indexing.mock_translation
        and settings.retrieval_preparation.use_model_understanding
    ):
        understanding_config = settings.llm.understanding
        understanding_chain = RetrievalUnderstandingChain(
            build_chat_model(
                capability="understanding",
                provider_name=understanding_config.provider,
                model_name=understanding_config.model,
                api_key=understanding_config.api_key,
                base_url=understanding_config.base_url,
            )
        )
    if (
        not settings.indexing.mock_translation
        and settings.retrieval_preparation.use_model_rewrite
    ):
        rewrite_config = settings.llm.rewrite
        rewrite_chain = RetrievalRewriteChain(
            build_chat_model(
                capability="rewrite",
                provider_name=rewrite_config.provider,
                model_name=rewrite_config.model,
                api_key=rewrite_config.api_key,
                base_url=rewrite_config.base_url,
            )
        )

    return RetrievalPreparationService(
        understanding_service=QueryUnderstandingService(chain=understanding_chain),
        rewrite_service=RetrievalRewriteService(chain=rewrite_chain),
    )
