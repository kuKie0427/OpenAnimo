"""add thread_id to agentrun

Revision ID: 0010
Revises: 0009
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_add_thread_id_to_agentrun"
down_revision = "0009_create_asset_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agentrun", sa.Column("thread_id", sa.String(), nullable=True, index=True))


def downgrade() -> None:
    op.drop_column("agentrun", "thread_id")
