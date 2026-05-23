from dataclasses import dataclass


@dataclass(slots=True)
class TranslationRequest:
    analysis_text: str


@dataclass(slots=True)
class TranslationResponse:
    search_text: str


@dataclass(slots=True)
class SemanticEnrichmentRequest:
    image_url: str
    analysis_text: str
    search_text: str


@dataclass(slots=True)
class EmbeddingRequest:
    search_text: str
    caption: str
    tags: list[str]
