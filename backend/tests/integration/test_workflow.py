from __future__ import annotations

import json

from PIL import Image

from app.services.image_composer import ImageComposer

import pytest
from sqlmodel import select

from app.agents.base import AgentContext
from app.agents.compose import ComposeAgent
from app.agents.plan import PlanAgent
from app.agents.render import RenderAgent
from app.models.project import Character, Shot
from app.services.llm import LLMResponse
from tests.agent_fixtures import DummyWsManager
from tests.factories import create_project, create_run


class StubLLM:
    responses: list[str] = []

    def __init__(self, settings):
        self.settings = settings

    async def stream(self, **kwargs):
        if not self.responses:
            raise RuntimeError("No stub response configured")
        text = self.responses.pop(0)
        yield {"type": "final", "response": LLMResponse(text=text, tool_calls=[], raw=None)}


class StubImage:
    def __init__(self, settings):
        self.settings = settings
        self.count = 0

    async def generate_url(self, **kwargs):
        self.count += 1
        return f"http://image.test/{self.count}"

    async def cache_external_image(self, url: str) -> str:
        return url


class StubVideo:
    def __init__(self, settings):
        self.settings = settings
        self.count = 0

    async def generate_url(self, **kwargs):
        self.count += 1
        return f"http://video.test/{self.count}"

    async def merge_urls(self, video_urls):
        return "/static/videos/merged.mp4"


@pytest.mark.asyncio
async def test_full_workflow(monkeypatch, test_session, test_settings):
    project = await create_project(test_session, title="Workflow")
    run = await create_run(test_session, project_id=project.id, status="queued")
    ws = DummyWsManager()

    StubLLM.responses = [
        json.dumps(
            {
                "project_update": {"title": "Workflow", "style": "anime", "status": "planning"},
                "characters": [{"name": "Hero", "description": "Brave"}],
                "shots": [{"order": 1, "description": "Shot 1", "scene": "Opening", "action": "Hero enters", "expression": "determined", "lighting": "dramatic", "dialogue": "Here I come!", "sfx": "wind"}],
                "user_message": "Plan done",
            }
        ),
        json.dumps({"user_message": "Character images done"}),
        json.dumps({"user_message": "Shot images done"}),
    ]

    monkeypatch.setattr("app.services.face_cropper._get_face_analysis", lambda: None)

    # StubImage returns fake URLs — monkeypatch the download to return a tiny real PIL Image
    async def _fake_download_image(self, url: str) -> Image.Image:
        return Image.new("RGB", (64, 64), color="red")

    monkeypatch.setattr(ImageComposer, "_download_image", _fake_download_image)

    ctx = AgentContext(
        settings=test_settings,
        session=test_session,
        ws=ws,
        project=project,
        run=run,
        llm=StubLLM(test_settings),
        image=StubImage(test_settings),
        video=StubVideo(test_settings),
    )

    plan_agent = PlanAgent()
    render_agent = RenderAgent()
    compose_agent = ComposeAgent()

    await plan_agent.run_characters(ctx)
    await plan_agent.run_shots(ctx)
    await render_agent.run_characters(ctx)
    await render_agent.run_shots(ctx)
    await compose_agent.run_videos(ctx)
    await compose_agent.run_merge(ctx)

    run.status = "succeeded"
    test_session.add(run)
    await test_session.commit()

    await test_session.refresh(project)
    await test_session.refresh(run)
    assert project.status == "ready"
    assert project.video_url == "/static/videos/merged.mp4"
    assert run.status == "succeeded"

    res = await test_session.execute(select(Character).where(Character.project_id == project.id))
    assert len(res.scalars().all()) == 1

    res = await test_session.execute(select(Shot).where(Shot.project_id == project.id))
    shots = list(res.scalars().all())
    assert len(shots) == 1
    assert shots[0].image_url
    assert shots[0].video_url
