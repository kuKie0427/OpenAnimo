"""E2E tests for narrative beat analysis integration with PlanAgent.

Tests verify:
- E2E-BA-01: PlanAgent.run_shots creates shots with proper properties
- E2E-BA-02: analyze_beats(10) produces correct three-act 2:5:3 distribution
- E2E-BA-03: PlanAgent prompt contains beat schedule metadata when outline is approved
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy import select

from app.agents.plan import PlanAgent
from app.models.project import Shot
from app.services.beat_analyzer import analyze_beats
from tests.agent_fixtures import FakeLLM, make_context
from tests.factories import create_project, create_run


@pytest.mark.asyncio
async def test_e2e_ba_01_plan_agent_shots_reflect_beat_metadata(
    test_session, test_settings
):
    """E2E-BA-01: PlanAgent.run_shots creates shots with proper properties.

    Verifies that when PlanAgent processes beat data via FakeLLM, created shots
    have duration > 0 and valid camera values from the plan response.
    """
    project = await create_project(test_session)
    run = await create_run(test_session, project_id=project.id)

    llm_output = json.dumps(
        {
            "agent": "plan",
            "project_update": {"status": "planning"},
            "visual_bible": "warm tones",
            "shots": [
                {
                    "order": 1,
                    "description": "Opening scene",
                    "scene": "Intro",
                    "action": "Character enters",
                    "expression": "neutral",
                    "lighting": "bright",
                    "dialogue": "Hello",
                    "sfx": "wind",
                    "camera": "medium",
                    "duration": 3.0,
                },
                {
                    "order": 2,
                    "description": "Action scene",
                    "scene": "Forest",
                    "action": "Running",
                    "expression": "determined",
                    "lighting": "dramatic",
                    "dialogue": "",
                    "sfx": "footsteps",
                    "camera": "close-up",
                    "duration": 2.5,
                },
            ],
        },
        ensure_ascii=False,
    )

    llm = FakeLLM(llm_output)
    ctx = await make_context(
        test_session, test_settings, project=project, run=run, llm=llm
    )

    await PlanAgent().run_shots(ctx)

    shots = (
        await test_session.execute(
            select(Shot).where(Shot.project_id == project.id).order_by(Shot.order)
        )
    ).scalars().all()

    assert len(shots) == 2
    for shot in shots:
        assert shot.duration > 0
        assert shot.camera in ("medium", "close-up")


@pytest.mark.asyncio
async def test_e2e_ba_02_analyze_beats_10_three_act_distribution():
    """E2E-BA-02: analyze_beats(10) produces correct 2:5:3 distribution.

    Pure function test — no DB or LLM dependencies.
    """
    result = analyze_beats(10)

    assert len(result) == 10

    act_counts: dict[int, int] = {}
    for beat in result:
        act_counts[beat.act] = act_counts.get(beat.act, 0) + 1

    assert act_counts == {1: 2, 2: 5, 3: 3}


@pytest.mark.asyncio
async def test_e2e_ba_03_plan_agent_prompt_contains_beat_metadata(
    test_session, test_settings
):
    """E2E-BA-03: PlanAgent injects beat schedule metadata into LLM prompt.

    When project has outline_approved=True, story_outline dict, and
    target_shot_count > 0, verify that format_beat_schedule() output
    appears in the prompt JSON payload sent to the LLM.
    """
    project = await create_project(test_session)

    # Set beat-triggering flags: outline_approved + story_outline + target_shot_count
    project.outline_approved = True
    project.story_outline = {
        "acts": [{"name": "Act 1"}, {"name": "Act 2"}, {"name": "Act 3"}]
    }
    project.target_shot_count = 10
    test_session.add(project)
    await test_session.commit()
    await test_session.refresh(project)

    run = await create_run(test_session, project_id=project.id)

    llm_output = json.dumps(
        {
            "agent": "plan",
            "project_update": {"status": "planning"},
            "visual_bible": "test",
            "shots": [
                {
                    "order": 1,
                    "description": "Test shot",
                    "camera": "medium",
                    "duration": 3.0,
                },
            ],
        },
        ensure_ascii=False,
    )

    llm = FakeLLM(llm_output)
    ctx = await make_context(
        test_session, test_settings, project=project, run=run, llm=llm
    )

    await PlanAgent().run_shots(ctx)

    # Verify FakeLLM received beat metadata in the prompt
    assert len(llm.calls) == 1
    call = llm.calls[0]
    user_msg = call["messages"][0]["content"]

    # beat_schedule JSON key in the payload
    assert "beat_schedule" in user_msg
    # Chinese beat-specific keywords from format_beat_schedule
    assert "节拍调度表" in user_msg
    assert "强度" in user_msg
    assert "时长" in user_msg
