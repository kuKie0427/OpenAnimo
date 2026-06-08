# pyright: reportArgumentType=false, reportAttributeAccessIssue=false, reportAssignmentType=false
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

from app.db.utils import utcnow


class StyleTemplate(SQLModel, table=True):
    """风格模板"""

    __tablename__ = "style_template"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)  # 模板名称，如 "日系动漫"
    slug: str = Field(unique=True, index=True)  # URL 标识，如 "anime"
    category: str = Field(default="custom", index=True)  # builtin / custom
    description: Optional[str] = None  # 模板描述
    style_prompt: str  # 注入到 image prompt 中的风格描述
    color_palette: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=True))
    negative_prompt: Optional[str] = None  # 负面提示词
    preview_image_url: Optional[str] = None  # 预览图 URL
    sort_order: int = Field(default=0)  # 排序权重
    is_active: bool = Field(default=True)  # 是否启用
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
