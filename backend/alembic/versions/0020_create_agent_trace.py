"""create agent_trace table

Revision ID: 0020
Revises: 0019
"""
from alembic import op
import sqlalchemy as sa

revision = "0020_create_agent_trace"
down_revision = "0013_storyboard_elements_reviews_exports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_trace",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("agentrun.id"), index=True, nullable=False),
        sa.Column("agent_name", sa.String(), nullable=False),
        sa.Column("stage", sa.String(), nullable=False),
        sa.Column("method", sa.String(), nullable=False),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=True),
        sa.Column("llm_calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_input", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_output", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("images_generated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(), nullable=False, server_default="running"),
        sa.Column("error", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("agent_trace")
