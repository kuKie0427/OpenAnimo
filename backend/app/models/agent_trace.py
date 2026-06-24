# pyright: reportArgumentType=false, reportAttributeAccessIssue=false, reportAssignmentType=false
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class AgentTrace(SQLModel, table=True):
    __tablename__ = "agent_trace"

    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="agentrun.id", index=True)
    agent_name: str
    model_name: str = Field(default="")
    stage: str
    method: str
    start_time: datetime
    end_time: Optional[datetime] = None
    llm_calls: int = 0
    tokens_input: int = 0
    tokens_output: int = 0
    images_generated: int = 0
    video_seconds: float = 0.0
    status: str = "running"
    error: Optional[str] = None
