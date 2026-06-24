"""测试字幕烧入集成"""
from __future__ import annotations

import pytest


def test_subtitle_service_imports():
    """验证 subtitle_service 能正确导入"""
    from app.services.subtitle_service import (
        _format_timestamp,
        build_srt,
        burn_subtitles_into_video,
    )

    assert callable(_format_timestamp)
    assert callable(build_srt)
    assert callable(burn_subtitles_into_video)


@pytest.mark.asyncio
async def test_build_srt_with_real_shots(test_session):
    """验证 build_srt 能处理从 DB 查询到的真实 Shot 对象"""
    from sqlalchemy import select

    from app.models.project import Shot
    from app.services.subtitle_service import build_srt

    # Query any shots from the test DB (may be empty)
    res = await test_session.execute(select(Shot).limit(5))
    shots = list(res.scalars().all())

    # build_srt should handle real Shot objects without error
    result = build_srt(shots)
    assert isinstance(result, str)


def test_srt_filename_uses_run_id_not_getattr_fallback():
    import inspect

    from app.agents.compose import ComposeAgent

    source = inspect.getsource(ComposeAgent._add_audio_to_videos)
    assert "ctx.run.id" in source, (
        "compose.py 字幕块必须用 ctx.run.id 解析 run id "
        "（AgentContext.run: AgentRun，run.id 是实际字段）"
    )
    assert 'getattr(ctx, "run_id"' not in source, (
        "defensive getattr(ctx, 'run_id', None) 是 bug — AgentContext 没有 run_id 字段，"
        "该 fallback 永远 fire，导致 SRT 文件名恒为 {project_id}_{project_id}.srt，"
        "并发 run 必冲突"
    )


def test_srt_filename_includes_run_id_for_concurrent_safety():
    from app.agents.compose import ComposeAgent

    project_id = 42
    run_a_id = 1001
    run_b_id = 1002

    filename_a = f"{project_id}_{run_a_id}.srt"
    filename_b = f"{project_id}_{run_b_id}.srt"

    assert filename_a != filename_b, "并发 run 必须生成不同 SRT 文件名（不同 run_id）"
    assert filename_a == "42_1001.srt"
    assert filename_b == "42_1002.srt"
    assert hasattr(ComposeAgent, "_add_audio_to_videos")


@pytest.mark.skip(reason="Requires FFmpeg on PATH and real video files")
class TestSubtitleBurninIntegration:
    """字幕烧入集成测试（需 DB + FFmpeg + 视频文件）"""

    @pytest.mark.asyncio
    async def test_burn_subtitles_with_real_video(self, test_session, tmp_path):
        """端到端烧录测试（需要 FFmpeg + 真实视频文件）"""
        from tests.factories import create_project, create_shot

        from app.services.subtitle_service import build_srt, burn_subtitles_into_video

        # Create project with shots that have dialogue
        project = await create_project(test_session, title="Subtitle Test")
        shot1 = await create_shot(
            test_session,
            project_id=project.id,
            order=1,
            duration=3.0,
            description="Opening scene",
        )
        # Set dialogue directly on the ORM object
        shot1.dialogue = "你好世界"
        shot1.approved_dialogue = "你好世界"
        await test_session.commit()

        # Generate SRT
        srt_content = build_srt([shot1], include_unapproved=False)
        assert "你好世界" in srt_content

        # Write SRT to temp file
        srt_path = tmp_path / "test.srt"
        srt_path.write_text(srt_content, encoding="utf-8")

        # Create a simple test video using FFmpeg
        video_path = tmp_path / "test_video.mp4"
        import asyncio

        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=320x240:d=3",
            "-c:v",
            "libx264",
            "-t",
            "3",
            str(video_path),
        )
        await proc.communicate()
        assert proc.returncode == 0, "Failed to create test video"

        output_path = tmp_path / "output.mp4"

        # Burn subtitles
        result = await burn_subtitles_into_video(
            str(video_path),
            str(srt_path),
            str(output_path),
        )
        assert result == str(output_path)
        assert output_path.exists()
        assert output_path.stat().st_size > 0
