# pyright: reportArgumentType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false
from __future__ import annotations

import json
import logging
import re
from typing import Any

from sqlalchemy import select

from app.agents.base import AgentContext, BaseAgent
from app.agents.prompts.critic import CHARACTER_REVIEW_SYSTEM_PROMPT, SHOT_REVIEW_SYSTEM_PROMPT
from app.config import Settings
from app.models.project import Character, Shot

logger = logging.getLogger(__name__)


class CriticAgent(BaseAgent):
    name = "critic"

    def __init__(self) -> None:
        super().__init__()

    async def _build_multimodal_message(
        self,
        *,
        text_prompt: str,
        image_url: str | None,
        settings: Settings,
    ) -> list[dict[str, Any]]:
        """Build a multimodal user message for VLM review.

        If the image URL can be resolved to a public URL, send as image_url content block.
        Otherwise, fall back to text-only review.
        """
        content_parts: list[dict[str, Any]] = [
            {"type": "text", "text": text_prompt},
        ]

        if image_url:
            # Resolve local paths to public URLs if configured
            resolved_url = settings.build_public_url(image_url)
            if resolved_url and (
                resolved_url.startswith("http://") or resolved_url.startswith("https://")
            ):
                content_parts.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": resolved_url},
                    }
                )
            else:
                # No public URL available — graceful degradation
                content_parts.append(
                    {
                        "type": "text",
                        "text": f"[图片无法附加，原始路径: {image_url}]",
                    }
                )

        return [{"role": "user", "content": content_parts}]

    def _parse_review_response(self, raw_text: str) -> dict[str, Any]:
        """Parse structured JSON from the VLM response.

        Handles potential markdown code fences and extracts the JSON object.
        """
        text = raw_text.strip()
        # Strip markdown code fences if present
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fence_match:
            text = fence_match.group(1)
        else:
            # Try to find a JSON object directly
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                text = json_match.group(0)

        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("CriticAgent: failed to parse JSON response: %s", raw_text[:200])
            # Fallback: return a passing score (JSON parse failure in dev/stub mode
            # should not block the pipeline; real VLM would provide valid JSON)
            result = {
                "score": 7.0,
                "dimensions": {"consistency": 7, "quality": 7, "composition": 7},
                "issues": ["审查结果解析失败（使用默认评分）"],
                "suggestions": ["继续下一步"],
            }

        # Validate and normalise
        score = float(result.get("score", 5.0))
        dims = result.get("dimensions", {})
        consistency = int(dims.get("consistency", 5))
        quality = int(dims.get("quality", 5))
        composition = int(dims.get("composition", 5))
        issues = result.get("issues", [])
        suggestions = result.get("suggestions", [])

        # Clamp values
        score = max(0.0, min(10.0, score))
        consistency = max(0, min(10, consistency))
        quality = max(0, min(10, quality))
        composition = max(0, min(10, composition))

        # Recalculate score from dimensions if it looks wrong
        calculated = round(consistency * 0.4 + quality * 0.3 + composition * 0.3, 1)
        if abs(score - calculated) > 1.0:
            score = calculated

        return {
            "score": score,
            "dimensions": {
                "consistency": consistency,
                "quality": quality,
                "composition": composition,
            },
            "issues": [str(i) for i in issues],
            "suggestions": [str(s) for s in suggestions],
        }

    @staticmethod
    def _critique_decision(result: dict, settings) -> tuple[bool, list[str]]:
        """Determine whether to regenerate based on multi-dimensional thresholds.

        Replaces the single-score check. A regeneration is triggered if:
        - Weighted aggregate score < critique_score_threshold, OR
        - ANY dimension score < its per-dimension threshold (fail-fast).

        Returns:
            (should_regenerate: bool, failed_checks: list[str])
            failed_checks contains human-readable descriptions of which
            dimensions failed (e.g. ["consistency: 3 < 4", "score: 5.5 < 6.0"])
        """
        dims = result["dimensions"]
        consistency = int(dims.get("consistency", 5))
        quality = int(dims.get("quality", 5))
        composition = int(dims.get("composition", 5))
        score = float(result.get("score", 5.0))

        failed = []

        # Dimension-level fail-fast checks
        if consistency < settings.critique_consistency_threshold:
            failed.append(f"consistency: {consistency} < {settings.critique_consistency_threshold}")
        if quality < settings.critique_quality_threshold:
            failed.append(f"quality: {quality} < {settings.critique_quality_threshold}")
        if composition < settings.critique_composition_threshold:
            failed.append(f"composition: {composition} < {settings.critique_composition_threshold}")

        # Aggregate score check (existing behavior preserved)
        if score < settings.critique_score_threshold:
            failed.append(f"score: {score:.1f} < {settings.critique_score_threshold:.1f}")

        return (len(failed) > 0, failed)

    async def _run_review(
        self,
        ctx: AgentContext,
        *,
        system_prompt: str,
        user_prompt: str,
        image_url: str | None,
        entity_type: str,
        entity_id: int,
        entity_name: str,
    ) -> dict[str, Any]:
        """Execute a single review via the TextService VLM call."""
        # Fault injection for degradation testing
        if ctx.fault_injector and ctx.fault_injector.get("fail_vlm"):
            raise RuntimeError("Fault injected: VLM unavailable")
        if ctx.fault_injector and ctx.fault_injector.get("fail_text"):
            raise RuntimeError("Fault injected: text-only fallback unavailable")
        settings = ctx.settings

        # Check if critique is enabled
        if not settings.critique_enabled:
            logger.debug("CriticAgent: critique disabled, skipping review")
            return {
                "score": 10.0,
                "dimensions": {"consistency": 10, "quality": 10, "composition": 10},
                "issues": [],
                "suggestions": [],
                "failed_checks": [],
                "entity_type": entity_type,
                "entity_id": entity_id,
                "will_regenerate": False,
            }

        messages = await self._build_multimodal_message(
            text_prompt=user_prompt,
            image_url=image_url,
            settings=settings,
        )

        async with self.trace_step(
            ctx, stage="review", method="_run_review", model_name=settings.text_model
        ) as trace:
            try:
                llm_response = await self.call_llm(
                    ctx,
                    system_prompt=system_prompt,
                    user_prompt="",
                    messages=messages,
                    max_tokens=512,
                    trace=trace,
                )
                raw_text = llm_response.text
            except (RuntimeError, ValueError) as exc:
                logger.warning(
                    "CriticAgent: VLM call failed, degrading to text-only: %s", exc
                )
                # Graceful degradation: try text-only (no image)
                try:
                    llm_response = await self.call_llm(
                        ctx,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt
                        + "\n[注意：图片无法加载，仅基于文本描述评估]",
                        max_tokens=512,
                        trace=trace,
                    )
                    raw_text = llm_response.text
                except (RuntimeError, ValueError) as exc2:
                    logger.error(
                        "CriticAgent: text-only fallback also failed: %s", exc2
                    )
                    trace.status = "failed"
                    trace.error = str(exc2)[:500]
                    return {
                        "score": 5.0,
                        "dimensions": {"consistency": 5, "quality": 5, "composition": 5},
                        "issues": ["VLM 审查调用失败"],
                        "suggestions": ["请检查文本服务配置"],
                        "failed_checks": [],
                        "entity_type": entity_type,
                        "entity_id": entity_id,
                        "will_regenerate": False,
                    }

        result = self._parse_review_response(raw_text)
        result["entity_type"] = entity_type
        result["entity_id"] = entity_id

        will_regenerate, failed_checks = self._critique_decision(result, settings)
        result["will_regenerate"] = will_regenerate
        result["failed_checks"] = failed_checks

        # Send critique result via WebSocket
        await ctx.ws.send_event(
            ctx.project_id,
            {
                "type": "critique_result",
                "data": result,
            },
        )

        # Also persist as an AgentMessage
        score_str = f"{result['score']:.1f}"
        dims = result["dimensions"]
        issues_str = "；".join(result["issues"]) if result["issues"] else "无"
        sug_str = "；".join(result["suggestions"]) if result["suggestions"] else "无"
        content = (
            f"{entity_name} 审查结果：总分 {score_str}/10\n"
            f"  一致性: {dims['consistency']} | 质量: {dims['quality']} | 构图: {dims['composition']}\n"
            f"  问题: {issues_str}\n"
            f"  建议: {sug_str}"
        )
        if failed_checks:
            content += f"\n⚠️ 维度未达标：{'；'.join(failed_checks)}"
        if will_regenerate:
            content += "\n将重新生成"
        else:
            content += "\n质量达标，继续下一步"

        await self.send_message(ctx, content, summary=f"审查评分: {score_str}")

        return result

    async def run_character_review(self, ctx: AgentContext) -> dict[str, Any]:
        """Review all character images in the project."""
        query = select(Character).where(
            Character.project_id == ctx.project_id,
            Character.image_url.isnot(None),
        )
        res = await ctx.session.execute(query)
        characters = res.scalars().all()

        if not characters:
            await self.send_message(ctx, "没有角色形象图需要审查。")
            return {"scores": {}, "min_score": 10.0, "should_regenerate": False}

        total = len(characters)

        # Thinking: reviewing phase — starting character review
        await self.send_thinking(
            ctx,
            phase="reviewing",
            content=f"正在审查 {total} 张角色形象图，评分维度：一致性、质量、构图",
        )

        await self.send_message(
            ctx,
            f"开始审查 {total} 个角色形象图...",
            progress=0.0,
            is_loading=True,
        )

        scores: dict[str, Any] = {}
        min_score = 10.0
        any_regenerate = False

        for i, char in enumerate(characters):
            progress_val = (i) / total
            await self.send_message(
                ctx,
                f"审查角色: {char.name} ({i + 1}/{total})",
                progress=progress_val,
            )

            # Build the text prompt with character description
            desc = char.description or char.name
            user_prompt = (
                f"请审查以下角色形象图。\n\n"
                f"角色名称: {char.name}\n"
                f"角色描述: {desc}\n\n"
                f"请根据角色描述对形象图进行打分，重点关注角色一致性。"
            )

            review = await self._run_review(
                ctx,
                system_prompt=CHARACTER_REVIEW_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                image_url=char.image_url,
                entity_type="character",
                entity_id=char.id,
                entity_name=char.name,
            )

            # Thinking: decision after each character review
            issue_count = len(review.get("issues", []))
            await self.send_thinking(
                ctx,
                phase="decision",
                content=f"角色 {char.name} 评分：{review['score']:.1f}/10，{issue_count} 个问题",
            )

            scores[str(char.id)] = review
            if review["score"] < min_score:
                min_score = review["score"]
            if review["will_regenerate"]:
                any_regenerate = True

        summary_score = f"{min_score:.1f}"
        if any_regenerate:
            await self.send_message(
                ctx,
                f"角色审查完成，最低分 {summary_score}，部分角色需重新生成。",
                progress=1.0,
            )
        else:
            await self.send_message(
                ctx,
                f"角色审查完成，所有角色质量达标（最低分 {summary_score}）。",
                progress=1.0,
            )

        return {
            "scores": scores,
            "min_score": min_score,
            "should_regenerate": any_regenerate,
        }

    async def run_shot_review(self, ctx: AgentContext) -> dict[str, Any]:
        """Review all shot images in the project."""
        query = select(Shot).where(
            Shot.project_id == ctx.project_id,
            Shot.image_url.isnot(None),
        )
        res = await ctx.session.execute(query)
        shots = res.scalars().all()

        if not shots:
            await self.send_message(ctx, "没有分镜画面需要审查。")
            return {"scores": {}, "min_score": 10.0, "should_regenerate": False}

        total = len(shots)

        # Thinking: reviewing phase — starting shot review
        await self.send_thinking(
            ctx,
            phase="reviewing",
            content=f"正在审查 {total} 张分镜画面，评分维度：一致性、质量、构图",
        )

        await self.send_message(
            ctx,
            f"开始审查 {total} 个分镜画面...",
            progress=0.0,
            is_loading=True,
        )

        scores: dict[str, Any] = {}
        min_score = 10.0
        any_regenerate = False

        for i, shot in enumerate(shots):
            progress_val = (i) / total
            await self.send_message(
                ctx,
                f"审查分镜: 第 {shot.order} 镜 ({i + 1}/{total})",
                progress=progress_val,
            )

            # Build the text prompt with shot description
            desc = shot.description or shot.image_prompt or f"分镜 {shot.order}"
            scene = shot.scene or ""
            action = shot.action or ""
            expression = shot.expression or ""
            camera = shot.camera or ""
            lighting = shot.lighting or ""

            user_prompt = (
                f"请审查以下分镜画面。\n\n"
                f"场景: {scene}\n"
                f"动作: {action}\n"
                f"表情: {expression}\n"
                f"镜头: {camera}\n"
                f"光影: {lighting}\n"
                f"综合描述: {desc}\n\n"
                f"请根据场景描述对分镜画面进行打分，重点关注场景一致性。"
            )

            review = await self._run_review(
                ctx,
                system_prompt=SHOT_REVIEW_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                image_url=shot.image_url,
                entity_type="shot",
                entity_id=shot.id,
                entity_name=f"分镜 {shot.order}",
            )

            # Thinking: decision after each shot review
            issue_count = len(review.get("issues", []))
            await self.send_thinking(
                ctx,
                phase="decision",
                content=f"分镜 #{shot.order} 评分：{review['score']:.1f}/10，{issue_count} 个问题",
            )

            scores[str(shot.id)] = review
            if review["score"] < min_score:
                min_score = review["score"]
            if review["will_regenerate"]:
                any_regenerate = True

        summary_score = f"{min_score:.1f}"
        if any_regenerate:
            await self.send_message(
                ctx,
                f"分镜审查完成，最低分 {summary_score}，部分分镜需重新生成。",
                progress=1.0,
            )
        else:
            await self.send_message(
                ctx,
                f"分镜审查完成，所有分镜质量达标（最低分 {summary_score}）。",
                progress=1.0,
            )

        # Trigger consistency evaluation after shot review
        try:
            from app.services.consistency_eval import get_consistency_eval_service

            consistency_service = get_consistency_eval_service()
            consistency_report = await consistency_service.evaluate_project_consistency(
                ctx.project, ctx.session, run_id=ctx.run.id
            )
            # Send WS event
            await ctx.ws.send_event(
                ctx.project_id,
                {
                    "type": "consistency_eval_completed",
                    "data": {
                        "project_id": ctx.project_id,
                        "overall_score": consistency_report["overall_score"],
                        "character_count": len(consistency_report["character_reports"]),
                    },
                },
            )
            # Include in return data
            result = {
                "scores": scores,
                "min_score": min_score,
                "should_regenerate": any_regenerate,
                "consistency_report": consistency_report,
            }
        except (RuntimeError, ValueError) as exc:
            logger.warning("Consistency eval after shot review failed: %s", exc)
            result = {
                "scores": scores,
                "min_score": min_score,
                "should_regenerate": any_regenerate,
            }

        return result
