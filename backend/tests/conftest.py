from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.api.deps import get_app_settings, get_db_session, get_ws_manager, require_admin
from app.config import Settings
from app.main import create_app
from app.models import agent_run, artifact, message, project, run, stage, style_template  # noqa: F401


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        anthropic_api_key="test-key",
        image_api_key="test-key",
        video_api_key="test-key",
    )


class StubWsManager:
    def __init__(self) -> None:
        self.events: list[tuple[int, dict]] = []

    async def send_event(self, project_id: int, event: dict) -> None:
        self.events.append((project_id, event))


@pytest_asyncio.fixture(scope="function")
async def test_db_engine_sessionmaker(
    tmp_path: Path,
) -> AsyncGenerator[tuple, None]:
    """Function-scoped sqlite engine + sessionmaker.

    Shared between test_session (for direct DB writes) and closure_app
    (for route-level async_session_maker patching) so both layers see the
    same data.
    """
    db_path = tmp_path / "test.db"
    database_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        yield engine, session_maker
    finally:
        await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_db_engine_sessionmaker) -> AsyncGenerator[AsyncSession, None]:
    _, session_maker = test_db_engine_sessionmaker
    async with session_maker() as session:
        yield session


@pytest.fixture()
def shared_session_maker(test_db_engine_sessionmaker):
    """Sessionmaker shared with test_session.

    Used by closure_app fixture to patch route-level async_session_maker
    so route _task() closures hit the same sqlite db as test_session.
    """
    _, session_maker = test_db_engine_sessionmaker
    return session_maker


@pytest_asyncio.fixture(scope="function")
async def checkpoint_sessionmaker(
    tmp_path: Path,
) -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    database_url = os.environ.get("TEST_CHECKPOINT_DATABASE_URL")
    if not database_url:
        database_url = f"sqlite+aiosqlite:///{tmp_path / 'checkpoint.db'}"

    engine = create_async_engine(database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        yield session_maker
    finally:
        await engine.dispose()


@pytest.fixture()
def ws_manager() -> StubWsManager:
    return StubWsManager()


@pytest_asyncio.fixture(scope="function")
async def app(test_session: AsyncSession, test_settings: Settings, ws_manager: StubWsManager):
    app = create_app()

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield test_session

    async def override_get_settings() -> Settings:
        return test_settings

    async def override_get_ws() -> StubWsManager:
        return ws_manager

    async def override_require_admin() -> None:
        return None

    app.dependency_overrides[get_db_session] = override_get_session
    app.dependency_overrides[get_app_settings] = override_get_settings
    app.dependency_overrides[get_ws_manager] = override_get_ws
    app.dependency_overrides[require_admin] = override_require_admin
    return app


@pytest_asyncio.fixture(scope="function")
async def async_client(app):
    transport = ASGITransport(app=app)

    class _AsyncClientWithYield(AsyncClient):
        async def request(self, *args, **kwargs):
            loop = asyncio.get_running_loop()
            task = loop.create_task(super().request(*args, **kwargs))
            # ASGITransport + body-carrying requests can deadlock on this runtime
            # unless the request coroutine gets at least one scheduling slice.
            await asyncio.sleep(0.01)
            return await task

    async with _AsyncClientWithYield(transport=transport, base_url="http://test") as client:
        yield client


@asynccontextmanager
async def _no_lifespan(_: object):
    yield


@pytest.fixture()
def ws_client(app):
    app.router.lifespan_context = _no_lifespan
    return TestClient(app)


@pytest_asyncio.fixture(scope="function")
async def e2e_stub_services(monkeypatch, test_db_engine_sessionmaker):
    """E2E stub services: replace factories + Redis + PIL + face_cropper.

    Must be applied BEFORE app fixture creation so that monkeypatches
    take effect before the orchestrator code is imported.
    """
    from unittest.mock import AsyncMock
    from PIL import Image as PILImage

    # 0. Patch async_session_maker to use the test DB so background tasks share the same database
    _, session_maker = test_db_engine_sessionmaker
    monkeypatch.setattr("app.db.session.async_session_maker", session_maker)

    # 0a. Also patch modules with module-level 'from app.db.session import async_session_maker' bindings
    import app.api.v1.routes.generation as gen_mod
    import app.api.v1.routes.script as script_mod
    import app.services.agent_runner as agent_runner_mod

    monkeypatch.setattr(gen_mod, "async_session_maker", session_maker)
    monkeypatch.setattr(script_mod, "async_session_maker", session_maker)
    monkeypatch.setattr(agent_runner_mod, "async_session_maker", session_maker)

    # 1. Text factory → FakeTextService (stage-aware fake responses)
    from app.services.fake_text import FakeTextService

    monkeypatch.setattr(
        "app.services.text_factory.create_text_service",
        lambda s: FakeTextService(s),
    )

    # 2. Image factory → agent_fixtures FakeImageService (simple URL returner)
    from tests.agent_fixtures import FakeImageService as FixtureImageService

    monkeypatch.setattr(
        "app.services.image_factory.create_image_service",
        lambda s: FixtureImageService(),
    )

    # 3. Video factory → agent_fixtures FakeVideoService (simple URL returner)
    from tests.agent_fixtures import FakeVideoService as FixtureVideoService

    monkeypatch.setattr(
        "app.services.video_factory.create_video_service",
        lambda s: FixtureVideoService(),
    )

    # 4. Redis → AsyncMock (no actual Redis needed)
    monkeypatch.setattr("app.orchestration.redis.get_redis", AsyncMock)

    # 5. PIL Image.open download stub → return tiny red image
    monkeypatch.setattr(
        PILImage, "open", lambda *a, **kw: PILImage.new("RGB", (64, 64), color="red"),
    )

    # 6. face_cropper stub
    monkeypatch.setattr("app.services.face_cropper._get_face_analysis", lambda: None)

    yield
