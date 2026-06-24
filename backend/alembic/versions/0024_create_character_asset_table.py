"""create character_asset table

Revision ID: 0024
Revises: 0023
"""
from alembic import op
import sqlalchemy as sa

revision = "0024_create_character_asset_table"
down_revision = "0023_add_aspect_ratio_to_project"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "characterasset" not in inspector.get_table_names():
        op.create_table(
            "characterasset",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("character_id", sa.Integer(), nullable=False),
            sa.Column("angle", sa.String(), nullable=False),
            sa.Column("emotion", sa.String(), nullable=False),
            sa.Column("image_url", sa.String(), nullable=True),
            sa.Column("face_embedding", sa.String(), nullable=True),
            sa.Column("prompt", sa.String(), nullable=True),
            sa.Column("seed", sa.Integer(), nullable=True),
            sa.Column("is_approved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["character_id"],
                ["character.id"],
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_characterasset_character_id"),
            "characterasset",
            ["character_id"],
            unique=False,
        )
        op.create_index(
            "ix_characterasset_character_angle",
            "characterasset",
            ["character_id", "angle"],
            unique=False,
        )
        op.create_index(
            "ix_characterasset_character_emotion",
            "characterasset",
            ["character_id", "emotion"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index("ix_characterasset_character_emotion", table_name="characterasset")
    op.drop_index("ix_characterasset_character_angle", table_name="characterasset")
    op.drop_index(op.f("ix_characterasset_character_id"), table_name="characterasset")
    op.drop_table("characterasset")
