from abc import ABC, abstractmethod

from backend.services.indexing.provider_models import TranslationRequest, TranslationResponse


class Translator(ABC):
    @abstractmethod
    def to_search_text(self, *, analysis_text: str) -> str: ...


class StubTranslator(Translator):
    def to_search_text(self, *, analysis_text: str) -> str:
        request = TranslationRequest(analysis_text=analysis_text)
        response = TranslationResponse(search_text=request.analysis_text.strip().lower())
        return response.search_text


def build_translator(settings) -> Translator:
    return StubTranslator()
