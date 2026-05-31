from langchain_core.language_models.chat_models import BaseChatModel

from backend.llm.providers.gemini import GeminiChatModelProvider
from backend.llm.providers.openai import OpenAIChatModelProvider
from backend.llm.providers.openrouter import OpenRouterChatModelProvider


def build_chat_model(
    *,
    capability: str,
    provider_name: str,
    model_name: str,
    api_key: str,
    base_url: str = "",
) -> BaseChatModel:
    del capability

    provider_map = {
        "openai": OpenAIChatModelProvider(),
        "gemini": GeminiChatModelProvider(),
        "openrouter": OpenRouterChatModelProvider(),
    }
    if provider_name not in provider_map:
        raise ValueError(f"unsupported provider: {provider_name}")

    return provider_map[provider_name].build(
        model_name=model_name,
        api_key=api_key,
        base_url=base_url or None,
    )
