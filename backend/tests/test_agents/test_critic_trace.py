"""Tests for CriticAgent trace recording in _run_review."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.agents.critic import CriticAgent
from app.models.agent_trace import AgentTrace
from app.services.llm import LLMResponse
from tests.agent_fixtures import make_context


class TokenFakeLLM:
    """Fake LLM that streams a final response with configurable token counts."""

    def __init__(self, text: str = "{}", input_tokens: int = 0, output_tokens: int = 0):
        self.text = text
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.calls: list[dict] = []

    async def stream(self, **kwargs):
        self.calls.append(kwargs)
        yield {
            "type": "final",
            "response": LLMResponse(
                text=self.text,
                tool_calls=[],
                raw=None,
                input_tokens=self.input_tokens,
                output_tokens=self.output_tokens,
            ),
        }


class VlmFailFakeLLM:
    """Fake LLM that fails on first call (simulating VLM failure), then succeeds."""

    def __init__(self, text: str = "{}", input_tokens: int = 80, output_tokens: int = 40):
        self.text = text
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.call_count = 0

    async def stream(self, **kwargs):
        self.call_count += 1
        if self.call_count == 1:
            raise RuntimeError("LLM stream failed: VLM unavailable")
        yield {
            "type": "final",
            "response": LLMResponse(
                text=self.text,
                tool_calls=[],
                raw=None,
                input_tokens=self.input_tokens,
                output_tokens=self.output_tokens,
            ),
        }


_REVIEW_JSON = (
    '{"score": 8, "dimensions": {"consistency": 8, "quality": 7, "composition": 6}}'
)


@pytest.mark.asyncio
async def test_run_review_trace_main_vlm_success(
    test_session, test_settings
):
    """Main VLM call (via call_llm) succeeds -> trace records correct token counts."""
    ctx = await make_context(test_session, test_settings)
    ctx.llm = TokenFakeLLM(  # type: ignore[assignment]
        text=_REVIEW_JSON, input_tokens=200, output_tokens=100
    )

    agent = CriticAgent()
    await agent._run_review(
        ctx,
        system_prompt="review this shot",
        user_prompt="shot content to review",
        image_url=None,
        entity_type="shot",
        entity_id=1,
        entity_name="Shot-1",
    )

    stmt = select(AgentTrace).where(AgentTrace.run_id == ctx.run.id)  # pyright: ignore[reportArgumentType]
    res = await test_session.execute(stmt)
    traces = res.scalars().all()

    assert len(traces) == 1
    trace = traces[0]
    assert trace.agent_name == "critic"
    assert trace.model_name == test_settings.text_model
    assert trace.tokens_input == 200
    assert trace.tokens_output == 100
    assert trace.llm_calls == 1
    assert trace.status == "completed"
    assert trace.stage == "review"
    assert trace.method == "_run_review"


@pytest.mark.asyncio
async def test_run_review_trace_fallback_succeeds(
    test_session, test_settings
):
    """Main VLM fails -> fallback call_llm records correct tokens on same trace."""
    ctx = await make_context(test_session, test_settings)
    ctx.llm = VlmFailFakeLLM(  # type: ignore[assignment]
        text=_REVIEW_JSON, input_tokens=80, output_tokens=40
    )

    agent = CriticAgent()
    await agent._run_review(
        ctx,
        system_prompt="review this shot",
        user_prompt="shot content to review",
        image_url=None,
        entity_type="shot",
        entity_id=1,
        entity_name="Shot-1",
    )

    # verify trace persisted with fallback tokens
    stmt = select(AgentTrace).where(AgentTrace.run_id == ctx.run.id)  # pyright: ignore[reportArgumentType]
    res = await test_session.execute(stmt)
    traces = res.scalars().all()

    assert len(traces) == 1
    trace = traces[0]
    assert trace.agent_name == "critic"
    assert trace.model_name == test_settings.text_model
    assert trace.tokens_input == 80
    assert trace.tokens_output == 40
    assert trace.llm_calls == 1
    assert trace.status == "completed"
    assert trace.stage == "review"
    assert trace.method == "_run_review"
