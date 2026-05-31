from backend.llm.providers.factory import build_chat_model


def test_provider_factory_can_build_capability_scoped_model_config() -> None:
    model = build_chat_model(
        capability="planner",
        provider_name="openai",
        model_name="gpt-4.1-mini",
        api_key="test-key",
        base_url="https://api.openai.com/v1",
    )

    assert model is not None
