from abc import ABC, abstractmethod

from backend.services.indexing.provider_models import EmbeddingRequest


class Embedder(ABC):
    @abstractmethod
    def embed(self, *, search_text: str, caption: str, tags: list[str]) -> list[float]: ...


class StubEmbedder(Embedder):
    def embed(self, *, search_text: str, caption: str, tags: list[str]) -> list[float]:
        _ = EmbeddingRequest(search_text=search_text, caption=caption, tags=tags)
        return [0.1] * 1536


def build_embedder(settings) -> Embedder:
    return StubEmbedder()
