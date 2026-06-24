"""add project target_shot_count and character_hints

Revision ID: 0007
Revises: 0006
"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg

revision = "0007_add_project_structured_input"
down_revision = "0006_add_shot_detail_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("project", sa.Column("target_shot_count", sa.Integer(), nullable=True))
    op.add_column("project", sa.Column("character_hints", pg.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("project", "character_hints")
    op.drop_column("project", "target_shot_count")
