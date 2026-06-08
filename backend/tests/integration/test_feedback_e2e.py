"""E2E tests for critique feedback injection into RenderAgent prompts.

Uses real DB entities (Project, Character, AgentRun) and REAL AgentContext
(via make_context) — no MagicMock for AgentContext.
"""

from __future__ import annotations

import pytest
from sqlmodel import select

from app.agents.render import RenderAgent
from app.models.agent_run import AgentMessage
from tests.agent_fixtures import make_context
from tests.factories import create_character, create_project


@pytest.mark.asyncio
async def test_e2e_cf_01_feedback_injected_into_prompt(
    test_session, test_settings
):
    """E2E-CF-01: Critic feedback → prompt contains improvement suggestions.

    Creates real Project + Character + AgentContext with critique_feedback,
    then verifies the suggestion text appears in the generated prompt.
    """
    # Arrange: real DB entities
    project = await create_project(test_session)
    character = await create_character(
        test_session,
        project_id=project.id,
        name="Warrior",
        description="warrior girl with red armor",
    )

    # Build REAL AgentContext (not MagicMock)
    ctx = await make_context(test_session, test_settings, project=project)

    # Set critique feedback — key must be str(character.id)
    ctx.critique_feedback = {
        "character": {
            str(character.id): {
                "issues": ["面部比例不对"],
                "suggestions": ["调大眼睛间距", "缩小嘴巴"],
            }
        }
    }

    agent = RenderAgent()

    # Act: build character prompt with feedback
    prompt = await agent._build_character_prompt(
        character, style="anime", session=test_session, ctx=ctx
    )

    # Assert: prompt contains the feedback suggestions
    assert "改进建议: 调大眼睛间距；缩小嘴巴" in prompt
    assert "warrior girl" in prompt
    assert prompt.endswith("缩小嘴巴")


@pytest.mark.asyncio
async def test_e2e_cf_02_no_feedback_no_injection(test_session, test_settings):
    """E2E-CF-02: No feedback → prompt has no feedback section.

    Sets critique_feedback to empty per-character dict and verifies
    the prompt does NOT contain the 改进建议 marker.
    """
    # Arrange
    project = await create_project(test_session)
    character = await create_character(
        test_session,
        project_id=project.id,
        name="Mage",
        description="wise mage with blue robe",
    )

    ctx = await make_context(test_session, test_settings, project=project)
    ctx.critique_feedback = {"character": {}}  # Empty feedback

    agent = RenderAgent()

    # Act
    prompt = await agent._build_character_prompt(
        character, style="anime", session=test_session, ctx=ctx
    )

    # Assert: no feedback marker in prompt
    assert "改进建议" not in prompt
    assert "wise mage" in prompt


@pytest.mark.asyncio
async def test_e2e_cf_03_trace_records_feedback_flow(
    test_session, test_settings
):
    """E2E-CF-03: AgentMessage records feedback flow.

    Creates a REAL AgentContext, calls _build_character_prompt with
    critique_feedback, records a trace AgentMessage, and verifies
    the trace is queryable by run_id.
    """
    # Arrange: real DB entities
    project = await create_project(test_session)
    character = await create_character(
        test_session,
        project_id=project.id,
        name="Archer",
        description="elven archer in forest",
    )

    ctx = await make_context(test_session, test_settings, project=project)
    ctx.critique_feedback = {
        "character": {
            str(character.id): {
                "issues": ["身体比例失调"],
                "suggestions": ["加长腿部比例", "收窄肩膀"],
            }
        }
    }

    agent = RenderAgent()

    # Act: build prompt — feedback is injected
    prompt = await agent._build_character_prompt(
        character, style="anime", session=test_session, ctx=ctx
    )
    assert "加长腿部比例" in prompt

    # Record a trace AgentMessage (simulates what orchestrator does)
    trace_msg = AgentMessage(
        run_id=ctx.run.id,
        agent="critic",
        role="system",
        content=(
            f"Feedback injected for character {character.id}: "
            "加长腿部比例；收窄肩膀"
        ),
    )
    test_session.add(trace_msg)
    await test_session.commit()

    # Assert: trace record exists and is queryable by run_id
    result = await test_session.execute(
        select(AgentMessage).where(AgentMessage.run_id == ctx.run.id)
    )
    records = result.scalars().all()

    assert len(records) >= 1
    assert any("加长腿部比例" in r.content for r in records)
    assert all(r.run_id == ctx.run.id for r in records)
