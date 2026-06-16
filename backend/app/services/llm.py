from __future__ import annotations

import anthropic
import asyncio
from dataclasses import dataclass
from typing import Any, AsyncIterator

from app.config import Settings
from app.services.text_capabilities import TextProviderCapability


@dataclass(slots=True)
class ToolCall:
    id: str
    name: str
    input: dict[str, Any]


@dataclass(slots=True)
class LLMResponse:
    text: str
    tool_calls: list[ToolCall]
    raw: Any
    input_tokens: int = 0
    output_tokens: int = 0


class LLMService:
    """Claude (Anthropic Messages API) 服务包装器。

    - 直接使用 `anthropic` SDK（不是 claude_agent_sdk）
    - 支持工具调用（tools/tool_choice）
    - 支持流式输出
    """

    def __init__(self, settings: Settings, *, max_retries: int = 3):
        self.settings = settings
        self.max_retries = max_retries
        self._client: Any | None = None
        self._anthropic: Any | None = None

    def _import_anthropic(self) -> Any:
        if self._anthropic is not None:
            return self._anthropic
        try:
            import anthropic  # type: ignore
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise RuntimeError(
                "Missing dependency `anthropic`. Run `uv sync` to install."
            ) from exc
        self._anthropic = anthropic
        return anthropic

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        anthropic = self._import_anthropic()

        api_key = self.settings.anthropic_api_key or self.settings.anthropic_auth_token
        if not api_key:
            raise ValueError("Anthropic credentials missing: set `anthropic_api_key` or `anthropic_auth_token`.")

        default_headers: dict[str, str] = {}
        if self.settings.anthropic_auth_token:
            # 兼容一些中转站使用 Bearer Token 的鉴权方式
            default_headers["Authorization"] = f"Bearer {self.settings.anthropic_auth_token}"

        kwargs: dict[str, Any] = {
            "api_key": api_key,
            "timeout": self.settings.request_timeout_s,
            # 我们在外层自己做重试，避免双重重试导致等待过长
            "max_retries": 0,
        }
        if self.settings.anthropic_base_url:
            kwargs["base_url"] = self.settings.anthropic_base_url
        if default_headers:
            kwargs["default_headers"] = default_headers

        self._client = anthropic.AsyncAnthropic(**kwargs)
        return self._client

    def _parse_message(self, message: Any) -> LLMResponse:
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []

        for block in getattr(message, "content", []) or []:
            block_type = getattr(block, "type", None)
            if block_type == "text":
                text_parts.append(getattr(block, "text", ""))
            elif block_type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=str(getattr(block, "id", "")),
                        name=str(getattr(block, "name", "")),
                        input=dict(getattr(block, "input", {}) or {}),
                    )
                )

        usage = getattr(message, "usage", None)
        input_tokens = getattr(usage, "input_tokens", 0) or 0
        output_tokens = getattr(usage, "output_tokens", 0) or 0
        return LLMResponse(
            text="".join(text_parts),
            tool_calls=tool_calls,
            raw=message,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    def _is_retryable_error(self, exc: Exception) -> bool:
        anthropic = self._import_anthropic()
        retryable_types: tuple[type[BaseException], ...] = (
            getattr(anthropic, "RateLimitError", Exception),
            getattr(anthropic, "APIConnectionError", Exception),
            getattr(anthropic, "APITimeoutError", Exception),
        )
        if isinstance(exc, retryable_types):
            return True

        status_code = getattr(exc, "status_code", None)
        if isinstance(status_code, int) and status_code in {408, 429, 500, 502, 503, 504}:
            return True

        return False

    async def _probe_generate_capability(self, *, messages: list[dict[str, Any]]) -> None:
        delay_s = 0.5
        last_exc: Exception | None = None

        for attempt in range(2):
            try:
                await self.generate(messages=messages, max_tokens=1, temperature=0)
                return
            except Exception as exc:
                last_exc = exc
                if attempt >= 1 or not self._is_retryable_error(exc):
                    raise
                await asyncio.sleep(delay_s)
                delay_s = min(delay_s * 2, 2.0)

        if last_exc is not None:
            raise last_exc

    async def probe(self) -> TextProviderCapability:
        probe_messages = [{"role": "user", "content": "ping"}]

        try:
            await self._probe_generate_capability(messages=probe_messages)
        except (anthropic.APIError, RuntimeError) as exc:
            return TextProviderCapability(
                status="invalid",
                generate=False,
                stream=False,
                reason_code="provider_generate_unavailable",
                reason_message=f"文本 Provider 连通性预检失败：{str(exc)[:200]}",
            )

        try:
            async for _ in self.stream(messages=probe_messages, max_tokens=1, temperature=0):
                pass
        except (anthropic.APIError, RuntimeError) as exc:
            return TextProviderCapability(
                status="degraded",
                generate=True,
                stream=False,
                reason_code="provider_stream_unavailable",
                reason_message=f"文本 Provider 流式不可用，将优先回退非流式。原始错误：{str(exc)[:200]}",
            )

        return TextProviderCapability(status="valid", generate=True, stream=True)

    async def generate(
        self,
        *,
        messages: list[dict[str, Any]],
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: dict[str, Any] | None = None,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        client = self._get_client()

        payload: dict[str, Any] = {
            "model": model or self.settings.anthropic_model,
            "max_tokens": max_tokens,
            "messages": messages,
            **kwargs,
        }
        if system is not None:
            payload["system"] = system
        if tools is not None:
            payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice
        if temperature is not None:
            payload["temperature"] = temperature

        delay_s = 0.5
        for attempt in range(self.max_retries + 1):
            try:
                message = await client.messages.create(**payload)
                return self._parse_message(message)
            except Exception as exc:
                if attempt >= self.max_retries or not self._is_retryable_error(exc):
                    raise
                await asyncio.sleep(delay_s)
                delay_s = min(delay_s * 2, 8.0)

        raise RuntimeError("unreachable")  # pragma: no cover

    async def stream(
        self,
        *,
        messages: list[dict[str, Any]],
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: dict[str, Any] | None = None,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        """流式输出。

        产出事件：
        - {"type": "text", "text": "..."}  # 增量文本
        - {"type": "final", "response": LLMResponse(...)}  # 最终聚合（包含 tool_calls）
        """

        client = self._get_client()

        payload: dict[str, Any] = {
            "model": model or self.settings.anthropic_model,
            "max_tokens": max_tokens,
            "messages": messages,
            **kwargs,
        }
        if system is not None:
            payload["system"] = system
        if tools is not None:
            payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice
        if temperature is not None:
            payload["temperature"] = temperature

        delay_s = 0.5
        for attempt in range(self.max_retries + 1):
            try:
                async with client.messages.stream(**payload) as stream:
                    # SDK 提供 text_stream（最稳定的文本增量接口）
                    text_stream = getattr(stream, "text_stream", None)
                    if text_stream is not None:
                        async for text in text_stream:
                            yield {"type": "text", "text": text}
                    else:  # pragma: no cover
                        async for event in stream:
                            event_type = getattr(event, "type", None)
                            if event_type == "text":
                                yield {"type": "text", "text": getattr(event, "text", "")}
                            elif event_type == "content_block_delta":
                                delta = getattr(event, "delta", None)
                                delta_text = getattr(delta, "text", None)
                                if isinstance(delta_text, str):
                                    yield {"type": "text", "text": delta_text}

                    final_message = await stream.get_final_message()
                    yield {"type": "final", "response": self._parse_message(final_message)}
                return
            except Exception as exc:
                if attempt >= self.max_retries or not self._is_retryable_error(exc):
                    raise
                await asyncio.sleep(delay_s)
                delay_s = min(delay_s * 2, 8.0)

        raise RuntimeError("unreachable")  # pragma: no cover
