"""add model_name to agent_trace

Revision ID: 0021
Revises: 0020
"""
from alembic import op
import sqlalchemy as sa

revision = "0021_add_model_name_to_agent_trace"
down_revision = "0020_create_agent_trace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_trace",
        sa.Column("model_name", sa.String(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("agent_trace", "model_name")
