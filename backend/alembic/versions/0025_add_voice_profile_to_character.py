"""add voice_profile to character, narrator_url/sfx_url to shot

Revision ID: 0025
Revises: 0024
"""
from alembic import op
import sqlalchemy as sa

revision = "0025_add_voice_profile_to_character"
down_revision = "0024_create_character_asset_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    char_cols = [col["name"] for col in inspector.get_columns("character")]
    if "voice_profile" not in char_cols:
        op.add_column("character", sa.Column("voice_profile", sa.JSON(), nullable=True))
    shot_cols = [col["name"] for col in inspector.get_columns("shot")]
    if "narrator_url" not in shot_cols:
        op.add_column("shot", sa.Column("narrator_url", sa.String(), nullable=True))
    if "sfx_url" not in shot_cols:
        op.add_column("shot", sa.Column("sfx_url", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("shot", "sfx_url")
    op.drop_column("shot", "narrator_url")
    op.drop_column("character", "voice_profile")
