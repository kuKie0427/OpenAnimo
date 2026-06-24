"""add tts_url and bgm_type to shot

Revision ID: 0014
Revises: 0013
"""
from alembic import op
import sqlalchemy as sa

revision = "0014_add_tts_bgm_to_shot"
down_revision = "0013_create_style_template_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("shot", sa.Column("tts_url", sa.String(), nullable=True))
    op.add_column("shot", sa.Column("bgm_type", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("shot", "tts_url")
    op.drop_column("shot", "bgm_type")
