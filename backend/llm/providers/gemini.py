from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI


class GeminiChatModelProvider:
    def build(
        self,
        *,
        model_name: str,
        api_key: str,
        base_url: str | None = None,
    ) -> BaseChatModel:
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=0,
        )
