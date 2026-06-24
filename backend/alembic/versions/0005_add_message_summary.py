"""add message summary column

Revision ID: 0005_add_message_summary
Revises: 0004_phase9_agent_run_provider_snapshot
Create Date: 2026-05-03

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0005_add_message_summary"
down_revision = "0004_phase9_agent_run_provider_snapshot"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)
    existing = {col["name"] for col in inspector.get_columns("message")}
    if "summary" not in existing:
        op.add_column("message", sa.Column("summary", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("message", "summary")
