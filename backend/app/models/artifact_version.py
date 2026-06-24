from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

from app.db.utils import utcnow


class ArtifactVersion(SQLModel, table=True):
    """产物版本快照 — 记录角色/分镜的每次变更。"""

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    entity_type: str = Field(index=True)  # character | shot
    entity_id: int = Field(index=True)
    version: int = Field(default=1, ge=1)
    snapshot: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    run_id: Optional[int] = Field(default=None, foreign_key="agentrun.id", index=True)
    trigger: str = Field(default="generation")
    created_at: datetime = Field(default_factory=utcnow)
