from backend.core.config import Settings


def test_settings_defaults() -> None:
    settings = Settings()

    assert settings.app_name == "MuseaAgent API"
    assert settings.environment == "development"
    assert settings.api_prefix == "/api"


def test_settings_read_environment_variables(monkeypatch) -> None:
    monkeypatch.setenv("MUSEA_AGENT_APP_NAME", "MuseaAgent Test API")
    monkeypatch.setenv("MUSEA_AGENT_ENVIRONMENT", "test")
    monkeypatch.setenv("MUSEA_AGENT_API_PREFIX", "/internal")

    settings = Settings()

    assert settings.app_name == "MuseaAgent Test API"
    assert settings.environment == "test"
    assert settings.api_prefix == "/internal"
