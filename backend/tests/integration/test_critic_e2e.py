"""E2E tests for CriticAgent dimension-level threshold behavior."""
from __future__ import annotations

import json
from typing import Any

import pytest
from sqlmodel import select

from app.agents.base import AgentContext
from app.agents.critic import CriticAgent
from app.models.project import Character
from app.services.llm import LLMResponse
from tests.agent_fixtures import (
    DummyWsManager,
    FakeImageService,
    FakeLLM,
    FakeVideoService,
)
from tests.factories import create_character, create_project, create_run


class StubTextService:
    def __init__(self, response_json: str):
        self.response_json = response_json

    async def generate(
        self,
        *,
        messages: list[dict[str, Any]] | None = None,
        prompt: str | None = None,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        return LLMResponse(text=self.response_json, tool_calls=[], raw=None)


async def _run_review_and_get_critique(
    monkeypatch, test_session, test_settings, review_json: str
) -> tuple[DummyWsManager, dict]:
    project = await create_project(test_session, title="Critic E2E")
    char = await create_character(
        test_session,
        project_id=project.id,
        name="Hero",
        description="A brave hero with a red cape",
        image_url="http://test.com/character.png",
    )
    run = await create_run(test_session, project_id=project.id, status="queued")

    ws = DummyWsManager()
    stub_text = StubTextService(review_json)

    monkeypatch.setattr("app.agents.critic.create_text_service", lambda s: stub_text)

    ctx = AgentContext(
        settings=test_settings,
        session=test_session,
        ws=ws,  # type: ignore[arg-type]
        project=project,
        run=run,
        llm=FakeLLM("{}"),  # type: ignore[arg-type]
        image=FakeImageService(),
        video=FakeVideoService(),  # type: ignore[arg-type]
    )

    agent = CriticAgent()
    result = await agent.run_character_review(ctx)

    assert str(char.id) in result["scores"]

    critique_events = [e for (_, e) in ws.events if e.get("type") == "critique_result"]
    assert len(critique_events) == 1
    critique_data = critique_events[0]["data"]

    query = select(Character).where(
        Character.project_id == project.id, Character.image_url.isnot(None)
    )
    db_res = await test_session.execute(query)
    assert len(db_res.scalars().all()) == 1

    return ws, critique_data


@pytest.mark.asyncio
async def test_e2e_ct01_all_pass_no_regeneration(monkeypatch, test_session, test_settings):
    """E2E-CT-01: All dimensions pass → no regeneration."""
    review_json = json.dumps({
        "score": 7,
        "dimensions": {"consistency": 8, "quality": 7, "composition": 6},
        "issues": [],
        "suggestions": [],
    })

    _, critique_data = await _run_review_and_get_critique(
        monkeypatch, test_session, test_settings, review_json
    )

    assert critique_data["failed_checks"] == []
    assert critique_data["will_regenerate"] is False


@pytest.mark.asyncio
async def test_e2e_ct02_consistency_masking_detected(monkeypatch, test_session, test_settings):
    """E2E-CT-02: Consistency masking — consistency=3 < 4 but weighted score 6.9 > 6.0."""
    review_json = json.dumps({
        "score": 6.9,
        "dimensions": {"consistency": 3, "quality": 10, "composition": 9},
        "issues": ["面部比例不对"],
        "suggestions": ["调大眼睛间距"],
    })

    _, critique_data = await _run_review_and_get_critique(
        monkeypatch, test_session, test_settings, review_json
    )

    failed = critique_data["failed_checks"]
    assert any("consistency" in f for f in failed)
    assert critique_data["will_regenerate"] is True


@pytest.mark.asyncio
async def test_e2e_ct03_quality_below_threshold(monkeypatch, test_session, test_settings):
    """E2E-CT-03: Quality dimension below threshold triggers regeneration."""
    review_json = json.dumps({
        "score": 7,
        "dimensions": {"consistency": 8, "quality": 3, "composition": 8},
        "issues": ["图像模糊"],
        "suggestions": ["提高清晰度"],
    })

    _, critique_data = await _run_review_and_get_critique(
        monkeypatch, test_session, test_settings, review_json
    )

    failed = critique_data["failed_checks"]
    assert any("quality" in f for f in failed)
    assert critique_data["will_regenerate"] is True


@pytest.mark.asyncio
async def test_e2e_ct04_score_below_threshold(monkeypatch, test_session, test_settings):
    """E2E-CT-04: Dimensions pass but aggregate score < 6.0 → regeneration."""
    review_json = json.dumps({
        "score": 5,
        "dimensions": {"consistency": 5, "quality": 5, "composition": 5},
        "issues": ["整体效果一般"],
        "suggestions": ["尝试不同风格"],
    })

    _, critique_data = await _run_review_and_get_critique(
        monkeypatch, test_session, test_settings, review_json
    )

    failed = critique_data["failed_checks"]
    assert any("score" in f for f in failed)
    assert critique_data["will_regenerate"] is True


@pytest.mark.asyncio
async def test_e2e_ct05_all_fail_four_reasons(monkeypatch, test_session, test_settings):
    """E2E-CT-05: All dimensions + score below thresholds → 4 failure reasons."""
    review_json = json.dumps({
        "score": 2,
        "dimensions": {"consistency": 2, "quality": 2, "composition": 1},
        "issues": ["严重失真", "构图混乱"],
        "suggestions": ["重新生成", "调整参数"],
    })

    _, critique_data = await _run_review_and_get_critique(
        monkeypatch, test_session, test_settings, review_json
    )

    failed = critique_data["failed_checks"]
    assert len(failed) == 4
    assert any("consistency" in f for f in failed)
    assert any("quality" in f for f in failed)
    assert any("composition" in f for f in failed)
    assert any("score" in f for f in failed)
    assert critique_data["will_regenerate"] is True
