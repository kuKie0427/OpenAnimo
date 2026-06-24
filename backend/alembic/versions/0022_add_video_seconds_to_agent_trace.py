"""add video_seconds to agent_trace

Revision ID: 0022
Revises: 0021
"""
from alembic import op
import sqlalchemy as sa

revision = "0022_add_video_seconds_to_agent_trace"
down_revision = "0021_add_model_name_to_agent_trace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if column already exists (idempotent migration)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col["name"] for col in inspector.get_columns("agent_trace")]
    if "video_seconds" not in columns:
        op.add_column(
            "agent_trace",
            sa.Column(
                "video_seconds",
                sa.Float(),
                nullable=False,
                server_default="0.0",
            ),
        )


def downgrade() -> None:
    op.drop_column("agent_trace", "video_seconds")
