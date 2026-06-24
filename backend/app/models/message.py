from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.db.utils import utcnow


class Message(SQLModel, table=True):
    """对话消息"""

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    run_id: Optional[int] = Field(default=None, foreign_key="agentrun.id", index=True)
    agent: str  # agent 名称
    role: str  # assistant, user, system, error, handoff, separator, info
    content: str  # 消息内容
    summary: Optional[str] = None  # 摘要（用于确认环节显示）
    progress: Optional[float] = None  # 进度值（0-1）
    is_loading: bool = Field(default=False)  # 是否显示加载动画
    created_at: datetime = Field(default_factory=utcnow)