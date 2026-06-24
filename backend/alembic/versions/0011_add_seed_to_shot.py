"""add seed to shot

Revision ID: 0011
Revises: 0010
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_add_seed_to_shot"
down_revision = "0010_add_thread_id_to_agentrun"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("shot", sa.Column("seed", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("shot", "seed")
