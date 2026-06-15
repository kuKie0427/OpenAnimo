# pyright: reportArgumentType=false, reportAttributeAccessIssue=false
"""角色一致性量化评估服务

使用 InsightFace 的人脸 embedding 余弦相似度，自动计算角色跨分镜的视觉一致性。
评估维度：
- face_similarity: 人脸 embedding 余弦相似度均值（0-1）
- face_consistency: 人脸相似度标准差（越小越一致）
- presence_rate: 该角色在应出现分镜中的实际检测率
- overall_score: 加权综合评分（0-100）
"""

from __future__ import annotations

import json
import logging
import math
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consistency_report import ConsistencyReport
from app.models.project import Character, Project, Shot
from app.services.face_cropper import detect_faces, is_face_cropping_available

logger = logging.getLogger(__name__)


def _compute_grade(score: float) -> str:
    """将 0-100 分数映射为等级"""
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 40:
        return "D"
    return "F"


class ConsistencyEvalService:
    """角色一致性量化评估"""

    async def evaluate_character_consistency(
        self,
        character: Character,
        shots: list[Shot],
        session: AsyncSession,
    ) -> dict[str, Any]:
        """评估单个角色在所有相关分镜中的一致性。

        Args:
            character: 角色（需要 face_embedding）
            shots: 包含该角色的分镜列表
            session: 数据库会话

        Returns:
            CharacterConsistencyReport 字典
        """
        # 1. 获取 reference embedding
        ref_embedding = await self._get_character_embedding(character)
        if ref_embedding is None:
            logger.warning(
                "Character %s (id=%d) has no face_embedding, skipping",
                character.name,
                character.id,
            )
            return {
                "character_id": character.id,
                "character_name": character.name,
                "face_similarity_mean": 0.0,
                "face_similarity_std": 0.0,
                "presence_rate": 0.0,
                "overall_score": 0.0,
                "face_matches": [],
                "grade": "F",
            }

        # 2. 对每个分镜提取人脸 embedding 并匹配
        face_matches: list[dict[str, Any]] = []
        similarities: list[float] = []

        for shot in shots:
            if not shot.image_url:
                face_matches.append(
                    {
                        "shot_id": shot.id,
                        "shot_order": shot.order,
                        "similarity": 0.0,
                        "detected": False,
                    }
                )
                continue

            shot_embedding = await self.extract_face_embedding_from_image(shot.image_url)
            if shot_embedding is None:
                face_matches.append(
                    {
                        "shot_id": shot.id,
                        "shot_order": shot.order,
                        "similarity": 0.0,
                        "detected": False,
                    }
                )
                continue

            # 找到与 reference 最匹配的人脸（这里 shot_embedding 是最高置信度人脸）
            sim = self.compute_cosine_similarity(ref_embedding, shot_embedding)
            face_matches.append(
                {
                    "shot_id": shot.id,
                    "shot_order": shot.order,
                    "similarity": round(sim, 4),
                    "detected": True,
                }
            )
            similarities.append(sim)

        # 3. 计算各维度分数
        n_shots = len(shots)
        n_detected = sum(1 for m in face_matches if m["detected"])

        face_similarity_mean = sum(similarities) / len(similarities) if similarities else 0.0
        face_similarity_std = (
            math.sqrt(sum((s - face_similarity_mean) ** 2 for s in similarities) / len(similarities))
            if len(similarities) > 1
            else 0.0
        )
        presence_rate = n_detected / n_shots if n_shots > 0 else 0.0

        # 4. 综合评分（加权）
        # face_similarity_mean (0-1) * 50 + presence_rate (0-1) * 30 + consistency_bonus * 20
        # consistency_bonus = max(0, 1 - std * 5)  (std越小越好)
        consistency_bonus = max(0.0, 1.0 - face_similarity_std * 5)
        overall_score = (
            face_similarity_mean * 50 + presence_rate * 30 + consistency_bonus * 20
        )

        grade = _compute_grade(overall_score)

        return {
            "character_id": character.id,
            "character_name": character.name,
            "face_similarity_mean": round(face_similarity_mean, 4),
            "face_similarity_std": round(face_similarity_std, 4),
            "presence_rate": round(presence_rate, 4),
            "overall_score": round(overall_score, 2),
            "face_matches": face_matches,
            "grade": grade,
        }

    async def evaluate_project_consistency(
        self,
        project: Project,
        session: AsyncSession,
        run_id: int | None = None,
    ) -> dict[str, Any]:
        """评估整个项目的角色一致性。

        Args:
            project: 项目
            session: 数据库会话
            run_id: 关联的 AgentRun ID（可选）

        Returns:
            ProjectConsistencyReport 字典
        """
        from datetime import datetime, timezone as _tz
        UTC = _tz.utc

        # 加载角色
        char_res = await session.execute(
            select(Character).where(Character.project_id == project.id)
        )
        characters = list(char_res.scalars().all())

        # 加载分镜
        shot_res = await session.execute(
            select(Shot).where(Shot.project_id == project.id).order_by(Shot.order)
        )
        all_shots = list(shot_res.scalars().all())

        character_reports: list[dict[str, Any]] = []

        for char in characters:
            # 筛选包含该角色的分镜
            char_shots = [s for s in all_shots if char.id in (s.character_ids or [])]
            if not char_shots and char.image_url:
                # 角色不在任何分镜中但有形象图 — 仍然评估（0分）
                pass

            report = await self.evaluate_character_consistency(char, char_shots, session)
            character_reports.append(report)

        # 项目级评分 = 各角色评分的均值
        if character_reports:
            overall_score = sum(r["overall_score"] for r in character_reports) / len(
                character_reports
            )
        else:
            overall_score = 0.0

        project_report = {
            "project_id": project.id,
            "overall_score": round(overall_score, 2),
            "character_reports": character_reports,
            "evaluated_at": datetime.now(UTC).isoformat(),
        }

        # 持久化到数据库
        db_report = ConsistencyReport(
            project_id=project.id,
            run_id=run_id,
            report_data=project_report,
            overall_score=round(overall_score, 2),
        )
        session.add(db_report)
        await session.commit()
        await session.refresh(db_report)

        # 将 eval_id 注入返回
        project_report["eval_id"] = db_report.id

        return project_report

    def compute_cosine_similarity(self, emb1: list[float], emb2: list[float]) -> float:
        """计算余弦相似度。

        Args:
            emb1: 向量1
            emb2: 向量2

        Returns:
            余弦相似度 [-1, 1]，实际人脸 embedding 通常 [0, 1]
        """
        dot = sum(a * b for a, b in zip(emb1, emb2))
        norm1 = math.sqrt(sum(a * a for a in emb1))
        norm2 = math.sqrt(sum(b * b for b in emb2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    async def extract_face_embedding_from_image(self, image_url: str) -> list[float] | None:
        """从图片 URL 提取人脸 embedding。

        下载图片 → detect_faces → 取最高置信度人脸的 embedding

        Args:
            image_url: 图片路径（本地 /static/ 路径或 HTTP URL）

        Returns:
            512维 embedding 列表，未检测到人脸返回 None
        """
        if not is_face_cropping_available():
            logger.debug("InsightFace not available, cannot extract face embedding")
            return None

        image_bytes = await self._download_image(image_url)
        if image_bytes is None:
            return None

        faces = detect_faces(image_bytes)
        if not faces:
            return None

        # 取最高置信度人脸
        best_face = max(faces, key=lambda f: f["det_score"])
        embedding = best_face["embedding"]
        # Convert numpy array to list if needed
        if hasattr(embedding, "tolist"):
            return embedding.tolist()
        return list(embedding)

    async def _get_character_embedding(self, character: Character) -> list[float] | None:
        """获取角色的 reference face embedding。

        优先使用 character.face_embedding（已缓存的 JSON 字符串），
        否则尝试从 character.image_url 提取。
        """
        if character.face_embedding:
            try:
                return json.loads(character.face_embedding)
            except (json.JSONDecodeError, TypeError):
                logger.warning(
                    "Failed to parse face_embedding for character %d", character.id
                )

        # 尝试从 image_url 提取
        if character.image_url:
            emb = await self.extract_face_embedding_from_image(character.image_url)
            if emb is not None:
                # 缓存到 character 模型
                character.face_embedding = json.dumps(emb)
                return emb

        return None

    async def _download_image(self, image_url: str) -> bytes | None:
        """下载图片字节流。

        支持本地 /static/ 路径和 HTTP URL。
        """
        if not image_url:
            return None

        # 本地 /static/ 路径
        if image_url.startswith("/static/"):
            try:
                from pathlib import Path

                # 项目根目录下的 static
                base_dir = Path(__file__).resolve().parents[1]
                file_path = base_dir / image_url.lstrip("/")
                if file_path.exists():
                    return file_path.read_bytes()
            except (OSError, PermissionError) as exc:
                logger.warning("Failed to read local image %s: %s", image_url, exc)
                return None

        # HTTP URL
        if image_url.startswith("http://") or image_url.startswith("https://"):
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(image_url)
                    resp.raise_for_status()
                    return resp.content
            except httpx.HTTPError as exc:
                logger.warning("Failed to download image %s: %s", image_url, exc)
                return None

        logger.warning("Unsupported image URL format: %s", image_url[:100])
        return None


# 单例
_consistency_eval_service: ConsistencyEvalService | None = None


def get_consistency_eval_service() -> ConsistencyEvalService:
    """获取 ConsistencyEvalService 单例"""
    global _consistency_eval_service
    if _consistency_eval_service is None:
        _consistency_eval_service = ConsistencyEvalService()
    return _consistency_eval_service
