"""create universe tables and add universe fields to project

Revision ID: 0019
Revises: 0018
"""
from alembic import op
import sqlalchemy as sa

revision = "0019_create_universe_tables"
down_revision = "0018_create_consistency_report_table"
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create universe table
    op.create_table(
        "universe",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), index=True, nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("world_setting", sa.Text(), nullable=True),
        sa.Column("style_rules", sa.Text(), nullable=True),
        sa.Column("cover_image_url", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    # Create sharedcharacter table
    op.create_table(
        "sharedcharacter",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("universe_id", sa.Integer(), sa.ForeignKey("universe.id"), index=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("visual_notes", sa.Text(), nullable=True),
        sa.Column("reference_images", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("face_embedding", sa.Text(), nullable=True),
        sa.Column("canonical_image_url", sa.String(), nullable=True),
        sa.Column("character_tags", sa.String(), nullable=True),
        sa.Column("source_project_id", sa.Integer(), sa.ForeignKey("project.id"), nullable=True),
        sa.Column("source_character_id", sa.Integer(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    # Create universeprojectlink table
    op.create_table(
        "universeprojectlink",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("universe_id", sa.Integer(), sa.ForeignKey("universe.id"), index=True, nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("project.id"), index=True, nullable=False),
        sa.Column("chapter_number", sa.Integer(), nullable=True),
        sa.Column("chapter_title", sa.String(), nullable=True),
        sa.Column("is_main_story", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    # Add universe fields to project table
    # Use batch_alter_table for SQLite compatibility (FK in ALTER not supported on SQLite)
    with op.batch_alter_table("project", schema=None) as batch_op:
        batch_op.add_column(sa.Column("universe_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("chapter_number", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("chapter_title", sa.String(), nullable=True))
        # FK created separately for SQLite compat; the relationship is enforced at app level
        # batch_op.create_foreign_key("fk_project_universe_id", "universe", ["universe_id"], ["id"])

def downgrade() -> None:
    # Remove universe fields from project
    with op.batch_alter_table("project", schema=None) as batch_op:
        batch_op.drop_column("chapter_title")
        batch_op.drop_column("chapter_number")
        batch_op.drop_column("universe_id")

    # Drop tables in reverse order
    op.drop_table("universeprojectlink")
    op.drop_table("sharedcharacter")
    op.drop_table("universe")
