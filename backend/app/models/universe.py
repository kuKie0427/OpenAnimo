"""Universe / IP 宇宙模型 — 管理跨项目的共享世界观和角色库。"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, Relationship, SQLModel

from app.db.utils import utcnow

if TYPE_CHECKING:
    from app.models.project import Project


class Universe(SQLModel, table=True):
    """IP 宇宙 — 管理跨项目的共享世界观和角色库"""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None
    world_setting: Optional[str] = None  # 世界观设定文本
    style_rules: Optional[str] = None  # 统一风格规则
    cover_image_url: Optional[str] = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    # relationships
    projects: List["Project"] = Relationship(back_populates="universe")
    shared_characters: List["SharedCharacter"] = Relationship(
        back_populates="universe",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    project_links: List["UniverseProjectLink"] = Relationship(
        back_populates="universe",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class SharedCharacter(SQLModel, table=True):
    """宇宙级共享角色 — 跨项目复用的角色圣经"""

    id: Optional[int] = Field(default=None, primary_key=True)
    universe_id: int = Field(foreign_key="universe.id", index=True)
    name: str
    description: Optional[str] = None
    visual_notes: Optional[str] = None  # 角色视觉圣经
    reference_images: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    face_embedding: Optional[str] = None  # 512维向量 JSON
    canonical_image_url: Optional[str] = None  # 标准形象图
    character_tags: Optional[str] = None  # comma-separated tags
    source_project_id: Optional[int] = Field(
        default=None, foreign_key="project.id"
    )
    source_character_id: Optional[int] = Field(default=None)  # 原始角色 ID
    version: int = Field(default=1)  # 版本号（角色圣经可能更新）
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    universe: Optional[Universe] = Relationship(back_populates="shared_characters")


class UniverseProjectLink(SQLModel, table=True):
    """宇宙-项目关联"""

    id: Optional[int] = Field(default=None, primary_key=True)
    universe_id: int = Field(foreign_key="universe.id", index=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    chapter_number: Optional[int] = None  # 第几章/集
    chapter_title: Optional[str] = None  # 章节标题
    is_main_story: bool = Field(default=True)  # 主线/外传
    created_at: datetime = Field(default_factory=utcnow)

    universe: Optional[Universe] = Relationship(back_populates="project_links")
    project: Optional["Project"] = Relationship(back_populates="universe_link")
