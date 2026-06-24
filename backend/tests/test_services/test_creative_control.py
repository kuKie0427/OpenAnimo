from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.creative_control import (
    _blocking_clip_reason,
    _sanitize_ids,
    collect_project_blocking_clips,
    invalidate_character_downstream_outputs,
    invalidate_shot_clip_output,
    invalidate_shot_storyboard_outputs,
    apply_character_rerun_edits,
    infer_feedback_targets,
)


def test_sanitize_ids_deduplicates_and_ignores_invalid_values():
    assert _sanitize_ids([1, 2, 2, True, 3.0, 4.5, "x"]) == [1, 2, 3]
    assert _sanitize_ids("bad") == []


def test_blocking_clip_reason_maps_known_states():
    assert _blocking_clip_reason("missing") == "当前分镜视频尚未生成"
    assert _blocking_clip_reason("generating") == "当前分镜视频仍在生成中"
    assert _blocking_clip_reason("failed") == "当前分镜视频生成失败"
    assert _blocking_clip_reason("anything") == "当前分镜视频不可用于最终拼接"


def test_infer_feedback_targets_from_target_ids():
    data = {"target_ids": {"character_ids": [1, 1, 2], "shot_ids": [3, 4, 4]}}
    result = infer_feedback_targets(data, {})

    assert result.character_ids == [1, 2]
    assert result.shot_ids == [3, 4]


def test_infer_feedback_targets_from_analysis_and_state():
    data = {"analysis": {"target_items": ["角色A需要重做", "镜头2要修改"]}}
    state = {"characters": [{"id": 10, "name": "角色A"}], "shots": [{"id": 20, "order": 2}]}

    result = infer_feedback_targets(data, state)

    assert result.character_ids == [10]
    assert result.shot_ids == [20]


def test_infer_feedback_targets_returns_none_for_unmatched_items():
    data = {"analysis": {"target_items": ["无关内容"]}}
    assert infer_feedback_targets(data, {"characters": [], "shots": []}) is None


@pytest.mark.asyncio
async def test_apply_character_rerun_edits_updates_fields(monkeypatch):
    class DummySession:
        def __init__(self):
            self.added = []
            self.flushed = False

        def add(self, obj):
            self.added.append(obj)

        async def flush(self):
            self.flushed = True

    character = SimpleNamespace(description="old", image_url="old.png")
    session = DummySession()

    updated = await apply_character_rerun_edits(
        session, character, description="new", image_url="new.png"
    )

    assert updated.description == "new"
    assert updated.image_url == "new.png"
    assert session.flushed is True


@pytest.mark.asyncio
async def test_collect_project_blocking_clips_reports_missing_and_generating(test_session):
    from app.models.project import Project, Shot
    from app.models.agent_run import AgentRun

    project = Project(title="P", story="S", style="Style", status="draft")
    test_session.add(project)
    await test_session.flush()

    shot1 = Shot(project_id=project.id, order=1, description="A")
    shot2 = Shot(project_id=project.id, order=2, description="B", video_url="done.mp4")
    test_session.add_all([shot1, shot2])
    await test_session.flush()

    test_session.add(
        AgentRun(project_id=project.id, resource_type="shot", resource_id=shot1.id, status="running")
    )
    await test_session.commit()

    clips = await collect_project_blocking_clips(test_session, project)

    assert clips[0]["status"] == "generating"
    assert clips[0]["reason"] == "当前分镜视频仍在生成中"


@pytest.mark.asyncio
async def test_invalidate_character_downstream_outputs_clears_matching_shots(test_session):
    from app.models.project import Project, Shot

    project = Project(title="P", story="S", style="Style", status="draft")
    test_session.add(project)
    await test_session.flush()

    shot = Shot(
        project_id=project.id,
        order=1,
        description="A",
        image_url="image.png",
        video_url="video.mp4",
        character_ids=[1],
    )
    test_session.add(shot)
    await test_session.commit()

    await invalidate_character_downstream_outputs(test_session, project, 1)

    await test_session.refresh(shot)
    assert shot.image_url is None
    assert shot.video_url is None


@pytest.mark.asyncio
async def test_invalidate_shot_storyboard_outputs_clears_outputs(test_session):
    from app.models.project import Project, Shot

    project = Project(title="P", story="S", style="Style", status="draft", video_url="proj.mp4")
    test_session.add(project)
    await test_session.flush()
    shot = Shot(project_id=project.id, order=1, description="A", image_url="image.png", video_url="video.mp4")
    test_session.add(shot)
    await test_session.commit()

    await invalidate_shot_storyboard_outputs(test_session, project, shot)

    await test_session.refresh(shot)
    assert shot.image_url is None
    assert shot.video_url is None


@pytest.mark.asyncio
async def test_invalidate_shot_clip_output_marks_project_superseded(test_session):
    from app.models.project import Project

    project = Project(title="P", story="S", style="Style", status="draft", video_url="proj.mp4")
    test_session.add(project)
    await test_session.commit()

    await invalidate_shot_clip_output(test_session, project)

    await test_session.refresh(project)
    assert project.status == "superseded"
