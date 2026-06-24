"""add project creation_mode and reference_images

Revision ID: 0008
Revises: 0007
"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg

revision = "0008_add_project_creation_mode"
down_revision = "0007_add_project_structured_input"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("project", sa.Column("creation_mode", sa.String(), nullable=True))
    op.add_column("project", sa.Column("reference_images", pg.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("project", "reference_images")
    op.drop_column("project", "creation_mode")
