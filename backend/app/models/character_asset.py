from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel
from pydantic import field_validator

from app.db.utils import utcnow

if TYPE_CHECKING:
    from app.models.project import Character


class CharacterAsset(SQLModel, table=True):
    """角色多角度/多情绪资产"""

    id: Optional[int] = Field(default=None, primary_key=True)
    character_id: int = Field(foreign_key="character.id", index=True)
    angle: str  # one of: front, side, back, three_quarter
    emotion: str  # one of: smile, angry, crying, surprised
    image_url: Optional[str] = None
    face_embedding: Optional[str] = Field(default=None)  # JSON string of 512-dim float list
    prompt: Optional[str] = None  # The prompt used to generate this asset
    seed: Optional[int] = None  # deterministic seed for regeneration
    is_approved: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utcnow)

    character: Optional["Character"] = Relationship(back_populates="assets")

    @field_validator("angle")
    @classmethod
    def validate_angle(cls, v: str) -> str:
        allowed = {"front", "side", "back", "three_quarter"}
        if v not in allowed:
            raise ValueError(f"angle must be one of {allowed}, got {v!r}")
        return v

    @field_validator("emotion")
    @classmethod
    def validate_emotion(cls, v: str) -> str:
        allowed = {"smile", "angry", "crying", "surprised"}
        if v not in allowed:
            raise ValueError(f"emotion must be one of {allowed}, got {v!r}")
        return v
