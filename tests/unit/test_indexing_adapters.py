"""Tests for indexing model adapters — stubs vs real OpenAI implementations."""

from unittest.mock import MagicMock, sentinel

from backend.services.indexing.embedding import StubEmbedder, build_embedder
from backend.services.indexing.semantic_enrichment import StubSemanticEnricher, build_semantic_enricher
from backend.services.indexing.translation import StubTranslator, build_translator


BIG_SENTINEL = sentinel


def test_build_translator_returns_stub_when_mock_true() -> None:
    settings = MockIndexingSettings(mock_translation=True)
    translator = build_translator(settings)
    assert isinstance(translator, StubTranslator)


def test_build_semantic_enricher_returns_stub_when_mock_true() -> None:
    settings = MockIndexingSettings(mock_enrichment=True)
    enricher = build_semantic_enricher(settings)
    assert isinstance(enricher, StubSemanticEnricher)


def test_build_embedder_returns_stub_when_mock_true() -> None:
    settings = MockIndexingSettings(mock_embedding=True)
    embedder = build_embedder(settings)
    assert isinstance(embedder, StubEmbedder)


# --- Real adapter behaviour tests (with fake OpenAI client) -------------------

def _make_fake_client(response_factory):
    """Return an OpenAI-client-shaped object with a configurable completion."""
    client = MagicMock()
    client.chat.completions.create = MagicMock(side_effect=response_factory)
    return client


def test_openai_translator_lowercases_and_returns_text() -> None:
    from backend.services.indexing.translation import OpenAITranslator

    def fake_create(*args, **kwargs):
        msg = MagicMock()
        msg.content = "  quiet dark mountain wallpaper  "
        choice = MagicMock()
        choice.message = msg
        result = MagicMock()
        result.choices = [choice]
        return result

    client = _make_fake_client(fake_create)
    translator = OpenAITranslator(client=client, model="gpt-4o-mini")

    result = translator.to_search_text(analysis_text="  Quiet Dark Mountain Wallpaper  ")

    assert result == "quiet dark mountain wallpaper"


def test_openai_semantic_enricher_parses_json_response() -> None:
    from backend.services.indexing.semantic_enrichment import OpenAISemanticEnricher

    def fake_create(*args, **kwargs):
        msg = MagicMock()
        msg.content = (
            '{"ai_caption": "A dark mountain under stars.",'
            '"ai_short_caption": "Dark mountain",'
            '"scene_tags": ["mountain", "night"],'
            '"mood_tags": ["calm"],'
            '"style_tags": ["minimal"],'
            '"composition_tags": ["wide"],'
            '"lighting_tags": ["low-light"],'
            '"color_tags": ["black"],'
            '"subject_tags": ["mountain"],'
            '"use_case_tags": ["wallpaper"],'
            '"dominant_colors": ["#000000"],'
            '"has_human": false,'
            '"has_face": false,'
            '"is_abstract": false,'
            '"is_minimal": true,'
            '"is_dark": true}'
        )
        choice = MagicMock()
        choice.message = msg
        result = MagicMock()
        result.choices = [choice]
        return result

    client = _make_fake_client(fake_create)
    enricher = OpenAISemanticEnricher(client=client, model="gpt-4o")

    artifacts = enricher.enrich(
        image_url="https://example.com/photo.jpg",
        analysis_text="mountain",
        search_text="dark mountain",
    )

    assert artifacts.ai_caption == "A dark mountain under stars."
    assert artifacts.scene_tags == ["mountain", "night"]
    assert artifacts.has_human is False
    assert artifacts.is_dark is True


def test_openai_embedder_returns_vector() -> None:
    from backend.services.indexing.embedding import OpenAIEmbedder

    client = MagicMock()
    embedding = MagicMock()
    embedding.embedding = [0.1] * 1536
    response = MagicMock()
    response.data = [embedding]
    client.embeddings.create = MagicMock(return_value=response)

    embedder = OpenAIEmbedder(client=client, model="text-embedding-3-small")

    vector = embedder.embed(search_text="dark mountain", caption="A dark mountain.", tags=["mountain", "night"])

    assert len(vector) == 1536
    assert vector[0] == 0.1


# --- Builder returns real adapter when mock flag is False --------------------

def test_build_translator_returns_openai_when_mock_false() -> None:
    from backend.services.indexing.translation import OpenAITranslator

    settings = MockIndexingSettings(mock_translation=False)
    translator = build_translator(settings)
    assert isinstance(translator, OpenAITranslator)


def test_build_semantic_enricher_returns_openai_when_mock_false() -> None:
    from backend.services.indexing.semantic_enrichment import OpenAISemanticEnricher

    settings = MockIndexingSettings(mock_enrichment=False)
    enricher = build_semantic_enricher(settings)
    assert isinstance(enricher, OpenAISemanticEnricher)


def test_build_embedder_returns_openai_when_mock_false() -> None:
    from backend.services.indexing.embedding import OpenAIEmbedder

    settings = MockIndexingSettings(mock_embedding=False)
    embedder = build_embedder(settings)
    assert isinstance(embedder, OpenAIEmbedder)


class MockIndexingSettings:
    """Minimal settings stub for adapter builder tests."""

    def __init__(
        self,
        *,
        mock_translation: bool = True,
        mock_enrichment: bool = True,
        mock_embedding: bool = True,
    ) -> None:
        self.mock_translation = mock_translation
        self.mock_enrichment = mock_enrichment
        self.mock_embedding = mock_embedding
        self.translation_model = "gpt-4o-mini"
        self.enrichment_model = "gpt-4o"
        self.embedding_model = "text-embedding-3-small"
        self.translation_timeout_seconds = 10.0
        self.enrichment_timeout_seconds = 20.0
        self.embedding_timeout_seconds = 10.0
        self.openai_api_key = "sk-test"
        self.openai_base_url = "https://api.openai.com/v1"
        self.embedding_api_key = ""
        self.embedding_base_url = ""
