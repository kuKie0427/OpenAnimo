from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.agents.compose import ComposeAgent
from app.agents.base import TargetIds
from app.services.doubao_video import DoubaoVideoService
from tests.agent_fixtures import FakeVideoService, make_context
from tests.factories import create_character, create_project, create_run, create_shot


class FakeImageComposer:
    def __init__(self):
        self.calls = []

    async def compose_and_save_reference_image(self, **kwargs):
        self.calls.append(("save_ref", kwargs))
        return "http://image.test/composed.png"

    async def compose_reference_image(self, **kwargs):
        self.calls.append(("ref", kwargs))
        return b"fake_bytes"


class FakeImageComposerFails:
    async def compose_and_save_reference_image(self, **kwargs):
        raise RuntimeError("compose failed")

    async def compose_reference_image(self, **kwargs):
        raise RuntimeError("compose failed")


class FakeDoubaoVideoService(DoubaoVideoService):
    def __init__(self):
        pass

    async def generate_url(self, **kwargs):
        return "http://video.test/doubao.mp4"

    async def merge_urls(self, video_urls):
        return "http://video.test/merged.mp4"


@pytest.mark.asyncio
async def test_compose_agent_generates_videos(test_session, test_settings):
    project = await create_project(test_session)
    run = await create_run(test_session, project_id=project.id)
    await create_character(test_session, project_id=project.id, image_url="http://img.test/char.png")
    shot = await create_shot(
        test_session,
        project_id=project.id,
        image_url="http://img.test/shot.png",
        video_url=None,
    )
    await test_session.commit()

    video = FakeVideoService(url="http://video.test/shot1.mp4")
    ctx = await make_context(test_session, test_settings, project=project, run=run, video=video)
    agent = ComposeAgent()
    agent.image_composer = FakeImageComposer()

    await agent.run(ctx)

    await test_session.refresh(shot)
    assert shot.video_url == "http://video.test/shot1.mp4"


@pytest.mark.asyncio
async def test_compose_agent_merge_videos(test_session, test_settings):
    project = await create_project(test_session)
    run = await create_run(test_session, project_id=project.id)
    await create_shot(
        test_session,
        project_id=project.id,
        video_url="http://video.test/s1.mp4",
        duration=5.0,
    )
    await create_shot(
        test_session,
        project_id=project.id,
        video_url="http://video.test/s2.mp4",
        duration=5.0,
    )
    await test_session.commit()

    video = FakeVideoService(merged_url="http://video.test/merged.mp4")
    ctx = await make_context(test_session, test_settings, project=project, run=run, video=video)
    agent = ComposeAgent()
    agent.image_composer = FakeImageComposer()

    await agent._merge_videos(ctx)

    await test_session.refresh(project)
    assert project.video_url == "http://video.test/merged.mp4"
    assert project.status == "ready"


@pytest.mark.asyncio
async def test_compose_agent_no_videos_to_generate(test_session, test_settings):
    project = await create_project(test_session)
    run = await create_run(test_session, project_id=project.id)
    await create_shot(
        test_session,
        project_id=project.id,
        video_url="http://video.test/already.mp4",
    )
    await test_session.commit()

    video = FakeVideoService()
    ctx = await make_context(test_session, test_settings, project=project, run=run, video=video)
    agent = ComposeAgent()

    count, _ = await agent._generate_videos(ctx)
    assert count == 0


@pytest.mark.asyncio
async def test_compose_agent_no_shots_to_merge(test_session, test_settings):
    project = await create_project(test_session)
    run = await create_run(test_session, project_id=project.id)
    await test_session.commit()

    video = FakeVideoService()
    ctx = await make_context(test_session, test_settings, project=project, run=run, video=video)
    agent = ComposeAgent()

    await agent._merge_videos(ctx)

    msg_events = [e for pid, e in ctx.ws.events if e["type"] == "run_message"]
    assert any("没有可拼接" in e["data"]["content"] for e in msg_events)


@pytest.mark.asyncio
async def test_compose_agent_blocking_clips_prevents_merge(test_session, test_settings, monkeypatch):
    project = await create_project(test_session)
    run = await create_run(test_session, project_id=project.id)
    await test_session.commit()

    fake_blocking = [{"shot_id": 1, "order": 1, "status": "pending", "reason": "no video"}]
    monkeypatch.setattr(
        "app.agents.compose.collect_project_blocking_clips",
        AsyncMock(return_value=fake_blocking),
    )

    video = FakeVideoService()
    ctx = await make_context(test_session, test_settings, project=project, run=run, video=video)
    agent = ComposeAgent()

    await agent._merge_videos(ctx)

    msg_events = [e for pid, e in ctx.ws.events if e["type"] == "run_message"]
    assert any("未满足拼接条件" in e["data"]["content"] for e in msg_events)


@pytest.mark.asyncio
async def test_compose_agent_existing_video_full_mode_skips(test_session, test_settings, monkeypatch):
    project = await create_project(test_session, status="ready")
    project.video_url = "http://video.test/old.mp4"
    run = await create_run(test_session, project_id=project.id)
    await test_session.commit()

    video = FakeVideoService()
    ctx = await make_context(test_session, test_settings, project=project, run=run, video=video)
    ctx.rerun_mode = "full"
    agent = ComposeAgent()

    monkeypatch.setattr(
        "app.agents.compose.collect_project_blocking_clips",
        AsyncMock(return_value=[]),
    )

    await agent._merge_videos(ctx)

    msg_events = [e for pid, e in ctx.ws.events if e["type"] == "run_message"]
    assert any("已有最终视频" in e["data"]["content"] for e in msg_events)


@pytest.mark.asyncio
async def test_compose_agent_video_generation_failure(test_session, test_settings):
    project = await create_project(test_session)
    run = await create_run(test_session, project_id=project.id)
    await create_shot(
        test_session,
        project_id=project.id,
        image_url="http://img.test/shot.png",
        video_url=None,
    )
    await test_session.commit()

    class FailingVideoService:
        async def generate_url(self, **kwargs):
            raise RuntimeError("video API down")

        async def merge_urls(self, video_urls):
            return "/static/videos/merged.mp4"

    ctx = await make_context(test_session, test_settings, project=project, run=run, video=FailingVideoService())
    agent = ComposeAgent()
    agent.image_composer = FakeImageComposer()

    await agent.run(ctx)

    msg_events = [e for pid, e in ctx.ws.events if e["type"] == "run_message"]
    assert any("视频生成失败" in e["data"]["content"] for e in msg_events)


@pytest.mark.asyncio
async def test_compose_agent_merge_failure(test_session, test_settings, monkeypatch):
    project = await create_project(test_session)
    run = await create_run(test_session, project_id=project.id)
    await create_shot(
        test_session,
        project_id=project.id,
        video_url="http://video.test/s1.mp4",
    )
    await test_session.commit()

    class FailingMergeVideo:
        async def generate_url(self, **kwargs):
            return "http://video.test/v.mp4"

        async def merge_urls(self, video_urls):
            raise RuntimeError("merge failed")

    ctx = await make_context(test_session, test_settings, project=project, run=run, video=FailingMergeVideo())
    agent = ComposeAgent()

    monkeypatch.setattr(
        "app.agents.compose.collect_project_blocking_clips",
        AsyncMock(return_value=[]),
    )

    await agent._merge_videos(ctx)

    msg_events = [e for pid, e in ctx.ws.events if e["type"] == "run_message"]
    assert any("拼接失败" in e["data"]["content"] for e in msg_events)


@pytest.mark.asyncio
async def test_compose_agent_target_ids_filter(test_session, test_settings):
    project = await create_project(test_session)
    run = await create_run(test_session, project_id=project.id)
    shot1 = await create_shot(test_session, project_id=project.id, image_url="http://img/1.png", video_url=None)
    shot2 = await create_shot(test_session, project_id=project.id, image_url="http://img/2.png", video_url=None)
    await test_session.commit()

    video = FakeVideoService(url="http://video.test/new.mp4")
    ctx = await make_context(test_session, test_settings, project=project, run=run, video=video)
    ctx.target_ids = TargetIds(shot_ids=[shot1.id])
    agent = ComposeAgent()
    agent.image_composer = FakeImageComposer()

    count, _ = await agent._generate_videos(ctx)

    assert count == 1
    await test_session.refresh(shot1)
    await test_session.refresh(shot2)
    assert shot1.video_url is not None
    assert shot2.video_url is None


@pytest.mark.asyncio
async def test_compose_agent_no_video_urls_to_merge(test_session, test_settings, monkeypatch):
    project = await create_project(test_session)
    run = await create_run(test_session, project_id=project.id)
    await create_shot(test_session, project_id=project.id, video_url=None)
    await test_session.commit()

    video = FakeVideoService()
    ctx = await make_context(test_session, test_settings, project=project, run=run, video=video)
    agent = ComposeAgent()

    monkeypatch.setattr(
        "app.agents.compose.collect_project_blocking_clips",
        AsyncMock(return_value=[]),
    )

    await agent._merge_videos(ctx)

    msg_events = [e for pid, e in ctx.ws.events if e["type"] == "run_message"]
    assert any("没有可拼接" in e["data"]["content"] for e in msg_events)


@pytest.mark.asyncio
async def test_compose_agent_project_not_persisted_raises(test_session, test_settings):
    from types import SimpleNamespace

    project = SimpleNamespace(id=None, style="anime", video_url=None, status="draft")
    run = await create_run(test_session, project_id=1)
    ctx = await make_context(test_session, test_settings, run=run)
    ctx.project = project

    agent = ComposeAgent()

    with pytest.raises(RuntimeError, match="persisted"):
        await agent._merge_videos(ctx)


@pytest.mark.asyncio
async def test_compose_agent_image_composer_fails_fallback(test_session, test_settings):
    project = await create_project(test_session)
    run = await create_run(test_session, project_id=project.id)
    await create_shot(
        test_session,
        project_id=project.id,
        image_url="http://img.test/shot.png",
        video_url=None,
    )
    await test_session.commit()

    video = FakeVideoService(url="http://video.test/v.mp4")
    ctx = await make_context(test_session, test_settings, project=project, run=run, video=video)
    agent = ComposeAgent()
    agent.image_composer = FakeImageComposerFails()

    count, _ = await agent._generate_videos(ctx)
    assert count == 1


def test_build_video_prompt():
    from app.models.project import Character as CharModel, Shot as ShotModel

    agent = ComposeAgent()
    shot = ShotModel(id=1, project_id=1, order=1, description="test", prompt="zoom in", scene=None, action=None, expression=None, camera=None, lighting=None, dialogue=None, sfx=None, duration=None, image_prompt=None, image_url=None, video_url=None, character_ids=[])
    chars: list[CharModel] = []
    result = agent._build_video_prompt(shot, chars, style="anime")
    assert "zoom in" in result
    assert "anime" in result


def test_build_video_prompt_with_characters():
    from app.models.project import Character as CharModel, Shot as ShotModel

    agent = ComposeAgent()
    shot = ShotModel(id=1, project_id=1, order=1, description="test", prompt=None, scene=None, action=None, expression=None, camera=None, lighting=None, dialogue=None, sfx=None, duration=None, image_prompt=None, image_url=None, video_url=None, character_ids=[])
    char = CharModel(id=1, project_id=1, name="Hero", description="brave warrior", image_url=None)
    result = agent._build_video_prompt(shot, [char], style="cinematic")
    assert "Hero" in result
    assert "cinematic" in result


def test_get_duration_with_valid_duration():
    from app.models.project import Shot as ShotModel

    agent = ComposeAgent()
    shot = ShotModel(id=1, project_id=1, order=1, description="test", duration=8.0, prompt=None, scene=None, action=None, expression=None, camera=None, lighting=None, dialogue=None, sfx=None, image_prompt=None, image_url=None, video_url=None, character_ids=[])
    assert agent._get_duration(shot, 5.0) == 8.0


def test_get_duration_with_default():
    from app.models.project import Shot as ShotModel

    agent = ComposeAgent()
    shot = ShotModel(id=1, project_id=1, order=1, description="test", duration=None, prompt=None, scene=None, action=None, expression=None, camera=None, lighting=None, dialogue=None, sfx=None, image_prompt=None, image_url=None, video_url=None, character_ids=[])
    assert agent._get_duration(shot, 5.0) == 5.0


def test_get_duration_with_zero():
    from app.models.project import Shot as ShotModel

    agent = ComposeAgent()
    shot = ShotModel(id=1, project_id=1, order=1, description="test", duration=0, prompt=None, scene=None, action=None, expression=None, camera=None, lighting=None, dialogue=None, sfx=None, image_prompt=None, image_url=None, video_url=None, character_ids=[])
    assert agent._get_duration(shot, 7.0) == 7.0


@pytest.mark.asyncio
async def test_compose_agent_blocking_clips_with_existing_video(test_session, test_settings, monkeypatch):
    project = await create_project(test_session, status="ready")
    project.video_url = "http://video.test/old.mp4"
    run = await create_run(test_session, project_id=project.id)
    await test_session.commit()

    fake_blocking = [{"shot_id": 1, "order": 1, "status": "pending", "reason": "no video"}]
    monkeypatch.setattr(
        "app.agents.compose.collect_project_blocking_clips",
        AsyncMock(return_value=fake_blocking),
    )

    video = FakeVideoService()
    ctx = await make_context(test_session, test_settings, project=project, run=run, video=video)
    ctx.rerun_mode = "incremental"
    agent = ComposeAgent()

    await agent._merge_videos(ctx)

    await test_session.refresh(project)
    assert project.status == "superseded"


@pytest.mark.asyncio
async def test_compose_agent_run_no_videos_skips_merge(test_session, test_settings):
    project = await create_project(test_session)
    run = await create_run(test_session, project_id=project.id)
    await create_shot(
        test_session,
        project_id=project.id,
        video_url="http://video.test/already.mp4",
    )
    await test_session.commit()

    video = FakeVideoService()
    ctx = await make_context(test_session, test_settings, project=project, run=run, video=video)
    agent = ComposeAgent()

    await agent.run(ctx)

    msg_events = [e for pid, e in ctx.ws.events if e["type"] == "run_message"]
    assert any("无视频可合成" in e["data"]["content"] for e in msg_events)


@pytest.mark.asyncio
async def test_compose_agent_doubao_reference_mode(test_session, test_settings):
    project = await create_project(test_session)
    run = await create_run(test_session, project_id=project.id)
    char = await create_character(test_session, project_id=project.id, image_url="http://img/char.png")
    shot = await create_shot(
        test_session,
        project_id=project.id,
        image_url="http://img/shot.png",
        video_url=None,
    )
    shot.approved_character_ids = [char.id]
    await test_session.commit()

    video = FakeDoubaoVideoService()
    ctx = await make_context(test_session, test_settings, project=project, run=run, video=video)
    object.__setattr__(ctx.settings, "use_i2v", lambda: True)
    ctx.settings.video_image_mode = "reference"
    ctx.settings.doubao_video_duration = 5
    ctx.settings.doubao_video_ratio = "16:9"
    ctx.settings.doubao_generate_audio = False

    composer = FakeImageComposer()
    agent = ComposeAgent()
    agent.image_composer = composer

    await agent._generate_videos(ctx)

    await test_session.refresh(shot)
    assert shot.video_url == "http://video.test/doubao.mp4"
    assert any(c[0] == "save_ref" for c in composer.calls)


@pytest.mark.asyncio
async def test_compose_agent_total_duration_only_counts_this_run(
    test_session, test_settings,
):
    """Regression: total_duration must include ONLY shots generated in this run,
    not pre-existing shots with video_url. Prevents per-run video cost from
    accumulating across re-runs.
    """
    project = await create_project(test_session)
    run = await create_run(test_session, project_id=project.id)
    await create_shot(
        test_session,
        project_id=project.id,
        image_url="http://img/old.png",
        video_url="http://video.test/old.mp4",
        duration=99.0,
    )
    new_shot = await create_shot(
        test_session,
        project_id=project.id,
        image_url="http://img/new.png",
        video_url=None,
        duration=None,
    )
    await test_session.commit()

    video = FakeDoubaoVideoService()
    ctx = await make_context(test_session, test_settings, project=project, run=run, video=video)
    object.__setattr__(ctx.settings, "use_i2v", lambda: True)
    ctx.settings.video_image_mode = "first_frame"
    ctx.settings.doubao_video_duration = 7
    ctx.settings.doubao_video_ratio = "16:9"
    ctx.settings.doubao_generate_audio = False

    agent = ComposeAgent()
    agent.image_composer = FakeImageComposer()

    count, total_duration = await agent._generate_videos(ctx)

    assert count == 1
    assert total_duration == 7.0
    await test_session.refresh(new_shot)
    assert new_shot.duration == 7.0


@pytest.mark.asyncio
async def test_compose_agent_doubao_first_frame_mode(test_session, test_settings):
    project = await create_project(test_session)
    run = await create_run(test_session, project_id=project.id)
    shot = await create_shot(
        test_session,
        project_id=project.id,
        image_url="http://img/shot.png",
        video_url=None,
    )
    await test_session.commit()

    video = FakeDoubaoVideoService()
    ctx = await make_context(test_session, test_settings, project=project, run=run, video=video)
    object.__setattr__(ctx.settings, "use_i2v", lambda: True)
    ctx.settings.video_image_mode = "first_frame"
    ctx.settings.doubao_video_duration = 5
    ctx.settings.doubao_video_ratio = "16:9"
    ctx.settings.doubao_generate_audio = False

    agent = ComposeAgent()
    agent.image_composer = FakeImageComposer()

    await agent._generate_videos(ctx)

    await test_session.refresh(shot)
    assert shot.video_url == "http://video.test/doubao.mp4"


@pytest.mark.asyncio
async def test_compose_agent_non_doubao_reference_mode(test_session, test_settings):
    project = await create_project(test_session)
    run = await create_run(test_session, project_id=project.id)
    char = await create_character(test_session, project_id=project.id, image_url="http://img/char.png")
    shot = await create_shot(
        test_session,
        project_id=project.id,
        image_url="http://img/shot.png",
        video_url=None,
    )
    shot.approved_character_ids = [char.id]
    await test_session.commit()

    video = FakeVideoService(url="http://video.test/non_doubao.mp4")
    ctx = await make_context(test_session, test_settings, project=project, run=run, video=video)
    object.__setattr__(ctx.settings, "use_i2v", lambda: True)
    ctx.settings.video_image_mode = "reference"

    composer = FakeImageComposer()
    agent = ComposeAgent()
    agent.image_composer = composer

    await agent._generate_videos(ctx)

    await test_session.refresh(shot)
    assert shot.video_url == "http://video.test/non_doubao.mp4"
    assert any(c[0] == "ref" for c in composer.calls)


@pytest.mark.asyncio
async def test_compose_agent_non_doubao_first_frame_mode(test_session, test_settings):
    project = await create_project(test_session)
    run = await create_run(test_session, project_id=project.id)
    shot = await create_shot(
        test_session,
        project_id=project.id,
        image_url="http://img/shot.png",
        video_url=None,
    )
    await test_session.commit()

    video = FakeVideoService(url="http://video.test/non_doubao.mp4")
    ctx = await make_context(test_session, test_settings, project=project, run=run, video=video)
    object.__setattr__(ctx.settings, "use_i2v", lambda: True)
    ctx.settings.video_image_mode = "first_frame"

    composer = FakeImageComposer()
    agent = ComposeAgent()
    agent.image_composer = composer

    await agent._generate_videos(ctx)

    await test_session.refresh(shot)
    assert shot.video_url == "http://video.test/non_doubao.mp4"
    assert any(c[0] == "ref" for c in composer.calls)
