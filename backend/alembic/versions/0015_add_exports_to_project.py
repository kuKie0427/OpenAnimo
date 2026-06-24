"""add exports field to project

Revision ID: 0015
Revises: 0014
"""
from alembic import op
import sqlalchemy as sa

revision = "0015_add_exports_to_project"
down_revision = "0014_add_tts_bgm_to_shot"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("project", sa.Column("exports", sa.JSON(), nullable=True))

def downgrade() -> None:
    op.drop_column("project", "exports")
