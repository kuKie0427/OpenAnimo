"""add script_markdown to project

Revision ID: 0026
Revises: 0025
"""
from alembic import op
import sqlalchemy as sa

revision = "0026_add_script_markdown_to_project"
down_revision = "0025_add_voice_profile_to_character"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col["name"] for col in inspector.get_columns("project")]
    if "script_markdown" not in columns:
        op.add_column("project", sa.Column("script_markdown", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("project", "script_markdown")
