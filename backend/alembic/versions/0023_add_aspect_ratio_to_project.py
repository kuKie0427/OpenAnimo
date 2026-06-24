"""add aspect_ratio to project

Revision ID: 0023
Revises: 0022
"""
from alembic import op
import sqlalchemy as sa

revision = "0023_add_aspect_ratio_to_project"
down_revision = "0022_add_video_seconds_to_agent_trace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col["name"] for col in inspector.get_columns("project")]
    if "aspect_ratio" not in columns:
        op.add_column(
            "project",
            sa.Column(
                "aspect_ratio",
                sa.String(),
                nullable=True,
                server_default="16:9",
            ),
        )


def downgrade() -> None:
    op.drop_column("project", "aspect_ratio")
