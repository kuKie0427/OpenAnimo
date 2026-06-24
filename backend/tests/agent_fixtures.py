from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentContext
from app.config import Settings
from app.models.agent_run import AgentRun
from app.models.project import Project
from app.services.llm import LLMResponse
from tests.factories import create_project, create_run


class FakeLLM:
    def __init__(self, response_text: str | list[str]):
        if isinstance(response_text, list):
            self.responses = list(response_text)
        else:
            self.responses = [response_text]
        self.calls: list[dict] = []

    @property
    def response_text(self) -> str:
        return self.responses[-1] if self.responses else "{}"

    async def stream(self, **kwargs):
        self.calls.append(kwargs)
        text = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        yield {"type": "final", "response": LLMResponse(text=text, tool_calls=[], raw=None)}


class FakeImageService:
    def __init__(self, url: str = "http://image.test/default.png"):
        self.url = url
        self.count = 0

    async def generate_url(self, **kwargs):
        self.count += 1
        return self.url

    async def cache_external_image(self, url: str) -> str:
        # Tests use fake URLs; keep the URL unchanged.
        return url


class FakeVideoService:
    def __init__(self, url: str = "http://video.test/default.mp4", merged_url: str | None = None):
        self.url = url
        self.merged_url = merged_url
        self.count = 0

    async def generate_url(self, **kwargs):
        self.count += 1
        return self.url

    async def merge_urls(self, video_urls):
        return self.merged_url or "/static/videos/merged.mp4"


class DummyWsManager:
    def __init__(self):
        self.events: list[tuple[int, dict]] = []

    async def send_event(self, project_id: int, event: dict):
        self.events.append((project_id, event))


async def make_context(
    session: AsyncSession,
    settings: Settings,
    project: Project | None = None,
    run: AgentRun | None = None,
    llm: FakeLLM | None = None,
    image: FakeImageService | None = None,
    video: FakeVideoService | None = None,
) -> AgentContext:
    if project is None:
        project = await create_project(session)
    if run is None:
        run = await create_run(session, project_id=project.id)

    ws = DummyWsManager()

    # Create default services if not provided
    if llm is None:
        llm = FakeLLM("{}")
    if image is None:
        image = FakeImageService()
    if video is None:
        video = FakeVideoService()

    return AgentContext(
        settings=settings,
        session=session,
        ws=ws,
        project=project,
        run=run,
        llm=llm,  # type: ignore[arg-type]
        image=image,  # type: ignore[arg-type]
        video=video,  # type: ignore[arg-type]
    )
