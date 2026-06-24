"""导出相关 Schema"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ExportRequest(BaseModel):
    """导出请求"""

    format: Literal["pdf", "webtoon", "vertical"]
    include_dialogue: bool = True
    include_character_info: bool = True


class ExportVerticalRequest(BaseModel):
    """竖屏视频导出请求"""

    reframe_mode: str = "smart"
    target_aspect: str = "9:16"


class ExportResponse(BaseModel):
    """导出响应"""

    export_id: str
    project_id: int
    format: str
    status: Literal["processing", "completed", "failed"]
    download_url: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)


class ExportCompletedEventData(BaseModel):
    """WebSocket export_completed 事件数据"""

    export_id: str
    format: str
    download_url: str | None = None
    status: Literal["completed", "failed"]
    error: str | None = None
