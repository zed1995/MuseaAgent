from abc import ABC, abstractmethod

from backend.services.indexing.contracts import SemanticArtifacts
from backend.services.indexing.provider_models import SemanticEnrichmentRequest


class SemanticEnricher(ABC):
    @abstractmethod
    def enrich(self, *, image_url: str, analysis_text: str, search_text: str) -> SemanticArtifacts: ...


class StubSemanticEnricher(SemanticEnricher):
    def enrich(self, *, image_url: str, analysis_text: str, search_text: str) -> SemanticArtifacts:
        request = SemanticEnrichmentRequest(
            image_url=image_url,
            analysis_text=analysis_text,
            search_text=search_text,
        )
        return SemanticArtifacts(
            ai_caption=f"A {request.search_text} scene.",
            ai_short_caption=request.search_text,
            scene_tags=["wallpaper", "scenic"],
            mood_tags=["calm"],
            style_tags=["minimal"],
            has_human=True if "person" in request.search_text.lower() or "human" in request.search_text.lower() else False,
            has_face=False,
        )


def build_semantic_enricher(settings) -> SemanticEnricher:
    return StubSemanticEnricher()
