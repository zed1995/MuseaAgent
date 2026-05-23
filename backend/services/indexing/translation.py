from abc import ABC, abstractmethod

from openai import OpenAI

from backend.services.indexing.provider_models import TranslationRequest, TranslationResponse

_TRANSLATION_PROMPT = (
    "You are a search-text normalization assistant. "
    "Transform the following photo description into clean, retrieval-friendly English search text. "
    "Preserve concrete scene terms, style terms, subject terms, and descriptive constraints "
    "that would help someone find this photo through search. "
    "Output only the normalized search text, nothing else.\n\n"
    "Input:\n{analysis_text}\n\n"
    "Output:"
)


class Translator(ABC):
    @abstractmethod
    def to_search_text(self, *, analysis_text: str) -> str: ...


class StubTranslator(Translator):
    def to_search_text(self, *, analysis_text: str) -> str:
        request = TranslationRequest(analysis_text=analysis_text)
        response = TranslationResponse(search_text=request.analysis_text.strip().lower())
        return response.search_text


class OpenAITranslator(Translator):
    def __init__(self, *, client: OpenAI, model: str) -> None:
        self._client = client
        self._model = model

    def to_search_text(self, *, analysis_text: str) -> str:
        request = TranslationRequest(analysis_text=analysis_text)
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": _TRANSLATION_PROMPT.format(analysis_text=request.analysis_text)}],
            temperature=0.3,
        )
        raw = response.choices[0].message.content or ""
        return TranslationResponse(search_text=raw.strip()).search_text


def build_translator(settings) -> Translator:
    if settings.mock_translation:
        return StubTranslator()
    client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    return OpenAITranslator(client=client, model=settings.translation_model)
