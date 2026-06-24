from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.db.utils import utcnow


class Asset(SQLModel, table=True):
    """全局资产 — 角色和场景跨项目复用"""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    asset_type: str = Field(index=True)  # "character" | "scene"
    description: Optional[str] = None
    image_url: Optional[str] = None
    metadata_json: Optional[str] = None  # 额外元数据 (color palette, tags, etc.)
    source_project_id: Optional[int] = Field(default=None, foreign_key="project.id")
    tags: Optional[str] = None  # comma-separated tags
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
