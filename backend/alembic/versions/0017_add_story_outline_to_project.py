"""add story outline to project

Revision ID: 0017
Revises: 0016
"""
from alembic import op
import sqlalchemy as sa

revision = "0017_add_story_outline_to_project"
down_revision = "0016_create_artifact_version_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("project", sa.Column("story_outline", sa.JSON(), nullable=True))
    op.add_column("project", sa.Column("visual_bible", sa.String(), nullable=True))
    op.add_column(
        "project",
        sa.Column("outline_approved", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("project", "outline_approved")
    op.drop_column("project", "visual_bible")
    op.drop_column("project", "story_outline")
