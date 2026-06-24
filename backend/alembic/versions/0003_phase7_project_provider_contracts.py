"""phase7 project provider contracts

Revision ID: 0003_phase7_project_provider_contracts
Revises: 0002_phase3_approval_workflow
Create Date: 2026-04-18 00:00:00

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0003_phase7_project_provider_contracts"
down_revision = "0002_phase3_approval_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("project", sa.Column("text_provider_override", sa.String(), nullable=True))
    op.add_column("project", sa.Column("image_provider_override", sa.String(), nullable=True))
    op.add_column("project", sa.Column("video_provider_override", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("project", "video_provider_override")
    op.drop_column("project", "image_provider_override")
    op.drop_column("project", "text_provider_override")
