"""phase3 approval workflow

Revision ID: 0002_phase3_approval_workflow
Revises: 0001_phase1_bootstrap
Create Date: 2026-04-11 00:00:00

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0002_phase3_approval_workflow"
down_revision = "0001_phase1_bootstrap"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "character",
        sa.Column("approved_name", sa.String(), nullable=True),
    )
    op.add_column(
        "character",
        sa.Column("approved_description", sa.String(), nullable=True),
    )
    op.add_column(
        "character",
        sa.Column("approved_image_url", sa.String(), nullable=True),
    )
    op.add_column(
        "character",
        sa.Column("approved_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "character",
        sa.Column("approval_version", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )

    op.add_column(
        "shot",
        sa.Column("camera", sa.String(), nullable=True),
    )
    op.add_column(
        "shot",
        sa.Column("motion_note", sa.String(), nullable=True),
    )
    op.add_column(
        "shot",
        sa.Column(
            "character_ids",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )
    op.add_column(
        "shot",
        sa.Column("approved_description", sa.String(), nullable=True),
    )
    op.add_column(
        "shot",
        sa.Column("approved_prompt", sa.String(), nullable=True),
    )
    op.add_column(
        "shot",
        sa.Column("approved_image_prompt", sa.String(), nullable=True),
    )
    op.add_column(
        "shot",
        sa.Column("approved_duration", sa.Float(), nullable=True),
    )
    op.add_column(
        "shot",
        sa.Column("approved_camera", sa.String(), nullable=True),
    )
    op.add_column(
        "shot",
        sa.Column("approved_motion_note", sa.String(), nullable=True),
    )
    op.add_column(
        "shot",
        sa.Column(
            "approved_character_ids",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )
    op.add_column(
        "shot",
        sa.Column("approved_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "shot",
        sa.Column("approval_version", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )

    op.create_table(
        "shot_character_binding",
        sa.Column("shot_id", sa.Integer(), nullable=False),
        sa.Column("character_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["shot_id"], ["shot.id"]),
        sa.ForeignKeyConstraint(["character_id"], ["character.id"]),
        sa.PrimaryKeyConstraint("shot_id", "character_id"),
    )
    op.create_index(
        op.f("ix_shot_character_binding_shot_id"),
        "shot_character_binding",
        ["shot_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_shot_character_binding_character_id"),
        "shot_character_binding",
        ["character_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_shot_character_binding_character_id"), table_name="shot_character_binding"
    )
    op.drop_index(op.f("ix_shot_character_binding_shot_id"), table_name="shot_character_binding")
    op.drop_table("shot_character_binding")

    op.drop_column("shot", "approval_version")
    op.drop_column("shot", "approved_at")
    op.drop_column("shot", "approved_character_ids")
    op.drop_column("shot", "approved_motion_note")
    op.drop_column("shot", "approved_camera")
    op.drop_column("shot", "approved_duration")
    op.drop_column("shot", "approved_image_prompt")
    op.drop_column("shot", "approved_prompt")
    op.drop_column("shot", "approved_description")
    op.drop_column("shot", "character_ids")
    op.drop_column("shot", "motion_note")
    op.drop_column("shot", "camera")

    op.drop_column("character", "approval_version")
    op.drop_column("character", "approved_at")
    op.drop_column("character", "approved_image_url")
    op.drop_column("character", "approved_description")
    op.drop_column("character", "approved_name")
