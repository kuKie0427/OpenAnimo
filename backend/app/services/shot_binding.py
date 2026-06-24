from __future__ import annotations

from collections.abc import Sequence
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.models.project import Character, Shot


async def resolve_shot_bound_approved_characters(
    session: AsyncSession,
    shot: Shot,
) -> list[Character]:
    character_ids: Sequence[int] = shot.approved_character_ids or shot.character_ids
    if not character_ids:
        return []

    character_project_id_col = cast(InstrumentedAttribute[int], cast(object, Character.project_id))
    character_id_col = cast(InstrumentedAttribute[int | None], cast(object, Character.id))
    result = await session.execute(
        select(Character).where(
            character_project_id_col == shot.project_id,
            character_id_col.in_(list(character_ids)),
        )
    )
    characters_by_id = {
        character.id: character for character in result.scalars().all() if character.id is not None
    }
    return [
        character
        for character_id in character_ids
        if (character := characters_by_id.get(character_id)) is not None
    ]
