"""add shot detail fields scene/action/expression/lighting/dialogue/sfx

Revision ID: 0006
Revises: 0005
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_add_shot_detail_fields"
down_revision = "0005_add_message_summary"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for col in ("scene", "action", "expression", "lighting", "dialogue", "sfx"):
        op.add_column("shot", sa.Column(col, sa.String(), nullable=True))
    for col in (
        "approved_scene",
        "approved_action",
        "approved_expression",
        "approved_lighting",
        "approved_dialogue",
        "approved_sfx",
    ):
        op.add_column("shot", sa.Column(col, sa.String(), nullable=True))


def downgrade() -> None:
    for col in (
        "approved_sfx",
        "approved_dialogue",
        "approved_lighting",
        "approved_expression",
        "approved_action",
        "approved_scene",
    ):
        op.drop_column("shot", col)
    for col in ("sfx", "dialogue", "lighting", "expression", "action", "scene"):
        op.drop_column("shot", col)
