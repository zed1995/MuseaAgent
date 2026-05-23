from abc import ABC, abstractmethod

from openai import OpenAI

from backend.services.indexing.provider_models import EmbeddingRequest


class Embedder(ABC):
    @abstractmethod
    def embed(self, *, search_text: str, caption: str, tags: list[str]) -> list[float]: ...


class StubEmbedder(Embedder):
    def embed(self, *, search_text: str, caption: str, tags: list[str]) -> list[float]:
        _ = EmbeddingRequest(search_text=search_text, caption=caption, tags=tags)
        return [0.1] * 1536


class OpenAIEmbedder(Embedder):
    def __init__(self, *, client: OpenAI, model: str) -> None:
        self._client = client
        self._model = model

    def embed(self, *, search_text: str, caption: str, tags: list[str]) -> list[float]:
        request = EmbeddingRequest(search_text=search_text, caption=caption, tags=tags)
        tag_str = ", ".join(tags) if tags else ""
        parts = [request.search_text, request.caption]
        if tag_str:
            parts.append(tag_str)
        input_text = ". ".join(parts)

        response = self._client.embeddings.create(
            model=self._model,
            input=input_text,
        )
        return response.data[0].embedding


def build_embedder(settings) -> Embedder:
    if settings.mock_embedding:
        return StubEmbedder()
    client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    return OpenAIEmbedder(client=client, model=settings.embedding_model)
