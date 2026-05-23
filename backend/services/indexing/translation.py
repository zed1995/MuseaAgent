from abc import ABC, abstractmethod

from openai import OpenAI

from backend.services.indexing.provider_models import TranslationRequest, TranslationResponse

_TRANSLATION_PROMPT = (
    "You generate English keyword search text for a photo search engine. "
    "The keywords will be matched against user search queries via PostgreSQL full-text search, "
    "so every distinct concept must appear as a separate space-separated keyword.\n\n"
    "Rules:\n"
    "- Output 5-15 English keywords only, space-separated, one line.\n"
    "- Include: subjects, scene type, style, mood, lighting, colors, composition, orientation.\n"
    "- Include common synonyms and related search terms that a Chinese user might type.\n"
    "- Use US English spelling.\n"
    "- Do NOT include: articles (a, an, the), prepositions (of, in, on, at, for, with, to), "
    "filler verbs (is, are, was, were, has, have, been, being, showing, featuring).\n"
    "- Do NOT output explanations, labels, or punctuation.\n\n"
    "Examples:\n"
    "  Input: A serene beach at sunset with calm waves and golden sky\n"
    "  Output: beach sunset calm waves golden sky serene ocean shore coastline evening peaceful\n\n"
    "  Input: Minimalist dark interior with soft lighting and wooden furniture\n"
    "  Output: dark minimalist interior soft lighting wood furniture cozy calm evening\n\n"
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
            temperature=0,
        )
        raw = response.choices[0].message.content or ""
        return TranslationResponse(search_text=raw.strip()).search_text


def build_translator(settings) -> Translator:
    if settings.mock_translation:
        return StubTranslator()
    client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    return OpenAITranslator(client=client, model=settings.translation_model)
