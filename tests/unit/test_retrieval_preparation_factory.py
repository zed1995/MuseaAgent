from backend.core.config import Settings
from backend.services.retrieval_preparation.factory import build_retrieval_preparation_service


def test_retrieval_preparation_factory_skips_model_chains_without_api_keys(monkeypatch) -> None:
    settings = Settings()
    settings.indexing.mock_translation = False
    settings.retrieval_preparation.use_model_understanding = True
    settings.retrieval_preparation.use_model_rewrite = True
    settings.llm.understanding.api_key = ""
    settings.llm.rewrite.api_key = ""

    def _unexpected_build(**kwargs):
        raise AssertionError("build_chat_model should not be called without an API key")

    monkeypatch.setattr(
        "backend.services.retrieval_preparation.factory.build_chat_model",
        _unexpected_build,
    )

    service = build_retrieval_preparation_service(settings)
    prepared = service.prepare("我想找深色安静的壁纸，不要人物", "auto")

    assert prepared.understanding.inferred_mode == "wallpaper"
    assert prepared.rewrite.rewrite_for_embedding
