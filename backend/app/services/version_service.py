from __future__ import annotations

from typing import Any, Iterable, Literal, cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.exceptions import BusinessError, NotFoundError
from app.models.artifact_version import ArtifactVersion
from app.models.project import Character, Shot

EntityType = Literal["character", "shot"]

CHARACTER_SNAPSHOT_FIELDS = (
    "id",
    "project_id",
    "name",
    "description",
    "image_url",
    "reference_images",
    "visual_notes",
    "approved_name",
    "approved_description",
    "approved_image_url",
    "approved_at",
    "approval_version",
)

SHOT_SNAPSHOT_FIELDS = (
    "id",
    "project_id",
    "order",
    "description",
    "prompt",
    "image_prompt",
    "image_url",
    "video_url",
    "duration",
    "camera",
    "motion_note",
    "scene",
    "action",
    "expression",
    "lighting",
    "dialogue",
    "sfx",
    "tts_url",
    "bgm_type",
    "seed",
    "character_ids",
    "approved_description",
    "approved_prompt",
    "approved_image_prompt",
    "approved_duration",
    "approved_camera",
    "approved_motion_note",
    "approved_scene",
    "approved_action",
    "approved_expression",
    "approved_lighting",
    "approved_dialogue",
    "approved_sfx",
    "approved_character_ids",
    "approved_at",
    "approval_version",
)

ROLLBACK_FIELDS: dict[EntityType, tuple[str, ...]] = {
    "character": ("name", "description", "image_url", "visual_notes"),
    "shot": (
        "description",
        "prompt",
        "image_prompt",
        "image_url",
        "camera",
        "motion_note",
        "scene",
        "action",
        "expression",
        "lighting",
        "dialogue",
        "sfx",
    ),
}


def _json_value(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, list):
        return list(value)
    return value


def _snapshot_from_fields(entity: Any, fields: Iterable[str]) -> dict[str, Any]:
    return {field: _json_value(getattr(entity, field, None)) for field in fields}


def character_snapshot(character: Character) -> dict[str, Any]:
    """Build a JSON-safe Character snapshot."""
    return _snapshot_from_fields(character, CHARACTER_SNAPSHOT_FIELDS)


def shot_snapshot(shot: Shot) -> dict[str, Any]:
    """Build a JSON-safe Shot snapshot."""
    return _snapshot_from_fields(shot, SHOT_SNAPSHOT_FIELDS)


class VersionService:
    """版本管理服务。"""

    async def create_version(
        self,
        session: AsyncSession,
        entity_type: EntityType,
        entity_id: int,
        snapshot: dict[str, Any],
        run_id: int | None = None,
        trigger: str = "generation",
    ) -> ArtifactVersion:
        """Create a version snapshot using max(version)+1 for the entity."""
        if entity_type not in ("character", "shot"):
            raise BusinessError("Unsupported entity type", code="INVALID_ENTITY_TYPE")

        version_col = cast(InstrumentedAttribute[int], cast(object, ArtifactVersion.version))
        entity_type_col = cast(InstrumentedAttribute[str], cast(object, ArtifactVersion.entity_type))
        entity_id_col = cast(InstrumentedAttribute[int], cast(object, ArtifactVersion.entity_id))
        result = await session.execute(
            select(func.max(version_col)).where(
                entity_type_col == entity_type,
                entity_id_col == entity_id,
            )
        )
        next_version = (result.scalar_one_or_none() or 0) + 1
        project_id = int(snapshot.get("project_id") or 0)
        if project_id <= 0:
            project_id = await self._project_id_for_entity(session, entity_type, entity_id)

        artifact_version = ArtifactVersion(
            project_id=project_id,
            entity_type=entity_type,
            entity_id=entity_id,
            version=next_version,
            snapshot=snapshot,
            run_id=run_id,
            trigger=trigger,
        )
        session.add(artifact_version)
        await session.flush()
        return artifact_version

    async def get_versions(
        self, session: AsyncSession, entity_type: EntityType, entity_id: int
    ) -> list[ArtifactVersion]:
        """Return all versions for an entity, newest first."""
        entity_type_col = cast(InstrumentedAttribute[str], cast(object, ArtifactVersion.entity_type))
        entity_id_col = cast(InstrumentedAttribute[int], cast(object, ArtifactVersion.entity_id))
        version_col = cast(InstrumentedAttribute[int], cast(object, ArtifactVersion.version))
        result = await session.execute(
            select(ArtifactVersion)
            .where(entity_type_col == entity_type, entity_id_col == entity_id)
            .order_by(version_col.desc())
        )
        return list(result.scalars().all())

    async def get_version(self, session: AsyncSession, version_id: int) -> ArtifactVersion | None:
        """Return a specific version snapshot."""
        return await session.get(ArtifactVersion, version_id)

    async def get_version_by_number(
        self, session: AsyncSession, entity_type: EntityType, entity_id: int, version: int
    ) -> ArtifactVersion | None:
        """Return an entity version by version number."""
        entity_type_col = cast(InstrumentedAttribute[str], cast(object, ArtifactVersion.entity_type))
        entity_id_col = cast(InstrumentedAttribute[int], cast(object, ArtifactVersion.entity_id))
        version_col = cast(InstrumentedAttribute[int], cast(object, ArtifactVersion.version))
        result = await session.execute(
            select(ArtifactVersion).where(
                entity_type_col == entity_type,
                entity_id_col == entity_id,
                version_col == version,
            )
        )
        return result.scalar_one_or_none()

    async def rollback(
        self,
        session: AsyncSession,
        entity_type: EntityType,
        entity_id: int,
        target_version: int,
    ) -> ArtifactVersion:
        """Rollback current entity fields to a target version and append a rollback version."""
        target = await self.get_version_by_number(session, entity_type, entity_id, target_version)
        if target is None:
            raise NotFoundError("ArtifactVersion", target_version)

        if entity_type == "character":
            entity = await session.get(Character, entity_id)
            if entity is None:
                raise NotFoundError("Character", entity_id)
            self._apply_snapshot(entity, target.snapshot, ROLLBACK_FIELDS["character"])
            session.add(entity)
            await session.flush()
            return await self.create_version(
                session,
                entity_type,
                entity_id,
                character_snapshot(entity),
                trigger="rollback",
            )

        entity = await session.get(Shot, entity_id)
        if entity is None:
            raise NotFoundError("Shot", entity_id)
        self._apply_snapshot(entity, target.snapshot, ROLLBACK_FIELDS["shot"])
        session.add(entity)
        await session.flush()
        return await self.create_version(
            session,
            entity_type,
            entity_id,
            shot_snapshot(entity),
            trigger="rollback",
        )

    async def auto_snapshot_character(
        self,
        session: AsyncSession,
        character: Character,
        run_id: int | None = None,
        trigger: str = "generation",
    ) -> ArtifactVersion | None:
        """Create a Character snapshot before mutation when entity is persisted."""
        if character.id is None:
            return None
        return await self.create_version(
            session,
            "character",
            character.id,
            character_snapshot(character),
            run_id=run_id,
            trigger=trigger,
        )

    async def auto_snapshot_shot(
        self,
        session: AsyncSession,
        shot: Shot,
        run_id: int | None = None,
        trigger: str = "generation",
    ) -> ArtifactVersion | None:
        """Create a Shot snapshot before mutation when entity is persisted."""
        if shot.id is None:
            return None
        return await self.create_version(
            session,
            "shot",
            shot.id,
            shot_snapshot(shot),
            run_id=run_id,
            trigger=trigger,
        )

    async def _project_id_for_entity(
        self, session: AsyncSession, entity_type: EntityType, entity_id: int
    ) -> int:
        model = Character if entity_type == "character" else Shot
        entity = await session.get(model, entity_id)
        if entity is None:
            raise NotFoundError(model.__name__, entity_id)
        return entity.project_id

    def _apply_snapshot(self, entity: Any, snapshot: dict[str, Any], fields: Iterable[str]) -> None:
        for field in fields:
            if field in snapshot:
                setattr(entity, field, snapshot[field])
