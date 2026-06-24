from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from sqlmodel import select

from app.agents.render import RenderAgent
from app.models.agent_trace import AgentTrace
from tests.agent_fixtures import FakeImageService, make_context
from tests.factories import create_character, create_project, create_run


@pytest.mark.asyncio
async def test_run_characters_writes_trace_images_generated(
    test_session, test_settings, monkeypatch
):
    """Verify run_characters correctly writes trace.images_generated to the DB."""
    project = await create_project(test_session, style="anime")
    run = await create_run(test_session, project_id=project.id)
    for i in range(3):
        await create_character(
            test_session,
            project_id=project.id,
            name=f"Character {i + 1}",
            image_url=None,
        )
    await test_session.commit()

    image = FakeImageService(url="http://image.test/char.png")
    ctx = await make_context(test_session, test_settings, project=project, run=run, image=image)
    agent = RenderAgent()

    monkeypatch.setattr(
        agent,
        "generate_and_cache_image",
        AsyncMock(return_value="http://image.test/char.png"),
    )

    await agent.run_characters(ctx)

    result = await test_session.execute(
        select(AgentTrace).where(AgentTrace.run_id == ctx.run.id)
    )
    traces = result.scalars().all()
    assert len(traces) == 1
    assert traces[0].images_generated == 3
    assert traces[0].status == "completed"
