from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.v1.routes import text as text_routes
from app.config import Settings
from app.schemas.text import TextGenerateRequest


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        anthropic_api_key="test-key",
        image_api_key="test-key",
        video_api_key="test-key",
    )


@pytest.mark.asyncio
async def test_generate_text_success(monkeypatch, test_settings):
    """测试文本生成成功"""

    async def fake_generate(self, *, prompt, max_tokens, temperature, **kwargs):
        return "Generated text response"

    from app.services import text as text_module

    monkeypatch.setattr(text_module.TextService, "generate", fake_generate)

    response = await text_routes.generate_text(
        TextGenerateRequest(prompt="Hello", max_tokens=100, temperature=0.7),
        settings=test_settings,
        _=None,
    )

    assert response.text == "Generated text response"
    assert response.model == test_settings.text_model


@pytest.mark.asyncio
async def test_generate_text_with_messages(monkeypatch, test_settings):
    """测试多轮对话"""

    async def fake_generate(self, *, prompt, max_tokens, temperature, **kwargs):
        assert "messages" in kwargs
        assert kwargs["messages"] == [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hi"},
        ]
        return "Response with context"

    from app.services import text as text_module

    monkeypatch.setattr(text_module.TextService, "generate", fake_generate)

    response = await text_routes.generate_text(
        TextGenerateRequest(
            prompt="ignored",
            messages=[
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hi"},
            ],
        ),
        settings=test_settings,
        _=None,
    )

    assert response.text == "Response with context"


def test_generate_text_validation_error():
    """测试参数验证"""
    with pytest.raises(ValidationError):
        TextGenerateRequest.model_validate({"max_tokens": 100})


def test_generate_text_max_tokens_validation():
    """测试 max_tokens 范围验证"""
    with pytest.raises(ValidationError):
        TextGenerateRequest.model_validate({"prompt": "test", "max_tokens": 10000})


def test_generate_text_temperature_validation():
    """测试 temperature 范围验证"""
    with pytest.raises(ValidationError):
        TextGenerateRequest.model_validate({"prompt": "test", "temperature": 3.0})


@pytest.mark.asyncio
async def test_stream_text_success(monkeypatch, test_settings):
    """测试流式文本生成"""

    async def fake_stream(self, *, prompt, max_tokens, temperature, **kwargs):
        for chunk in ["Hello", " ", "world"]:
            yield chunk

    from app.services import text as text_module

    monkeypatch.setattr(text_module.TextService, "stream", fake_stream)

    response = await text_routes.stream_text(
        TextGenerateRequest(prompt="Hello"),
        settings=test_settings,
        _=None,
    )

    assert response.media_type == "text/plain"

    chunks: list[str] = []
    async for chunk in response.body_iterator:
        chunks.append(chunk if isinstance(chunk, str) else chunk.decode())
    assert "".join(chunks) == "Hello world"


@pytest.mark.asyncio
async def test_stream_text_with_messages(monkeypatch, test_settings):
    """测试流式多轮对话"""

    async def fake_stream(self, *, prompt, max_tokens, temperature, **kwargs):
        assert "messages" in kwargs
        yield "Streaming response"

    from app.services import text as text_module

    monkeypatch.setattr(text_module.TextService, "stream", fake_stream)

    response = await text_routes.stream_text(
        TextGenerateRequest(
            prompt="ignored",
            messages=[{"role": "user", "content": "Hi"}],
        ),
        settings=test_settings,
        _=None,
    )

    chunks: list[str] = []
    async for chunk in response.body_iterator:
        chunks.append(chunk if isinstance(chunk, str) else chunk.decode())
    assert "".join(chunks) == "Streaming response"
