from typing import Protocol

from langchain_core.language_models.chat_models import BaseChatModel


class ChatModelProvider(Protocol):
    def build(
        self,
        *,
        model_name: str,
        api_key: str,
        base_url: str | None = None,
    ) -> BaseChatModel:
        """Construct a LangChain chat model."""
