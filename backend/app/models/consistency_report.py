# pyright: reportArgumentType=false, reportAttributeAccessIssue=false, reportAssignmentType=false
"""角色一致性评估报告持久化模型"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

from app.db.utils import utcnow


class ConsistencyReport(SQLModel, table=True):
    """角色一致性评估报告 — 持久化到数据库"""

    __tablename__ = "consistency_report"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    run_id: Optional[int] = Field(default=None, foreign_key="agentrun.id")
    report_data: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    overall_score: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=utcnow)
