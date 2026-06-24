from __future__ import annotations

import pytest

from app.config import Settings
from app.services.text_factory import create_text_service


def test_create_text_service_openai():
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        text_provider="openai",
        text_base_url="https://example.com/v1",
        text_api_key="test",
    )
    svc = create_text_service(settings)
    from app.services.text import TextService

    assert isinstance(svc, TextService)


def test_create_text_service_anthropic():
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        text_provider="anthropic",
        anthropic_auth_token="test",
    )
    svc = create_text_service(settings)
    from app.services.llm import LLMService

    assert isinstance(svc, LLMService)


def test_create_text_service_fake():
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        text_provider="fake",
        fake_text_response="local response",
    )
    svc = create_text_service(settings)
    from app.services.fake_text import FakeTextService

    assert isinstance(svc, FakeTextService)


def test_create_text_service_unsupported():
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        text_provider="unsupported_provider",
    )
    with pytest.raises(ValueError, match="Unsupported text provider"):
        create_text_service(settings)
