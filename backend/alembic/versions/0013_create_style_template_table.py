"""create style_template table

Revision ID: 0013
Revises: 0012
"""
from alembic import op
import sqlalchemy as sa

revision = "0013_create_style_template_table"
down_revision = "0012_add_character_bible_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "style_template",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, index=True),
        sa.Column("slug", sa.String(), nullable=False, unique=True, index=True),
        sa.Column("category", sa.String(), nullable=False, server_default="custom", index=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("style_prompt", sa.String(), nullable=False),
        sa.Column("color_palette", sa.JSON(), nullable=True),
        sa.Column("negative_prompt", sa.String(), nullable=True),
        sa.Column("preview_image_url", sa.String(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("style_template")
