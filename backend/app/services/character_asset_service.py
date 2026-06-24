# pyright: reportArgumentType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false
"""角色资产服务 — 生成和管理多角度/多情绪角色资产 (4 angles × 4 emotions).

CharacterAssetService 负责：
- 为角色生成 4 角度 × 4 情绪 = 16 张资产矩阵
- 在每个生成的图片上运行人脸 embedding（优雅降级）
- 查询/矩阵/删除角色资产
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Awaitable, Callable

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.character_asset import CharacterAsset

if TYPE_CHECKING:
    from app.models.project import Character

logger = logging.getLogger(__name__)

ANGLES = ("front", "side", "back", "three_quarter")
EMOTIONS = ("smile", "angry", "crying", "surprised")

GenerateImageFn = Callable[[str, int | None], Awaitable[str]]


async def generate_matrix(
    session: AsyncSession,
    character: Character,
    generate_and_cache: GenerateImageFn,
) -> dict:
    """生成 4 角度 × 4 情绪 = 16 张角色资产。

    对每一对 (angle, emotion)：
    1. 构造 prompt
    2. 计算确定性 seed
    3. 调用 generate_and_cache 生成 / 缓存图片
    4. 调用 compute_face_embedding 提取人脸 embedding（失败则记录警告，继续）
    5. 创建 CharacterAsset 记录，写入数据库

    Args:
        session: 异步数据库会话
        character: 目标角色对象
        generate_and_cache: 图片生成回调 (prompt, seed) → image_url

    Returns:
        {"total": 16, "succeeded": int, "failed": int, "assets": list[int]}
    """
    from app.services.character_bible import compute_face_embedding

    char_id = character.id
    if char_id is None:
        raise ValueError("Character must be saved before generating assets")
    if not character.visual_notes and not character.description:
        raise ValueError("Character must have visual_notes or description for asset generation")

    succeeded = 0
    failed = 0
    asset_ids: list[int] = []

    for angle in ANGLES:
        for emotion in EMOTIONS:
            try:
                visual_ref = character.visual_notes or character.description or character.name
                prompt = f"{visual_ref}, {angle} view, expressing {emotion}"

                seed = hash(f"{char_id}:{angle}:{emotion}") % 2**31

                image_url = await generate_and_cache(prompt, seed)

                face_embedding = await compute_face_embedding(image_url)
                embedding_str = json.dumps(face_embedding) if face_embedding else None

                asset = CharacterAsset(
                    character_id=char_id,
                    angle=angle,
                    emotion=emotion,
                    image_url=image_url,
                    face_embedding=embedding_str,
                    prompt=prompt,
                    seed=seed,
                )
                session.add(asset)
                await session.flush()
                assert asset.id is not None  # populated by flush
                asset_ids.append(asset.id)
                succeeded += 1

            except Exception:
                logger.warning(
                    "Failed to generate asset for character %d (%s, %s)",
                    character.id,
                    angle,
                    emotion,
                    exc_info=True,
                )
                failed += 1

    await session.commit()
    return {"total": 16, "succeeded": succeeded, "failed": failed, "assets": asset_ids}


async def list_assets(
    session: AsyncSession,
    character_id: int,
    *,
    angle: str | None = None,
    emotion: str | None = None,
) -> list[CharacterAsset]:
    """列出指定角色的资产，可按 angle/emotion 过滤。

    Args:
        session: 异步数据库会话
        character_id: 角色 ID
        angle: 可选的角度过滤
        emotion: 可选的情绪过滤

    Returns:
        CharacterAsset 对象列表，按 (angle, emotion) 排序
    """
    conditions = [CharacterAsset.character_id == character_id]
    if angle is not None:
        conditions.append(CharacterAsset.angle == angle)
    if emotion is not None:
        conditions.append(CharacterAsset.emotion == emotion)

    stmt = (
        select(CharacterAsset)
        .where(and_(*conditions))
        .order_by(CharacterAsset.angle, CharacterAsset.emotion)
    )

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_matrix(session: AsyncSession, character_id: int) -> dict[str, dict[str, dict]]:
    """以 4×4 矩阵的形式返回角色的所有资产。

    每个 cell 包含：
    - id: 资产 ID（不存在时为 None）
    - image_url: 图片 URL（不存在时为 None）
    - is_approved: 是否已审批（不存在时为 False）
    - prompt: 使用的 prompt（不存在时为 None）

    Args:
        session: 异步数据库会话
        character_id: 角色 ID

    Returns:
        {angle: {emotion: {"id": int|None, ...}}}
    """
    assets = await list_assets(session, character_id)

    lookup: dict[tuple[str, str], CharacterAsset] = {
        (a.angle, a.emotion): a for a in assets
    }

    matrix: dict[str, dict[str, dict]] = {}
    for angle in ANGLES:
        row: dict[str, dict] = {}
        for emotion in EMOTIONS:
            asset = lookup.get((angle, emotion))
            if asset is not None:
                row[emotion] = {
                    "id": asset.id,
                    "image_url": asset.image_url,
                    "is_approved": asset.is_approved,
                    "prompt": asset.prompt,
                }
            else:
                row[emotion] = {
                    "id": None,
                    "image_url": None,
                    "is_approved": False,
                    "prompt": None,
                }
        matrix[angle] = row

    return matrix


async def delete_asset(session: AsyncSession, asset_id: int) -> bool:
    """删除单个资产记录。

    注意：图片文件本身的清理是调用方的责任。

    Args:
        session: 异步数据库会话
        asset_id: 资产 ID

    Returns:
        True 如果资产存在并且已删除，否则 False
    """
    result = await session.execute(
        select(CharacterAsset).where(CharacterAsset.id == asset_id)
    )
    asset = result.scalar_one_or_none()
    if asset is None:
        return False

    await session.delete(asset)
    await session.commit()
    return True


# Ordered lists for nearest-neighbor matching in select_asset_for_shot.
# ANGLE_ORDER: spatial ordering (front → side → three_quarter → back).
# EMOTION_ORDER: expression intensity ordering.
# NOTE: different ordering from ANGLES/EMOTIONS above — ANGLES/EMOTIONS are plain
# enumerations for generation, while these encode spatial/intensity adjacency for
# Manhattan distance selection. If you add a new angle/emotion, update BOTH sets.
ANGLE_ORDER = ("front", "side", "three_quarter", "back")
EMOTION_ORDER = ("smile", "surprised", "angry", "crying")


async def select_asset_for_shot(
    session: AsyncSession,
    character_id: int,
    angle: str | None,
    expression: str | None,
) -> CharacterAsset | None:
    """Select the best-matching CharacterAsset for a shot's camera angle and emotional expression.

    Selection strategy:
    1. If angle or expression is None → return None (fall back to character default image_url).
    2. If the character has no assets → return None.
    3. Try EXACT match (asset.angle == angle AND asset.emotion == expression).
    4. If no exact match → NEAREST NEIGHBOR by minimum Manhattan distance in
       (ANGLE_ORDER, EMOTION_ORDER) space.

    Args:
        session: 异步数据库会话
        character_id: 角色 ID
        angle: 目标角度（对应 Shot.camera）
        expression: 目标情绪（对应 Shot.expression）

    Returns:
        最佳匹配的 CharacterAsset，或 None（无资产 / 参数缺失 / 无法映射）
    """
    if angle is None or expression is None:
        return None

    assets = await list_assets(session, character_id)
    if not assets:
        return None

    # 1) Exact match
    for asset in assets:
        if asset.angle == angle and asset.emotion == expression:
            return asset

    # 2) Nearest neighbor via Manhattan distance in order-index space
    try:
        target_angle_idx = ANGLE_ORDER.index(angle)
        target_emotion_idx = EMOTION_ORDER.index(expression)
    except ValueError:
        # angle or expression not in our known order lists → cannot map
        return None

    best_asset: CharacterAsset | None = None
    best_distance: float = float("inf")

    for asset in assets:
        try:
            a_idx = ANGLE_ORDER.index(asset.angle)
            e_idx = EMOTION_ORDER.index(asset.emotion)
        except ValueError:
            continue  # skip assets whose angle/emotion aren't in our order lists

        distance = abs(a_idx - target_angle_idx) + abs(e_idx - target_emotion_idx)
        if distance < best_distance:
            best_distance = distance
            best_asset = asset

    return best_asset
