from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.config import Settings
from app.services.llm import LLMService


class DummyMessage:
    def __init__(self):
        self.content = [
            SimpleNamespace(type="text", text="hello"),
            SimpleNamespace(type="tool_use", id="1", name="search", input={"q": "x"}),
        ]


class DummyStream:
    def __init__(self):
        self.text_stream = self._text_stream()

    async def _text_stream(self):
        yield "hello"
        yield " world"

    async def get_final_message(self):
        return DummyMessage()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class DummyMessages:
    async def create(self, **kwargs):
        return DummyMessage()

    def stream(self, **kwargs):
        return DummyStream()


class DummyClient:
    def __init__(self):
        self.messages = DummyMessages()


class DummyAnthropicModule:
    class RateLimitError(Exception):
        pass

    class APIConnectionError(Exception):
        pass

    class APITimeoutError(Exception):
        pass

    class AsyncAnthropic:
        def __init__(self, **kwargs):
            self.kwargs = kwargs


class DummyRetryableError(Exception):
    status_code = 503


def test_get_client_missing_credentials(monkeypatch):
    # 确保环境变量不干扰测试
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)

    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        anthropic_api_key=None,
        anthropic_auth_token=None
    )
    service = LLMService(settings)

    class MockAsyncAnthropic:
        def __init__(self, **kwargs):
            pass

    monkeypatch.setattr(service, "_import_anthropic", lambda: SimpleNamespace(AsyncAnthropic=MockAsyncAnthropic))

    with pytest.raises(ValueError, match="Anthropic credentials missing"):
        service._get_client()


def test_import_anthropic_missing_dependency_raises_runtime_error(monkeypatch):
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", anthropic_api_key="key")
    service = LLMService(settings)

    def fake_import(*args, **kwargs):
        raise ModuleNotFoundError("anthropic")

    monkeypatch.setattr("builtins.__import__", fake_import)

    with pytest.raises(RuntimeError, match="Missing dependency `anthropic`"):
        service._import_anthropic()


def test_get_client_builds_default_headers_and_base_url(monkeypatch):
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        anthropic_api_key="key",
        anthropic_auth_token="token",
        anthropic_base_url="https://api.example.com",
        request_timeout_s=12,
    )
    service = LLMService(settings)

    monkeypatch.setattr(service, "_import_anthropic", lambda: DummyAnthropicModule)

    client = service._get_client()

    assert client.kwargs["api_key"] == "key"
    assert client.kwargs["timeout"] == 12
    assert client.kwargs["base_url"] == "https://api.example.com"
    assert client.kwargs["default_headers"]["Authorization"] == "Bearer token"


def test_get_client_returns_cached_client():
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", anthropic_api_key="key")
    service = LLMService(settings)
    cached = SimpleNamespace(name="cached")
    service._client = cached

    assert service._get_client() is cached


def test_import_anthropic_returns_cached_module():
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", anthropic_api_key="key")
    service = LLMService(settings)
    cached = SimpleNamespace(name="anthropic")
    service._anthropic = cached

    assert service._import_anthropic() is cached


@pytest.mark.asyncio
async def test_generate_parses_tool_calls(monkeypatch):
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", anthropic_api_key="key")
    service = LLMService(settings)
    monkeypatch.setattr(service, "_get_client", lambda: DummyClient())

    resp = await service.generate(messages=[{"role": "user", "content": "hi"}])
    assert resp.text == "hello"
    assert resp.tool_calls[0].name == "search"
    assert resp.tool_calls[0].input["q"] == "x"


def test_parse_message_handles_empty_and_unknown_blocks():
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", anthropic_api_key="key")
    service = LLMService(settings)
    message = SimpleNamespace(content=[SimpleNamespace(type="unknown"), SimpleNamespace(type="text")])

    resp = service._parse_message(message)

    assert resp.text == ""
    assert resp.tool_calls == []


def test_parse_message_handles_missing_content():
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", anthropic_api_key="key")
    service = LLMService(settings)
    message = SimpleNamespace(content=None)

    resp = service._parse_message(message)

    assert resp.text == ""
    assert resp.tool_calls == []


@pytest.mark.asyncio
async def test_generate_retries_retryable_error_then_succeeds(monkeypatch):
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", anthropic_api_key="key")
    service = LLMService(settings, max_retries=1)
    calls = {"create": 0}

    class RetryableClient:
        class messages:
            @staticmethod
            async def create(**kwargs):
                calls["create"] += 1
                if calls["create"] == 1:
                    raise DummyRetryableError("temporary")
                return DummyMessage()

    monkeypatch.setattr(service, "_get_client", lambda: RetryableClient())

    resp = await service.generate(messages=[{"role": "user", "content": "hi"}])

    assert calls["create"] == 2
    assert resp.text == "hello"


@pytest.mark.asyncio
async def test_generate_raises_non_retryable_error(monkeypatch):
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", anthropic_api_key="key")
    service = LLMService(settings, max_retries=3)

    class Client:
        class messages:
            @staticmethod
            async def create(**kwargs):
                err = RuntimeError("bad request")
                err.status_code = 400
                raise err

    monkeypatch.setattr(service, "_get_client", lambda: Client())

    with pytest.raises(RuntimeError, match="bad request"):
        await service.generate(messages=[{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_generate_includes_optional_payload_fields(monkeypatch):
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", anthropic_api_key="key")
    service = LLMService(settings)

    captured = {}

    class Client:
        class messages:
            @staticmethod
            async def create(**kwargs):
                captured.update(kwargs)
                return DummyMessage()

    monkeypatch.setattr(service, "_get_client", lambda: Client())

    await service.generate(
        messages=[{"role": "user", "content": "hi"}],
        system="sys",
        tools=[{"name": "tool"}],
        tool_choice={"type": "tool", "name": "tool"},
        model="custom-model",
        max_tokens=256,
        temperature=0.7,
        extra_param="x",
    )

    assert captured["model"] == "custom-model"
    assert captured["system"] == "sys"
    assert captured["tools"] == [{"name": "tool"}]
    assert captured["tool_choice"] == {"type": "tool", "name": "tool"}
    assert captured["temperature"] == 0.7
    assert captured["extra_param"] == "x"


@pytest.mark.asyncio
async def test_stream_emits_text_and_final(monkeypatch):
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", anthropic_api_key="key")
    service = LLMService(settings)
    monkeypatch.setattr(service, "_get_client", lambda: DummyClient())

    events = []
    async for event in service.stream(messages=[{"role": "user", "content": "hi"}]):
        events.append(event)

    assert events[0]["type"] == "text"
    assert events[-1]["type"] == "final"


@pytest.mark.asyncio
async def test_stream_includes_optional_payload_fields(monkeypatch):
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", anthropic_api_key="key")
    service = LLMService(settings)

    captured = {}

    class StreamCtx(DummyStream):
        def __init__(self):
            super().__init__()

    class Client:
        class messages:
            @staticmethod
            def stream(**kwargs):
                captured.update(kwargs)
                return StreamCtx()

    monkeypatch.setattr(service, "_get_client", lambda: Client())

    events = []
    async for event in service.stream(
        messages=[{"role": "user", "content": "hi"}],
        system="sys",
        tools=[{"name": "tool"}],
        tool_choice={"type": "tool", "name": "tool"},
        model="custom-model",
        max_tokens=256,
        temperature=0.7,
        extra_param="x",
    ):
        events.append(event)

    assert captured["model"] == "custom-model"
    assert captured["system"] == "sys"
    assert captured["tools"] == [{"name": "tool"}]
    assert captured["tool_choice"] == {"type": "tool", "name": "tool"}
    assert captured["temperature"] == 0.7
    assert captured["extra_param"] == "x"


@pytest.mark.asyncio
async def test_stream_uses_fallback_event_iteration(monkeypatch):
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", anthropic_api_key="key")
    service = LLMService(settings)

    class FallbackStream:
        def __init__(self):
            self.text_stream = None
            self._events = [
                SimpleNamespace(type="text", text="hello"),
                SimpleNamespace(type="content_block_delta", delta=SimpleNamespace(text=" world")),
            ]

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def __aiter__(self):
            return self

        async def __anext__(self):
            if not self._events:
                raise StopAsyncIteration
            return self._events.pop(0)

        async def get_final_message(self):
            return DummyMessage()

    class Client:
        class messages:
            @staticmethod
            def stream(**kwargs):
                return FallbackStream()

    monkeypatch.setattr(service, "_get_client", lambda: Client())

    events = []
    async for event in service.stream(messages=[{"role": "user", "content": "hi"}]):
        events.append(event)

    assert [event["text"] for event in events if event["type"] == "text"] == ["hello", " world"]
    assert events[-1]["type"] == "final"


@pytest.mark.asyncio
async def test_stream_retries_retryable_error_then_succeeds(monkeypatch):
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", anthropic_api_key="key")
    service = LLMService(settings, max_retries=1)
    calls = {"stream": 0}

    class RetryableClient:
        class messages:
            class _StreamCtx:
                def __init__(self, calls):
                    self.calls = calls

                async def __aenter__(self):
                    self.calls["stream"] += 1
                    if self.calls["stream"] == 1:
                        err = RuntimeError("temporary")
                        err.status_code = 503
                        raise err
                    return DummyStream()

                async def __aexit__(self, exc_type, exc, tb):
                    return False

            @staticmethod
            def stream(**kwargs):
                return RetryableClient.messages._StreamCtx(calls)

    monkeypatch.setattr(service, "_get_client", lambda: RetryableClient())

    events = []
    async for event in service.stream(messages=[{"role": "user", "content": "hi"}]):
        events.append(event)

    assert calls["stream"] == 2
    assert events[-1]["type"] == "final"


@pytest.mark.asyncio
async def test_probe_retries_transient_generate_failure(monkeypatch):
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", anthropic_api_key="key")
    service = LLMService(settings, max_retries=0)
    calls = {"generate": 0}

    class RetryableError(Exception):
        status_code = 503

    async def fake_generate(**kwargs):
        calls["generate"] += 1
        if calls["generate"] == 1:
            raise RetryableError("temporary")
        return DummyMessage()  # pragma: no cover

    async def fake_stream(**kwargs):
        raise RuntimeError("stream down")
        yield kwargs  # pragma: no cover

    monkeypatch.setattr(service, "generate", fake_generate)
    monkeypatch.setattr(service, "stream", fake_stream)
    monkeypatch.setattr(
        service,
        "_is_retryable_error",
        lambda exc: isinstance(exc, RetryableError),
    )

    result = await service.probe()

    assert calls["generate"] == 2
    assert result.status == "degraded"
    assert result.generate is True
    assert result.stream is False


@pytest.mark.asyncio
async def test_probe_returns_valid_when_generate_and_stream_succeed(monkeypatch):
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", anthropic_api_key="key")
    service = LLMService(settings)

    async def fake_generate(**kwargs):
        return DummyMessage()

    async def fake_stream(**kwargs):
        yield {"type": "text", "text": "ok"}
        yield {"type": "final", "response": DummyMessage()}

    monkeypatch.setattr(service, "generate", fake_generate)
    monkeypatch.setattr(service, "stream", fake_stream)

    result = await service.probe()

    assert result.status == "valid"
    assert result.generate is True
    assert result.stream is True


@pytest.mark.asyncio
async def test_probe_returns_invalid_when_generate_fails(monkeypatch):
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", anthropic_api_key="key")
    service = LLMService(settings)

    async def boom(**kwargs):
        raise RuntimeError("down")

    monkeypatch.setattr(service, "generate", boom)

    result = await service.probe()

    assert result.status == "invalid"
    assert result.generate is False
    assert result.stream is False


def test_is_retryable_error_matches_status_codes(monkeypatch):
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", anthropic_api_key="key")
    service = LLMService(settings)

    err = RuntimeError("temporary")
    err.status_code = 502

    assert service._is_retryable_error(err) is True


def test_is_retryable_error_matches_sdk_exceptions(monkeypatch):
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", anthropic_api_key="key")
    service = LLMService(settings)
    monkeypatch.setattr(service, "_import_anthropic", lambda: DummyAnthropicModule)

    assert service._is_retryable_error(DummyAnthropicModule.RateLimitError("x")) is True
    assert service._is_retryable_error(DummyAnthropicModule.APIConnectionError("x")) is True
    assert service._is_retryable_error(DummyAnthropicModule.APITimeoutError("x")) is True


def test_is_retryable_error_rejects_non_retryable(monkeypatch):
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", anthropic_api_key="key")
    service = LLMService(settings)

    err = RuntimeError("fatal")
    err.status_code = 400

    assert service._is_retryable_error(err) is False


@pytest.mark.asyncio
async def test_probe_generate_capability_raises_after_retry_exhaustion(monkeypatch):
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", anthropic_api_key="key")
    service = LLMService(settings)
    calls = {"generate": 0}

    async def fake_generate(**kwargs):
        calls["generate"] += 1
        err = RuntimeError("temporary")
        err.status_code = 503
        raise err

    monkeypatch.setattr(service, "generate", fake_generate)
    monkeypatch.setattr(service, "_is_retryable_error", lambda exc: True)

    with pytest.raises(RuntimeError, match="temporary"):
        await service._probe_generate_capability(messages=[{"role": "user", "content": "ping"}])

    assert calls["generate"] == 2


@pytest.mark.asyncio
async def test_probe_generate_capability_retries_once_then_succeeds(monkeypatch):
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", anthropic_api_key="key")
    service = LLMService(settings)
    calls = {"generate": 0}

    async def fake_generate(**kwargs):
        calls["generate"] += 1
        if calls["generate"] == 1:
            err = RuntimeError("temporary")
            err.status_code = 503
            raise err
        return DummyMessage()

    monkeypatch.setattr(service, "generate", fake_generate)
    monkeypatch.setattr(service, "_is_retryable_error", lambda exc: True)

    await service._probe_generate_capability(messages=[{"role": "user", "content": "ping"}])

    assert calls["generate"] == 2
