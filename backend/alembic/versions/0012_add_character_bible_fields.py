"""add character bible fields

Revision ID: 0012
Revises: 0011
"""
from alembic import op
import sqlalchemy as sa

revision = "0012_add_character_bible_fields"
down_revision = "0011_add_seed_to_shot"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("character", sa.Column("reference_images", sa.JSON(), nullable=True))
    op.add_column("character", sa.Column("face_embedding", sa.Text(), nullable=True))
    op.add_column("character", sa.Column("visual_notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("character", "visual_notes")
    op.drop_column("character", "face_embedding")
    op.drop_column("character", "reference_images")
