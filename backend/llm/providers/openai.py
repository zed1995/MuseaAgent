from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel


class OpenAIChatModelProvider:
    def build(
        self,
        *,
        model_name: str,
        api_key: str,
        base_url: str | None = None,
    ) -> BaseChatModel:
        kwargs = {
            "model": model_name,
            "api_key": api_key,
            "temperature": 0,
        }
        if base_url:
            kwargs["base_url"] = base_url
        return ChatOpenAI(**kwargs)
