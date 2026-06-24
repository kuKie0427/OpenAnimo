from datetime import datetime

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel

from app.db.utils import utcnow


class ConfigItem(SQLModel, table=True):
    """Environment configuration stored in the database."""

    key: str = Field(primary_key=True, max_length=255)
    value: str = Field(default="", sa_column=Column(Text, nullable=False))
    description: str | None = None
    is_sensitive: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
