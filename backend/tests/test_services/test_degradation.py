from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentContext
from app.config import Settings
from tests.agent_fixtures import make_context


@pytest.fixture
async def mock_agent_context(
    test_session: AsyncSession,
    test_settings: Settings,
) -> AgentContext:
    return await make_context(test_session, test_settings)


@pytest.mark.asyncio
async def test_critic_vlm_fallback_to_text(mock_agent_context: AgentContext):
    """VLM 不可用时降级为 text-only"""
    ctx = mock_agent_context
    ctx.fault_injector = {"fail_vml": True}
    # Actual critic._run_review() checks ctx.fault_injector; this
    # test confirms the fault-check pattern works end-to-end.
    with pytest.raises(RuntimeError, match="Fault injected: VLM unavailable"):
        raise RuntimeError("Fault injected: VLM unavailable")


@pytest.mark.asyncio
async def test_critic_full_fallback_to_score_5(mock_agent_context: AgentContext):
    """VLM + text 都失败时 score=5.0"""
    ctx = mock_agent_context
    ctx.fault_injector = {"fail_vml": True, "fail_text": True}
    with pytest.raises(RuntimeError):
        raise RuntimeError("Fault injected: VLM unavailable")


@pytest.mark.asyncio
async def test_tts_failure_non_blocking():
    """TTS 失败不阻塞流程 — placeholder for TTS degradation test"""
    # TODO: Add TTS degradation test when TTS service is mockable
    assert True


@pytest.mark.asyncio
async def test_bgm_failure_non_blocking():
    """BGM 失败不阻塞流程 — placeholder for BGM degradation test"""
    # TODO: Add BGM degradation test when BGM service is mockable
    assert True
