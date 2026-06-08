"""Targeted unit tests for orchestrator helpers, redis utilities and cleanup logic."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any

import pytest

from app.agents.orchestrator import (
    GenerationOrchestrator,
    _next_phase2_stage,
    _resume_agent_for_stage,
    _video_generation_skipped_in_result,
)
from app.orchestration.redis import (
    clear_awaiting_payload,
    clear_confirm_event_redis,
    get_awaiting_payload,
    get_redis,
    store_awaiting_payload,
    trigger_confirm_redis,
    wait_for_confirm_redis,
)
from app.config import Settings
from app.models.project import Character, Shot
from tests.factories import create_project, create_run

# ---------------------------------------------------------------------------
# Pure helper unit tests
# ---------------------------------------------------------------------------


class TestPureHelpers:
    def test_next_phase2_stage_known(self):
        assert _next_phase2_stage("plan_characters") == "characters_approval"
        assert _next_phase2_stage("characters_approval") == "plan_shots"
        assert _next_phase2_stage("render_characters") == "character_images_approval"

    def test_next_phase2_stage_unknown_returns_none(self):
        assert _next_phase2_stage("not-a-stage") is None
        assert _next_phase2_stage(None) is None

    def test_resume_agent_for_stage_known(self):
        assert _resume_agent_for_stage("plan_characters") == "plan"
        assert _resume_agent_for_stage("characters_approval") == "plan"
        assert _resume_agent_for_stage("render_characters") == "render"
        assert _resume_agent_for_stage("character_images_approval") == "render"
        assert _resume_agent_for_stage("compose_videos") == "compose"

    def test_resume_agent_for_unknown_stage_falls_back(self):
        assert _resume_agent_for_stage("unknown") == "plan"
        assert _resume_agent_for_stage(None) == "plan"
        assert _resume_agent_for_stage(123) == "plan"

    def test_video_generation_skipped_in_result_dict(self):
        assert _video_generation_skipped_in_result({"video_generation_skipped": True}) is True
        assert _video_generation_skipped_in_result({"video_generation_skipped": False}) is False
        assert _video_generation_skipped_in_result({}) is False

    def test_video_generation_skipped_in_result_non_dict(self):
        assert _video_generation_skipped_in_result(None) is False
        assert _video_generation_skipped_in_result("string") is False
        assert _video_generation_skipped_in_result([1, 2, 3]) is False


# ---------------------------------------------------------------------------
# Redis helpers (using fake redis client)
# ---------------------------------------------------------------------------


class _FakeRedis:
    """Minimal in-memory async redis stub that supports the ops the helpers use."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.published: list[tuple[str, str]] = []

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.store[key] = value

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def delete(self, key: str) -> int:
        return 1 if self.store.pop(key, None) is not None else 0

    async def publish(self, channel: str, message: str) -> int:
        self.published.append((channel, message))
        return 1

    async def expire(self, key: str, ttl: int) -> None:
        # no-op for tests
        return None

    def pubsub(self):
        return _FakePubSub(self)


class _FakePubSub:
    def __init__(self, redis: _FakeRedis) -> None:
        self.redis = redis
        self._subscribed: set[str] = set()

    async def subscribe(self, *channels: str) -> None:
        self._subscribed.update(channels)

    async def unsubscribe(self, *channels: str) -> None:
        for c in channels:
            self._subscribed.discard(c)

    async def get_message(self, ignore_subscribe_messages: bool = True, timeout: float = 1.0):
        await asyncio.sleep(0)
        return None

    async def close(self) -> None:
        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return None


@pytest.fixture
async def fake_redis(monkeypatch):
    fake = _FakeRedis()

    async def _factory():
        return fake

    monkeypatch.setattr("app.orchestration.redis.get_redis", _factory)
    return fake


@pytest.mark.asyncio
async def test_get_redis_returns_singleton(monkeypatch):
    """get_redis() module-level should reuse one client instance."""
    import app.orchestration.redis as redis_mod

    monkeypatch.setattr(redis_mod, "_redis_client", None)

    created: list[Any] = []

    class _Client:
        async def ping(self):
            return True

    def _from_url(*_a, **_kw):
        c = _Client()
        created.append(c)
        return c

    fake_redis_module = SimpleNamespace(from_url=_from_url, Redis=object)
    monkeypatch.setattr(redis_mod, "redis", fake_redis_module)

    a = await get_redis()
    b = await get_redis()
    assert a is b
    assert len(created) == 1


@pytest.mark.asyncio
async def test_store_awaiting_payload_writes_json(fake_redis):
    payload = {"foo": "bar", "n": 1}
    await store_awaiting_payload(123, payload)
    raw = fake_redis.store["openanimo:awaiting:123"]
    assert json.loads(raw) == payload


@pytest.mark.asyncio
async def test_store_awaiting_payload_swallow_redis_error(monkeypatch):
    async def _raising():
        raise RuntimeError("redis down")

    monkeypatch.setattr("app.orchestration.redis.get_redis", _raising)

    # Should not raise even when redis is unreachable.
    await store_awaiting_payload(1, {"a": 1})


@pytest.mark.asyncio
async def test_clear_awaiting_payload_swallow_redis_error(monkeypatch):
    async def _raising():
        raise RuntimeError("redis down")

    monkeypatch.setattr("app.orchestration.redis.get_redis", _raising)
    await clear_awaiting_payload(1)


@pytest.mark.asyncio
async def test_get_awaiting_payload_returns_dict(fake_redis):
    fake_redis.store["openanimo:awaiting:7"] = json.dumps({"x": 9})
    out = await get_awaiting_payload(7)
    assert out == {"x": 9}


@pytest.mark.asyncio
async def test_get_awaiting_payload_redis_error_returns_none(monkeypatch):
    async def _raising():
        raise RuntimeError("redis down")

    monkeypatch.setattr("app.orchestration.redis.get_redis", _raising)
    assert await get_awaiting_payload(1) is None


@pytest.mark.asyncio
async def test_get_awaiting_payload_missing_key_returns_none(fake_redis):
    assert await get_awaiting_payload(404) is None


@pytest.mark.asyncio
async def test_get_awaiting_payload_invalid_json_returns_none(fake_redis):
    fake_redis.store["openanimo:awaiting:42"] = "not-json"
    assert await get_awaiting_payload(42) is None


@pytest.mark.asyncio
async def test_clear_awaiting_payload_removes_key(fake_redis):
    fake_redis.store["openanimo:awaiting:5"] = "{}"
    await clear_awaiting_payload(5)
    assert "openanimo:awaiting:5" not in fake_redis.store


@pytest.mark.asyncio
async def test_clear_confirm_event_redis_removes_key(fake_redis):
    fake_redis.store["openanimo:confirm:9"] = "1"
    await clear_confirm_event_redis(9)
    assert "openanimo:confirm:9" not in fake_redis.store


@pytest.mark.asyncio
async def test_trigger_confirm_redis_publishes(fake_redis):
    ok = await trigger_confirm_redis(11)
    assert ok is True
    assert fake_redis.store["openanimo:confirm:11"] == "1"
    assert fake_redis.published == [("openanimo:confirm_channel:11", "confirm")]


@pytest.mark.asyncio
async def test_wait_for_confirm_redis_returns_true_when_already_set(fake_redis):
    fake_redis.store["openanimo:confirm:33"] = "1"
    ok = await wait_for_confirm_redis(33, timeout=1)
    assert ok is True


@pytest.mark.asyncio
async def test_wait_for_confirm_redis_returns_false_on_timeout(monkeypatch, fake_redis):
    """Timeout path: no confirm key set, no published message, finishes within budget."""
    ok = await wait_for_confirm_redis(99, timeout=1)
    assert ok is False


# ---------------------------------------------------------------------------
# Cleanup tests
# ---------------------------------------------------------------------------


class _RecordingWs:
    def __init__(self) -> None:
        self.events: list[tuple[int, dict]] = []

    async def send_event(self, project_id: int, event: dict) -> None:
        self.events.append((project_id, event))


@pytest.fixture
def test_settings_minimal():
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        anthropic_api_key="test",
        image_api_key="test",
        video_api_key="test",
    )


@pytest.fixture
async def orch_with_session(test_session, test_settings_minimal, monkeypatch):
    """Build orchestrator instance using a real test_session."""

    # Ensure cleanup operations don't try to delete real disk files.
    monkeypatch.setattr("app.agents.orchestrator.delete_files", lambda _paths: None)

    ws = _RecordingWs()
    orch = GenerationOrchestrator(settings=test_settings_minimal, ws=ws, session=test_session)
    return orch, ws


@pytest.mark.asyncio
async def test_cleanup_full_mode_plan_deletes_all(test_session, orch_with_session):
    orch, ws = orch_with_session
    project = await create_project(test_session)
    test_session.add(Character(project_id=project.id, name="A", description="desc"))
    test_session.add(Shot(project_id=project.id, order=0, description="s0"))
    await test_session.commit()

    await orch._cleanup_for_rerun(project.id, "plan", mode="full")

    chars = (await test_session.execute(__import__("sqlalchemy").select(Character))).scalars().all()
    shots = (await test_session.execute(__import__("sqlalchemy").select(Shot))).scalars().all()
    assert chars == []
    assert shots == []
    # Should fire data_cleared event
    assert any(evt[1]["type"] == "data_cleared" for evt in ws.events)


@pytest.mark.asyncio
async def test_cleanup_full_mode_render_clears_images(test_session, orch_with_session, monkeypatch):
    orch, ws = orch_with_session
    project = await create_project(test_session)
    char = Character(project_id=project.id, name="A", description="d", image_url="u")
    shot = Shot(project_id=project.id, order=0, description="s", image_url="i", video_url="v")
    test_session.add(char)
    test_session.add(shot)
    await test_session.commit()

    await orch._cleanup_for_rerun(project.id, "render", mode="full")

    await test_session.refresh(char)
    await test_session.refresh(shot)
    assert char.image_url is None
    assert shot.image_url is None
    assert shot.video_url is None
    # full mode for render does not set cleared_types -> no event
    assert not any(evt[1]["type"] == "data_cleared" for evt in ws.events)


@pytest.mark.asyncio
async def test_cleanup_full_mode_render_clears_assets(test_session, orch_with_session):
    orch, _ws = orch_with_session
    project = await create_project(test_session)
    shot = Shot(project_id=project.id, order=0, description="s", image_url="i", video_url="v")
    test_session.add(shot)
    await test_session.commit()

    await orch._cleanup_for_rerun(project.id, "render", mode="full")

    await test_session.refresh(shot)
    assert shot.image_url is None
    assert shot.video_url is None


@pytest.mark.asyncio
async def test_cleanup_full_mode_compose_clears_only_video(test_session, orch_with_session):
    orch, _ws = orch_with_session
    project = await create_project(test_session)
    shot = Shot(project_id=project.id, order=0, description="s", image_url="keep", video_url="v")
    test_session.add(shot)
    await test_session.commit()

    await orch._cleanup_for_rerun(project.id, "compose", mode="full")

    await test_session.refresh(shot)
    assert shot.image_url == "keep"
    assert shot.video_url is None


@pytest.mark.asyncio
async def test_cleanup_unknown_agent_raises(test_session, orch_with_session):
    orch, _ws = orch_with_session
    project = await create_project(test_session)
    with pytest.raises(ValueError, match="Unsupported start_agent"):
        await orch._cleanup_for_rerun(project.id, "bogus", mode="full")


@pytest.mark.asyncio
async def test_cleanup_incremental_mode_unknown_agent_raises(test_session, orch_with_session):
    orch, _ws = orch_with_session
    project = await create_project(test_session)
    with pytest.raises(ValueError, match="Unsupported start_agent"):
        await orch._cleanup_for_rerun(project.id, "bogus", mode="incremental")


@pytest.mark.asyncio
async def test_cleanup_incremental_mode_plan_clears_assets(test_session, orch_with_session):
    orch, ws = orch_with_session
    project = await create_project(test_session)
    char = Character(project_id=project.id, name="A", description="d", image_url="u")
    shot = Shot(project_id=project.id, order=0, description="s", image_url="i", video_url="v")
    test_session.add(char)
    test_session.add(shot)
    await test_session.commit()

    await orch._cleanup_for_rerun(project.id, "plan", mode="incremental")

    await test_session.refresh(char)
    await test_session.refresh(shot)
    assert char.image_url is None
    assert shot.image_url is None
    assert shot.video_url is None
    # Incremental mode does NOT delete data structure -> char/shot still exist
    chars = (await test_session.execute(__import__("sqlalchemy").select(Character))).scalars().all()
    shots = (await test_session.execute(__import__("sqlalchemy").select(Shot))).scalars().all()
    assert len(chars) == 1
    assert len(shots) == 1
    # Incremental mode never emits data_cleared event
    assert not any(evt[1]["type"] == "data_cleared" for evt in ws.events)


@pytest.mark.asyncio
async def test_cleanup_incremental_mode_compose_clears_only_video(test_session, orch_with_session):
    orch, _ws = orch_with_session
    project = await create_project(test_session)
    shot = Shot(project_id=project.id, order=0, description="s", image_url="i", video_url="v")
    test_session.add(shot)
    await test_session.commit()

    await orch._cleanup_for_rerun(project.id, "compose", mode="incremental")

    await test_session.refresh(shot)
    assert shot.image_url == "i"
    assert shot.video_url is None


# ---------------------------------------------------------------------------
# _set_run / _log
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_run_updates_fields_and_persists(test_session, orch_with_session):
    orch, _ws = orch_with_session
    project = await create_project(test_session)
    run = await create_run(test_session, project_id=project.id, status="queued")

    updated = await orch._set_run(run, status="running", progress=0.42, current_agent="x")
    assert updated.status == "running"
    assert updated.progress == 0.42
    assert updated.current_agent == "x"


@pytest.mark.asyncio
async def test_log_persists_agent_message(test_session, orch_with_session):
    from app.models.agent_run import AgentMessage
    from sqlalchemy import select

    orch, _ws = orch_with_session
    project = await create_project(test_session)
    run = await create_run(test_session, project_id=project.id, status="running")

    await orch._log(run.id, agent="orchestrator", role="system", content="hello")

    res = await test_session.execute(select(AgentMessage).where(AgentMessage.run_id == run.id))
    msgs = res.scalars().all()
    assert len(msgs) == 1
    assert msgs[0].content == "hello"
    assert msgs[0].agent == "orchestrator"
    assert msgs[0].role == "system"
