from __future__ import annotations

import pytest

from app.agents.base import BaseAgent
from app.db.utils import utcnow
from app.models.agent_trace import AgentTrace
from app.services.llm import LLMResponse
from tests.agent_fixtures import make_context


class TokenFakeLLM:
    """Fake LLM that streams a single final response with configurable token counts."""

    def __init__(self, input_tokens: int = 100, output_tokens: int = 50):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.calls: list[dict] = []

    async def stream(self, **kwargs):
        self.calls.append(kwargs)
        yield {
            "type": "final",
            "response": LLMResponse(
                text="result",
                tool_calls=[],
                raw=None,
                input_tokens=self.input_tokens,
                output_tokens=self.output_tokens,
            ),
        }


class _DummyAgent(BaseAgent):
    name = "dummy"


@pytest.mark.asyncio
async def test_trace_single_call(test_session, test_settings):
    """A single call_llm updates trace tokens and llm_calls correctly."""
    ctx = await make_context(test_session, test_settings)
    ctx.llm = TokenFakeLLM(input_tokens=100, output_tokens=50)  # type: ignore[assignment]

    trace = AgentTrace(
        run_id=ctx.run.id,  # pyright: ignore[reportArgumentType]
        agent_name="dummy",
        stage="test",
        method="test_trace_single_call",
        start_time=utcnow(),
        tokens_input=0,
        tokens_output=0,
        llm_calls=0,
    )

    result = await _DummyAgent().call_llm(
        ctx, system_prompt="sys", user_prompt="user", trace=trace
    )

    assert result.text == "result"
    assert trace.tokens_input == 100
    assert trace.tokens_output == 50
    assert trace.llm_calls == 1


@pytest.mark.asyncio
async def test_trace_multiple_calls_cumulative(test_session, test_settings):
    """Multiple call_llm calls accumulate token counts on the same trace."""
    ctx = await make_context(test_session, test_settings)
    ctx.llm = TokenFakeLLM(input_tokens=100, output_tokens=50)  # type: ignore[assignment]

    trace = AgentTrace(
        run_id=ctx.run.id,  # pyright: ignore[reportArgumentType]
        agent_name="dummy",
        stage="test",
        method="test_trace_multiple_calls_cumulative",
        start_time=utcnow(),
        tokens_input=0,
        tokens_output=0,
        llm_calls=0,
    )

    agent = _DummyAgent()
    await agent.call_llm(ctx, system_prompt="sys", user_prompt="call 1", trace=trace)
    await agent.call_llm(ctx, system_prompt="sys", user_prompt="call 2", trace=trace)

    assert trace.tokens_input == 200
    assert trace.tokens_output == 100
    assert trace.llm_calls == 2


@pytest.mark.asyncio
async def test_trace_none_no_error(test_session, test_settings):
    """call_llm with trace=None runs without error and returns correct response."""
    ctx = await make_context(test_session, test_settings)
    ctx.llm = TokenFakeLLM(input_tokens=100, output_tokens=50)  # type: ignore[assignment]

    result = await _DummyAgent().call_llm(
        ctx, system_prompt="sys", user_prompt="user", trace=None
    )

    assert result.text == "result"
    # trace=None should not crash — the method short-circuits the write-back


@pytest.mark.asyncio
async def test_trace_none_implicit(test_session, test_settings):
    """call_llm without trace parameter (defaults to None) runs without error."""
    ctx = await make_context(test_session, test_settings)
    ctx.llm = TokenFakeLLM(input_tokens=100, output_tokens=50)  # type: ignore[assignment]

    result = await _DummyAgent().call_llm(
        ctx, system_prompt="sys", user_prompt="user"
    )

    assert result.text == "result"


@pytest.mark.asyncio
async def test_trace_with_existing_values(test_session, test_settings):
    """call_llm adds to pre-existing trace token counts."""
    ctx = await make_context(test_session, test_settings)
    ctx.llm = TokenFakeLLM(input_tokens=100, output_tokens=50)  # type: ignore[assignment]

    trace = AgentTrace(
        run_id=ctx.run.id,  # pyright: ignore[reportArgumentType]
        agent_name="dummy",
        stage="test",
        method="test_trace_with_existing_values",
        start_time=utcnow(),
        tokens_input=50,
        tokens_output=25,
        llm_calls=3,
    )

    await _DummyAgent().call_llm(
        ctx, system_prompt="sys", user_prompt="user", trace=trace
    )

    assert trace.tokens_input == 150
    assert trace.tokens_output == 75
    assert trace.llm_calls == 4


@pytest.mark.asyncio
async def test_trace_zero_tokens_still_increments_llm_calls(test_session, test_settings):
    """Even when LLM returns zero tokens, llm_calls is still incremented."""
    ctx = await make_context(test_session, test_settings)
    ctx.llm = TokenFakeLLM(input_tokens=0, output_tokens=0)  # type: ignore[assignment]

    trace = AgentTrace(
        run_id=ctx.run.id,  # pyright: ignore[reportArgumentType]
        agent_name="dummy",
        stage="test",
        method="test_trace_zero_tokens",
        start_time=utcnow(),
        tokens_input=0,
        tokens_output=0,
        llm_calls=0,
    )

    await _DummyAgent().call_llm(
        ctx, system_prompt="sys", user_prompt="user", trace=trace
    )

    assert trace.tokens_input == 0
    assert trace.tokens_output == 0
    assert trace.llm_calls == 1
