from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI


class OpenRouterChatModelProvider:
    def build(
        self,
        *,
        model_name: str,
        api_key: str,
        base_url: str | None = None,
    ) -> BaseChatModel:
        return ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=base_url or "https://openrouter.ai/api/v1",
            temperature=0,
        )
