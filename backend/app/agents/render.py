# pyright: reportArgumentType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false, reportReturnType=false
from __future__ import annotations

import asyncio
import logging

import httpx
import random
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentContext, BaseAgent, CompletionInfo
from app.agents.utils import build_character_context
from app.models.project import Character, Shot
from app.models.style_template import StyleTemplate
from app.services.character_bible import (
    auto_populate_visual_notes,
    build_character_bible,
    compute_face_embedding,
)
from app.services.image_composer import ImageComposer
from app.services.character_asset_service import select_asset_for_shot
from app.services.shot_binding import resolve_shot_bound_approved_characters
from app.services.version_service import VersionService, character_snapshot, shot_snapshot

logger = logging.getLogger(__name__)


class RenderAgent(BaseAgent):
    name = "render"

    def __init__(self):
        super().__init__()
        self.image_composer = ImageComposer()
        self.version_service = VersionService()

    # Hardcoded fallback mapping used when no StyleTemplate row exists
    _FALLBACK_STYLE_MAP = {
        "anime": "anime, 2D illustration, cel-shading, vibrant colors, Japanese animation style",
        "shonen": "anime, shonen style, high contrast, dynamic composition, dramatic lighting, bold lines",
        "slice-of-life": "anime, slice of life, soft pastel colors, warm lighting, rounded lines, cozy atmosphere",
        "manga": "manga style, black and white, halftone dots, speed lines, high contrast ink",
        "donghua": "Chinese animation, ink wash, flowing lines, oriental color palette, watercolor textures",
        "cinematic": "cinematic, photorealistic, 35mm film grain, natural lighting, shallow depth of field",
        "pixar": "3D cartoon, Pixar-style rendering, smooth surfaces, global illumination, rounded shapes",
        "lowpoly": "low poly, geometric, faceted surfaces, hard edge lighting, minimalist palette",
        "watercolor": "watercolor, soft bleeding edges, transparent layering, white space breathing, painterly",
        "sketch": "pencil sketch, cross-hatching, monochrome shading, rough lines, hand-drawn",
        "realistic": "photorealistic, natural lighting, detailed textures, real-world proportions",
    }

    async def _lookup_style_template(self, session: "AsyncSession", style: str) -> StyleTemplate | None:
        """Look up a StyleTemplate by slug from the database."""
        res = await session.execute(
            select(StyleTemplate).where(
                StyleTemplate.slug == style,
                StyleTemplate.is_active.is_(True),
            )
        )
        return res.scalar_one_or_none()

    def _style_descriptor(self, style: str) -> str:
        """Synchronous fallback — used when no session is available."""
        return self._FALLBACK_STYLE_MAP.get(style, self._FALLBACK_STYLE_MAP.get("anime"))

    async def _style_descriptor_async(self, session: "AsyncSession", style: str) -> tuple[str, str | None]:
        """Look up StyleTemplate from DB and return (style_prompt, negative_prompt).

        Falls back to hardcoded mapping if template not found.
        """
        template = await self._lookup_style_template(session, style)
        if template:
            color_part = ", ".join(template.color_palette) if template.color_palette else ""
            prompt = template.style_prompt
            if color_part:
                prompt = f"{prompt}, {color_part}"
            return prompt, template.negative_prompt
        # Fallback to hardcoded mapping
        return self._style_descriptor(style), None

    async def _build_character_prompt(self, character: Character, *, style: str, session: "AsyncSession", ctx: AgentContext | None = None) -> str:
        desc = character.description or character.name
        # Inject visual_notes into the prompt if available
        if character.visual_notes:
            desc = f"{desc}, {character.visual_notes}"
        style_desc, negative = await self._style_descriptor_async(session, style)
        face_anchor = "detailed face, clear facial features, sharp eyes"
        prompt = f"{desc}, {face_anchor}, {style_desc}"
        if negative:
            prompt += f" || negative: {negative}"
        # Inject critique feedback if available (targeted regeneration)
        if ctx and ctx.critique_feedback:
            char_fb = ctx.critique_feedback.get("character", {}).get(str(character.id))
            if char_fb:
                suggestions = "；".join(char_fb.get("suggestions", []))
                if suggestions:
                    prompt += f"。改进建议: {suggestions}"
        return prompt

    async def _build_shot_prompt(self, shot: Shot, characters: list[Character], *, style: str, session: "AsyncSession", ctx: AgentContext | None = None) -> str:
        desc = shot.image_prompt or shot.description
        parts = [desc.strip()]
        # Inject character bible text for each character
        for char in characters:
            bible_text = build_character_bible(char)
            if bible_text:
                parts.append(f"Character {char.name}: {bible_text}")
        char_context = build_character_context(characters)
        if char_context:
            parts.append(char_context)
        if characters:
            parts.append("same character face as reference, consistent identity")
        style_desc, negative = await self._style_descriptor_async(session, style)
        parts.append(style_desc)

        # Inject critique feedback if available (targeted regeneration)
        if ctx and ctx.critique_feedback:
            shot_fb = ctx.critique_feedback.get("shot", {}).get(str(shot.id))
            if shot_fb:
                suggestions = "；".join(shot_fb.get("suggestions", []))
                if suggestions:
                    parts.append(f"改进建议: {suggestions}")

        if negative:
            parts.append(f"|| negative: {negative}")
        return ", ".join(parts)

    async def _render_characters(self, ctx: AgentContext) -> int:
        query = select(Character).where(
            Character.project_id == ctx.project_id,
            Character.image_url.is_(None),
        )
        if ctx.target_ids and ctx.target_ids.character_ids:
            query = query.where(Character.id.in_(ctx.target_ids.character_ids))
        res = await ctx.session.execute(query)
        characters = res.scalars().all()

        if not characters:
            await self.send_message(ctx, "所有角色已有形象图。")
            return 0

        total = len(characters)

        # Thinking: planning phase — starting character rendering
        await self.send_thinking(
            ctx,
            phase="planning",
            content="正在构建角色形象描述，注入风格和面部锚定词...",
            details=f"共 {total} 个角色待生成，风格：{ctx.project.style or '默认'}",
        )

        await self.send_message(
            ctx, f"开始为 {total} 个角色生成形象图...", progress=0.0, is_loading=True
        )

        updated_count = 0
        style = ctx.project.style or ""
        for i, char in enumerate(characters):
            try:
                await self.send_progress_batch(
                    ctx,
                    total=total,
                    current=i,
                    message=f"   正在绘制：{char.name} ({i + 1}/{total})",
                )
                image_prompt = await self._build_character_prompt(char, style=style, session=ctx.session, ctx=ctx)
                version = await self.version_service.auto_snapshot_character(
                    ctx.session,
                    char,
                    run_id=ctx.run.id,
                    trigger="generation",
                )
                if version is not None:
                    await ctx.session.flush()
                    await ctx.ws.send_event(
                        ctx.project_id,
                        {
                            "type": "version_created",
                            "data": {
                                "entity_type": "character",
                                "entity_id": char.id,
                                "version": version.version,
                                "trigger": version.trigger,
                            },
                        },
                    )
                # Thinking: reasoning for each character
                await self.send_thinking(
                    ctx,
                    phase="reasoning",
                    content=f"为 {char.name} 生成形象图，prompt 长度 {len(image_prompt)} 字符",
                )
                # Seed management: generate random seed on first render, reuse on regeneration
                char_seed = getattr(char, "seed", None)
                if char_seed is None:
                    char_seed = random.randint(1, 2_147_483_647)
                    if hasattr(char, "seed"):
                        char.seed = char_seed
                        ctx.session.add(char)

                external_url = await self.generate_and_cache_image(
                    ctx, prompt=image_prompt, seed=char_seed, timeout_s=480.0
                )
                char.image_url = external_url
                ctx.session.add(char)
                await ctx.session.flush()

                # Auto-populate visual_notes if missing
                if not char.visual_notes and char.description:
                    try:
                        visual_notes = await auto_populate_visual_notes(char, ctx.llm)
                        if visual_notes:
                            char.visual_notes = visual_notes
                            ctx.session.add(char)
                            await ctx.session.flush()
                    except (RuntimeError, ValueError) as e:
                        logger.warning("Failed to auto-populate visual_notes for %s: %s", char.name, e)

                # Auto-compute face embedding after image is generated
                if not char.face_embedding and external_url:
                    try:
                        embedding = await compute_face_embedding(external_url)
                        if embedding is not None:
                            import json
                            char.face_embedding = json.dumps(embedding)
                            ctx.session.add(char)
                            await ctx.session.flush()
                            logger.info("Computed face embedding for character %s", char.name)
                    except (httpx.HTTPError, RuntimeError, ValueError) as e:
                        logger.warning("Failed to compute face embedding for %s: %s", char.name, e)

                # Multi-angle asset generation (optional, gated by config flag)
                if ctx.settings.multi_angle_enabled:
                    try:
                        from app.services.character_asset_service import generate_matrix

                        async def _multi_angle_generate_fn(prompt: str, seed: int | None) -> str:
                            return await self.generate_and_cache_image(ctx, prompt=prompt, seed=seed)

                        _result = await generate_matrix(
                            ctx.session, char, _multi_angle_generate_fn
                        )
                        logger.info(
                            "Multi-angle assets generated for %s: %d/%d succeeded",
                            char.name,
                            _result["succeeded"],
                            _result["total"],
                        )
                    except Exception as e:
                        logger.warning(
                            "Failed to generate multi-angle assets for %s: %s",
                            char.name,
                            e,
                        )

                current_version = await self.version_service.create_version(
                    ctx.session,
                    "character",
                    char.id,
                    character_snapshot(char),
                    run_id=ctx.run.id,
                    trigger="generation",
                )
                await ctx.ws.send_event(
                    ctx.project_id,
                    {
                        "type": "version_created",
                        "data": {
                            "entity_type": "character",
                            "entity_id": char.id,
                            "version": current_version.version,
                            "trigger": current_version.trigger,
                        },
                    },
                )
                await self.send_character_event(ctx, char, "character_updated")
                updated_count += 1
            except (RuntimeError, ValueError, OSError) as e:
                await self.send_message(ctx, f"角色 {char.name} 图片生成失败: {str(e)[:50]}")

        await ctx.session.commit()
        if updated_count > 0:
            char_names_list = [c.name for c in characters[:updated_count]]
            names_str = "、".join(char_names_list) if char_names_list else f"{updated_count} 个角色"
            await self.send_message(ctx, f"已为 {names_str} 生成形象图，接下来生成分镜图。")
        return updated_count

    async def _render_shots(self, ctx: AgentContext) -> int:
        query = (
            select(Shot)
            .where(
                Shot.project_id == ctx.project_id,
                Shot.image_url.is_(None),
            )
            .order_by(Shot.order)
        )
        if ctx.target_ids and ctx.target_ids.shot_ids:
            query = query.where(Shot.id.in_(ctx.target_ids.shot_ids))
        res = await ctx.session.execute(query)
        shots = res.scalars().all()

        if not shots:
            await self.send_message(ctx, "所有分镜已有首帧图片。")
            return 0

        total = len(shots)
        updated_count = 0
        failed_count = 0
        style = ctx.project.style or ""

        # Thinking: planning phase — starting shot rendering
        await self.send_thinking(
            ctx,
            phase="planning",
            content=f"开始为 {total} 个分镜生成首帧图片...",
            details="使用角色参考图和风格描述",
        )

        await self.send_message(
            ctx,
            f"开始为 {total} 个分镜生成首帧图片（使用角色参考图）...",
            progress=0.0,
            is_loading=True,
        )

        for i, shot in enumerate(shots):
            try:
                await self.send_progress_batch(
                    ctx, total=total, current=i, message=f"   正在绘制分镜 {i + 1}/{total}..."
                )

                characters = await resolve_shot_bound_approved_characters(ctx.session, shot)
                char_image_urls = []
                for c in characters:
                    asset = await select_asset_for_shot(ctx.session, c.id, shot.camera, shot.expression)
                    if asset:
                        char_image_urls.append(asset.image_url)
                        logger.info(
                            "Selected asset for character %s in shot %d: angle=%s, emotion=%s",
                            c.name,
                            shot.id,
                            asset.angle,
                            asset.emotion,
                        )
                    elif c.image_url:
                        char_image_urls.append(c.image_url)

                # Thinking: reasoning for each shot
                n_refs = len(char_image_urls)
                await self.send_thinking(
                    ctx,
                    phase="reasoning",
                    content=f"分镜 #{shot.order} 使用了 {n_refs} 个角色参考图",
                )

                reference_image_bytes: bytes | None = None

                if char_image_urls:
                    try:
                        reference_image_bytes = (
                            await self.image_composer.compose_character_reference_image(
                                char_image_urls
                            )
                        )
                        logger.info(
                            "Composed character reference image with %d characters for shot %d",
                            len(char_image_urls),
                            shot.id,
                        )
                    except (RuntimeError, ValueError, OSError) as exc:
                        reference_image_bytes = None
                        logger.warning("Failed to compose character reference image: %s", exc)
                else:
                    logger.info(
                        "No character images available for shot %d; using text-to-image", shot.id
                    )

                image_prompt = await self._build_shot_prompt(shot, characters, style=style, session=ctx.session, ctx=ctx)
                version = await self.version_service.auto_snapshot_shot(
                    ctx.session,
                    shot,
                    run_id=ctx.run.id,
                    trigger="generation",
                )
                if version is not None:
                    await ctx.session.flush()
                    await ctx.ws.send_event(
                        ctx.project_id,
                        {
                            "type": "version_created",
                            "data": {
                                "entity_type": "shot",
                                "entity_id": shot.id,
                                "version": version.version,
                                "trigger": version.trigger,
                            },
                        },
                    )

                # Seed management: generate random seed on first render, reuse on regeneration
                render_seed = shot.seed
                if render_seed is None:
                    render_seed = random.randint(1, 2_147_483_647)  # int32 range
                    shot.seed = render_seed
                    ctx.session.add(shot)

                image_url = await self.generate_and_cache_image(
                    ctx,
                    prompt=image_prompt,
                    image_bytes=reference_image_bytes,
                    timeout_s=480.0,
                    seed=render_seed,
                )

                shot.image_url = image_url
                ctx.session.add(shot)
                await ctx.session.flush()
                current_version = await self.version_service.create_version(
                    ctx.session,
                    "shot",
                    shot.id,
                    shot_snapshot(shot),
                    run_id=ctx.run.id,
                    trigger="generation",
                )
                await ctx.ws.send_event(
                    ctx.project_id,
                    {
                        "type": "version_created",
                        "data": {
                            "entity_type": "shot",
                            "entity_id": shot.id,
                            "version": current_version.version,
                            "trigger": current_version.trigger,
                        },
                    },
                )
                await self.send_shot_event(ctx, shot, "shot_updated")
                updated_count += 1

                if i < total - 1:
                    await asyncio.sleep(1.0)

            except (RuntimeError, ValueError, OSError) as e:
                failed_count += 1
                await self.send_message(ctx, f"镜头 {shot.order} 首帧图片生成失败: {str(e)[:100]}")
                await asyncio.sleep(2.0)

        await ctx.session.commit()

        summary = (
            f"为{updated_count}个分镜生成了首帧图片" if updated_count > 0 else "分镜图片生成失败"
        )
        if updated_count > 0:
            shots[0].description[:20] if shots and shots[0].description else ""
            msg = f"已为 {updated_count} 个分镜生成首帧图片，接下来将生成视频。"
            if failed_count > 0:
                msg += f"（{failed_count} 个失败）"
            await self.send_message(ctx, msg, summary=summary, progress=1.0)
        elif failed_count > 0:
            await self.send_message(
                ctx,
                f"所有 {failed_count} 个分镜首帧图片生成均失败。",
                summary=summary,
                progress=1.0,
            )

        return updated_count

    async def run_characters(self, ctx: AgentContext) -> None:
        """Render character images only (sub-step 1)."""
        async with self.trace_step(
            ctx, stage="render_characters", method="run_characters",
            model_name=ctx.settings.image_model,
        ) as trace:
            await self.send_message(ctx, "开始生成角色形象图...", progress=0.0, is_loading=True)
            char_count = await self._render_characters(ctx)
            trace.images_generated += char_count
            ctx.completion_info = CompletionInfo(
                completed=f"已生成 {char_count} 个角色形象图",
                details="角色形象已渲染完成",
                next="接下来渲染分镜画面",
                question="角色形象是否满意？如果需要重新生成，请告诉我。",
            )
            await self.send_message(
                ctx,
                f"角色形象渲染完成！已生成 {char_count} 个角色形象图。",
                summary=f"{char_count} 个角色形象图",
                progress=1.0,
            )

    async def run_shots(self, ctx: AgentContext) -> None:
        """Render shot storyboard images only (sub-step 2)."""
        async with self.trace_step(
            ctx, stage="render_shots", method="run_shots",
            model_name=ctx.settings.image_model,
        ) as trace:
            await self.send_message(ctx, "开始生成分镜首帧图...", progress=0.0, is_loading=True)
            shot_count = await self._render_shots(ctx)
            trace.images_generated += shot_count
            ctx.completion_info = CompletionInfo(
                completed=f"已生成 {shot_count} 个分镜首帧图",
                details="分镜画面已渲染完成",
                next="接下来将根据分镜生成视频片段并合成",
                question="分镜画面是否满意？如果需要重新生成，请告诉我。",
            )
            await self.send_message(
                ctx,
                f"分镜画面渲染完成！已生成 {shot_count} 个分镜首帧图。",
                summary=f"{shot_count} 个分镜首帧图",
                progress=1.0,
            )

    async def run(self, ctx: AgentContext) -> None:
        """Legacy entry point — runs both sub-steps sequentially."""
        await self.send_message(
            ctx,
            "开始渲染：先生成角色形象图，再使用角色图作为参考生成分镜图...",
            progress=0.0,
            is_loading=True,
        )
        await self.run_characters(ctx)
        await self.run_shots(ctx)
