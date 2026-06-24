# pyright: reportArgumentType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false
from __future__ import annotations

import logging
import subprocess
from typing import cast

import httpx

from sqlalchemy import select
from sqlalchemy.orm import InstrumentedAttribute

from app.agents.base import AgentContext, BaseAgent, CompletionInfo
from app.agents.utils import build_character_context
from app.models.project import Character, Shot
from app.orchestration.state import workflow_progress_for_stage
from app.services.audio_service import AudioService
from app.services.creative_control import collect_project_blocking_clips
from app.services.doubao_video import DoubaoVideoService
from app.services.image_composer import ImageComposer
from app.services.shot_binding import resolve_shot_bound_approved_characters

logger = logging.getLogger(__name__)


class ComposeAgent(BaseAgent):
    name = "compose"

    def __init__(self):
        super().__init__()
        self.image_composer = ImageComposer()

    def _build_video_prompt(self, shot: Shot, characters: list[Character], *, style: str) -> str:
        desc = shot.prompt or shot.description
        parts = [desc.strip()]
        char_context = build_character_context(characters)
        if char_context:
            parts.append(char_context)
        if style.strip():
            parts.append(f"Style: {style.strip()}")
        return ", ".join(parts)

    def _get_duration(self, shot: Shot, default_duration: float) -> float:
        if shot.duration and shot.duration > 0:
            return shot.duration
        return default_duration

    async def _generate_videos(self, ctx: AgentContext) -> tuple[int, float]:
        query = select(Shot).where(
            Shot.project_id == ctx.project_id,
            Shot.video_url.is_(None),
        )
        if ctx.target_ids and ctx.target_ids.shot_ids:
            query = query.where(Shot.id.in_(ctx.target_ids.shot_ids))
        res = await ctx.session.execute(query)
        shots = res.scalars().all()

        if not shots:
            await self.send_message(ctx, "所有分镜已有视频。")
            return 0, 0.0

        use_image_mode = ctx.settings.use_i2v()
        is_doubao = isinstance(ctx.video, DoubaoVideoService)
        default_duration = float(ctx.settings.doubao_video_duration) if is_doubao else 5.0
        image_mode = (ctx.settings.video_image_mode or "first_frame").strip().lower()

        total = len(shots)
        updated_count = 0
        total_duration = 0.0
        mode_desc = "图生视频" if use_image_mode else "文生视频"

        # Thinking: planning phase — starting video generation
        await self.send_thinking(
            ctx,
            phase="planning",
            content=f"准备为 {total} 个分镜生成视频，模式：{mode_desc}",
            details=f"视频服务商：{'豆包' if is_doubao else 'OpenAI 兼容'}",
        )

        await self.send_message(
            ctx, f"开始为 {total} 个分镜生成视频（{mode_desc}）...", progress=0.0, is_loading=True
        )

        for i, shot in enumerate(shots):
            try:
                shot_progress = i / max(total, 1)
                await self.send_progress_batch(
                    ctx, total=total, current=i, message=f"   正在生成视频 {i + 1}/{total}..."
                )
                await ctx.ws.send_event(
                    ctx.project_id,
                    {
                        "type": "run_progress",
                        "data": {
                            "run_id": ctx.run.id,
                            "current_agent": "compose",
                            "current_stage": "compose",
                            "stage": "compose",
                            "next_stage": None,
                            "progress": workflow_progress_for_stage(
                                "compose", within_stage=shot_progress
                            ),
                        },
                    },
                )
                characters = await resolve_shot_bound_approved_characters(ctx.session, shot)
                video_prompt = self._build_video_prompt(shot, characters, style=ctx.project.style)

                # Thinking: reasoning for each video
                await self.send_thinking(
                    ctx,
                    phase="reasoning",
                    content=f"分镜 #{shot.order} 视频提示词：{video_prompt[:80]}...",
                )

                duration = self._get_duration(shot, default_duration)

                if is_doubao:
                    image_url: str | None = None
                    if use_image_mode and shot.image_url:
                        if image_mode == "reference":
                            try:
                                char_image_urls = [c.image_url for c in characters if c.image_url]
                                image_url = (
                                    await self.image_composer.compose_and_save_reference_image(
                                        shot_image_url=shot.image_url,
                                        character_image_urls=char_image_urls,
                                    )
                                )
                            except (RuntimeError, ValueError, OSError):
                                image_url = shot.image_url
                        else:
                            image_url = shot.image_url

                    video_url = await ctx.video.generate_url(
                        prompt=video_prompt,
                        image_url=image_url,
                        duration=int(duration) if duration in (5, 10) else 5,
                        ratio=ctx.settings.doubao_video_ratio,
                        generate_audio=ctx.settings.doubao_generate_audio,
                    )
                else:
                    reference_image_bytes: bytes | None = None
                    if use_image_mode and shot.image_url:
                        try:
                            if image_mode == "reference":
                                char_image_urls = [c.image_url for c in characters if c.image_url]
                                reference_image_bytes = (
                                    await self.image_composer.compose_reference_image(
                                        shot_image_url=shot.image_url,
                                        character_image_urls=char_image_urls,
                                    )
                                )
                            else:
                                reference_image_bytes = (
                                    await self.image_composer.compose_reference_image(
                                        shot_image_url=shot.image_url,
                                        character_image_urls=[],
                                    )
                                )
                        except (RuntimeError, ValueError, OSError):
                            reference_image_bytes = None

                    video_url = await ctx.video.generate_url(
                        prompt=video_prompt,
                        image_bytes=reference_image_bytes,
                    )

                shot.video_url = video_url
                shot.duration = duration
                total_duration += duration
                ctx.session.add(shot)
                await ctx.session.flush()
                await self.send_shot_event(ctx, shot, "shot_updated")
                updated_count += 1
            except (RuntimeError, ValueError, httpx.HTTPError) as e:
                await self.send_message(ctx, f"镜头 {shot.order} 视频生成失败: {e}")

        await ctx.session.commit()
        return updated_count, total_duration

    async def _merge_videos(self, ctx: AgentContext) -> None:
        project_id = ctx.project_id
        if project_id is None:
            raise RuntimeError("Project must be persisted before final assembly")

        if (
            ctx.project.video_url
            and ctx.project.status != "superseded"
            and ctx.rerun_mode == "full"
        ):
            await self.send_message(ctx, "项目已有最终视频。")
            return

        blocking_clips = await collect_project_blocking_clips(ctx.session, ctx.project)
        if blocking_clips:
            if ctx.project.video_url:
                ctx.project.status = "superseded"
            ctx.session.add(ctx.project)
            await ctx.session.commit()
            await ctx.session.refresh(ctx.project)
            await self.send_message(
                ctx, "当前仍有分镜视频未满足拼接条件，请先完成这些分镜。", progress=1.0
            )
            await ctx.ws.send_event(
                project_id,
                {
                    "type": "project_updated",
                    "data": {
                        "project": {
                            "id": ctx.project_id,
                            "video_url": ctx.project.video_url,
                            "status": ctx.project.status,
                            "blocking_clips": blocking_clips,
                        }
                    },
                },
            )
            return

        shot_project_id_col = cast(InstrumentedAttribute[int], cast(object, Shot.project_id))
        shot_video_url_col = cast(InstrumentedAttribute[str | None], cast(object, Shot.video_url))
        shot_order_col = cast(InstrumentedAttribute[int], cast(object, Shot.order))
        res = await ctx.session.execute(
            select(Shot)
            .where(shot_project_id_col == project_id, shot_video_url_col.is_not(None))
            .order_by(shot_order_col.asc())
        )
        shots = res.scalars().all()

        if not shots:
            await self.send_message(ctx, "没有可拼接的分镜视频。")
            return

        video_urls = [shot.video_url for shot in shots if shot.video_url]
        if not video_urls:
            await self.send_message(ctx, "没有有效的视频 URL 可拼接。")
            return

        try:
            await self.send_message(
                ctx, f"开始拼接 {len(video_urls)} 个分镜视频...", progress=0.0, is_loading=True
            )
            merged_url = await ctx.video.merge_urls(video_urls)

            ctx.project.video_url = merged_url
            ctx.project.status = "ready"
            ctx.session.add(ctx.project)
            await ctx.session.commit()
            await ctx.session.refresh(ctx.project)

            await ctx.ws.send_event(
                project_id,
                {
                    "type": "project_updated",
                    "data": {
                        "project": {
                            "id": ctx.project_id,
                            "video_url": merged_url,
                            "status": ctx.project.status,
                            "blocking_clips": [],
                        }
                    },
                },
            )

            summary = f"将{len(video_urls)}个分镜拼接为完整视频"
            first_shot = shots[0] if shots else None
            shot_hint = (
                f"「{first_shot.description[:15]}…」"
                if first_shot and first_shot.description
                else ""
            )
            ctx.completion_info = CompletionInfo(
                completed=f"已将 {len(video_urls)} 个分镜拼接为完整视频",
                next="您的漫剧已经准备就绪！可以下载或分享了。",
                question="最终视频效果满意吗？",
            )
            await self.send_message(
                ctx,
                f"漫剧制作完成！{shot_hint}等 {len(video_urls)} 个分镜已拼接为完整视频。",
                summary=summary,
                progress=1.0,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, RuntimeError, OSError) as e:
            await self.send_message(ctx, f"视频拼接失败: {e}。您可以稍后手动拼接。", progress=1.0)

    async def _add_audio_to_videos(self, ctx: AgentContext) -> None:
        """为分镜视频添加 TTS 配音 + BGM 背景音乐

        容错设计：
        - TTS 失败时跳过，仅加 BGM
        - BGM 失败时跳过
        - 整个阶段失败不阻塞主流程
        """
        settings = ctx.settings
        tts_enabled = settings.tts_enabled
        bgm_enabled = settings.bgm_enabled

        if not tts_enabled and not bgm_enabled:
            await self.send_message(ctx, "TTS 和 BGM 均未启用，跳过音频阶段。")
            return

        audio_service = AudioService(settings)

        # 获取所有有视频的分镜
        shot_project_id_col = cast(InstrumentedAttribute[int], cast(object, Shot.project_id))
        shot_video_url_col = cast(InstrumentedAttribute[str | None], cast(object, Shot.video_url))
        shot_order_col = cast(InstrumentedAttribute[int], cast(object, Shot.order))
        res = await ctx.session.execute(
            select(Shot)
            .where(shot_project_id_col == ctx.project_id, shot_video_url_col.is_not(None))
            .order_by(shot_order_col.asc())
        )
        shots = list(res.scalars().all())

        # 获取项目角色列表（用于 TTS 语音选择）
        characters = await self.get_project_characters(ctx)

        total = len(shots)
        audio_count = 0

        await self.send_message(
            ctx,
            f"开始添加音频：TTS={'开启' if tts_enabled else '关闭'}，BGM={'开启' if bgm_enabled else '关闭'}...",
            progress=0.0,
            is_loading=True,
        )

        for i, shot in enumerate(shots):
            try:
                await self.send_progress_batch(
                    ctx, total=total, current=i,
                    message=f"   正在处理音频 {i + 1}/{total}...",
                )

                tts_url: str | None = None
                narrator_url: str | None = None
                sfx_url: str | None = None
                bgm_type: str | None = None
                bgm_path: str | None = None

                # 1. 生成多轨音频（对白/旁白/音效）
                if tts_enabled:
                    tracks = await audio_service.generate_tracks(shot, characters)
                    tts_url = tracks.get("dialogue")
                    if tts_url:
                        shot.tts_url = tts_url
                    narrator_url = tracks.get("narrator")
                    if narrator_url:
                        shot.narrator_url = narrator_url
                    sfx_url = tracks.get("sfx")
                    if sfx_url:
                        shot.sfx_url = sfx_url
                    logger.info(
                        "Shot %s tracks: dialogue=%s, narrator=%s, sfx=%s",
                        shot.order, tts_url, narrator_url, sfx_url,
                    )

                # 2. 匹配 BGM
                if bgm_enabled:
                    bgm_path = audio_service.match_bgm(
                        scene=shot.scene,
                        expression=shot.expression,
                    )
                    if bgm_path:
                        # 提取 BGM 类型名称
                        bgm_type = bgm_path.rsplit("/", 1)[-1].replace(".mp3", "")
                        shot.bgm_type = bgm_type

                # 3. 混入视频（多轨混音 + BGM）
                if tts_url or narrator_url or sfx_url or bgm_path:
                    new_video_url = await audio_service.mix_tracks(
                        video_path=shot.video_url,
                        dialogue_path=tts_url,
                        narrator_path=narrator_url,
                        sfx_path=sfx_url,
                        bgm_path=bgm_path,
                    )
                    if new_video_url != shot.video_url:
                        shot.video_url = new_video_url
                        audio_count += 1

                # 更新分镜
                ctx.session.add(shot)
                await ctx.session.flush()

                # 发送音频生成事件
                await ctx.ws.send_event(
                    ctx.project_id,
                    {
                        "type": "audio_generated",
                        "data": {
                            "shot_id": shot.id,
                            "tts_url": shot.tts_url,
                            "bgm_type": shot.bgm_type,
                            "duration": shot.duration,
                        },
                    },
                )

            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as e:
                logger.warning("Audio processing failed for shot %s: %s", shot.id, e)
                await self.send_message(
                    ctx, f"分镜 {shot.order} 音频处理失败: {e}，跳过。"
                )

        # 4. 为最终合并视频匹配 BGM
        if bgm_enabled and ctx.project.video_url:
            try:
                # 使用所有分镜的场景信息综合匹配
                scenes = [s.scene for s in shots if s.scene]
                expressions = [s.expression for s in shots if s.expression]
                combined = " ".join(scenes + expressions)
                final_bgm_path = audio_service.match_bgm(
                    scene=combined if combined else None,
                    expression=None,
                    genre=ctx.project.style,
                )
                if final_bgm_path:
                    new_project_url = await audio_service.mix_bgm_into_video(
                        video_path=ctx.project.video_url,
                        bgm_path=final_bgm_path,
                    )
                    if new_project_url != ctx.project.video_url:
                        ctx.project.video_url = new_project_url
                        ctx.session.add(ctx.project)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as e:
                logger.warning("Final video BGM mixing failed: %s", e)

        # 5. 字幕烧入（硬字幕）
        if ctx.project.video_url:
            try:
                import uuid
                from pathlib import Path

                from app.services.subtitle_service import build_srt, burn_subtitles_into_video

                srt_content = build_srt(shots, include_unapproved=False)

                if srt_content:
                    project_id = ctx.project_id
                    run_id = ctx.run.id  # pyright: ignore[reportArgumentType]
                    exports_dir = Path("static/exports")
                    exports_dir.mkdir(parents=True, exist_ok=True)

                    srt_filename = f"{project_id}_{run_id}.srt"
                    srt_path = exports_dir / srt_filename
                    srt_path.write_text(srt_content, encoding="utf-8")

                    video_output_dir = Path("static/videos")
                    video_output_dir.mkdir(parents=True, exist_ok=True)
                    output_filename = f"sub_{uuid.uuid4().hex[:8]}.mp4"
                    output_path = str(video_output_dir / output_filename)

                    await burn_subtitles_into_video(
                        video_path=ctx.project.video_url,
                        srt_path=str(srt_path),
                        output_path=output_path,
                    )

                    new_video_url = f"/static/videos/{output_filename}"
                    ctx.project.video_url = new_video_url
                    ctx.session.add(ctx.project)

                    shots_with_dialogue = sum(
                        1 for s in shots
                        if s.approved_dialogue or s.dialogue
                    )

                    await ctx.ws.send_event(
                        ctx.project_id,
                        {
                            "type": "subtitle_burned",
                            "data": {
                                "video_url": new_video_url,
                                "srt_download_url": f"/static/exports/{srt_filename}",
                                "shot_count": shots_with_dialogue,
                            },
                        },
                    )

                    srt_path.unlink(missing_ok=True)

                    logger.info("Subtitles burned into final video: %s", new_video_url)
            except Exception:
                logger.warning("Subtitle burn-in failed, keeping original video", exc_info=True)

        await ctx.session.commit()

        if audio_count > 0:
            ctx.completion_info = CompletionInfo(
                completed=f"已为 {audio_count} 个分镜添加音频",
                next="音频处理完成，请查看最终效果",
                question="配音和背景音乐效果如何？",
            )
        else:
            ctx.completion_info = CompletionInfo(
                completed="音频阶段完成",
                next="",
                question="",
            )

        await self.send_message(
            ctx,
            f"音频处理完成！为 {audio_count} 个分镜添加了音频。",
            progress=1.0,
        )

    async def run_videos(self, ctx: AgentContext) -> int:
        """Generate shot videos only (sub-step 1)."""
        async with self.trace_step(
            ctx, stage="compose_videos", method="run_videos",
            model_name=ctx.settings.video_model,
        ) as trace:
            await self.send_message(ctx, "开始生成分镜视频...", progress=0.0, is_loading=True)
            video_count, total_duration = await self._generate_videos(ctx)
            if video_count > 0:
                trace.video_seconds += total_duration
                ctx.completion_info = CompletionInfo(
                    completed=f"已生成 {video_count} 个分镜视频",
                    next="接下来拼接完整视频",
                    question="分镜视频效果如何？",
                )
            else:
                ctx.completion_info = CompletionInfo(
                    completed="无视频可生成",
                    next="跳过拼接",
                    question="",
                )
            return video_count

    async def run_merge(self, ctx: AgentContext) -> None:
        """Merge shot videos into final video (sub-step 2)."""
        async with self.trace_step(
            ctx, stage="compose_merge", method="run_merge",
            model_name=ctx.settings.video_model,
        ):
            await self._merge_videos(ctx)

    async def run_add_audio(self, ctx: AgentContext) -> None:
        """Add TTS dubbing and BGM to shot videos and final merged video (sub-step 3)."""
        async with self.trace_step(
            ctx, stage="add_audio", method="run_add_audio",
            model_name=ctx.settings.video_model,
        ):
            await self._add_audio_to_videos(ctx)

    async def run(self, ctx: AgentContext) -> None:
        """Legacy entry point — runs both sub-steps sequentially."""
        await self.send_message(
            ctx, "开始合成：先生成分镜视频，再拼接完整视频...", progress=0.0, is_loading=True
        )
        video_count = await self.run_videos(ctx)
        if video_count > 0:
            await self.run_merge(ctx)
        else:
            await self.send_message(ctx, "无视频可合成。", progress=1.0)
