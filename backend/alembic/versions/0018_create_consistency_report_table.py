"""create consistency_report table

Revision ID: 0018
Revises: 0017
"""
from alembic import op
import sqlalchemy as sa

revision = "0018_create_consistency_report_table"
down_revision = "0017_add_story_outline_to_project"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "consistency_report",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("project.id"), index=True, nullable=False),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("agentrun.id"), nullable=True),
        sa.Column("report_data", sa.JSON(), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("consistency_report")
