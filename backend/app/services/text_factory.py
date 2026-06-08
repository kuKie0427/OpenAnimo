from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol

from app.config import Settings
from app.services.llm import LLMService
from app.services.text import TextService


class TextServiceProtocol(Protocol):
    """Text generation service protocol (LLM or OpenAI compatible)."""

    async def generate(
        self,
        *,
        messages: list[dict[str, Any]],
        prompt: str | None = None,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> Any:  # Returns LLMResponse in practice; Any for protocol compatibility
        """Generate text from messages and/or prompt.

        Args:
            messages: Message list (LLMService requires this)
            prompt: Simple text prompt (backward compat)
            system: System prompt
            max_tokens: Max output tokens
            temperature: Sampling temperature
            **kwargs: Provider-specific extras (tools, tool_choice, model, etc.)
        """
        ...

    def stream(
        self,
        *,
        messages: list[dict[str, Any]],
        prompt: str | None = None,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream text generation.

        Yields dict events: {"type": "text", "text": "..."} or {"type": "final", ...}
        """
        ...


def create_text_service(settings: Settings) -> TextServiceProtocol:
    """根据配置创建文本生成服务

    Args:
        settings: 应用配置

    Returns:
        LLMService（Anthropic）或 TextService（OpenAI 兼容）
    """
    if settings.text_provider == "fake":
        from app.services.fake_text import FakeTextService

        return FakeTextService(settings)
    if settings.text_provider == "openai":
        return TextService(settings)
    if settings.text_provider == "anthropic":
        return LLMService(settings)
    raise ValueError(f"Unsupported text provider: {settings.text_provider}")
