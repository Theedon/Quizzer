import pytest

from src.core.settings import Settings


def test_settings_starts_without_api_keys() -> None:
    s = Settings(
        GEMINI_API_KEY="",
        GROQ_API_KEY="",
        OPENAI_API_KEY="",
    )
    assert s.GEMINI_API_KEY == ""
    assert s.GROQ_API_KEY == ""
    assert s.OPENAI_API_KEY == ""


def test_settings_api_keys_default_to_empty_string(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("GEMINI_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(key, raising=False)

    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.GEMINI_API_KEY == ""
    assert s.GROQ_API_KEY == ""
    assert s.OPENAI_API_KEY == ""
