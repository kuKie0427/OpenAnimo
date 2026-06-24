"""phase9 agent run provider snapshot

Revision ID: 0004_phase9_agent_run_provider_snapshot
Revises: 0003_phase7_project_provider_contracts

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0004_phase9_agent_run_provider_snapshot"
down_revision = "0003_phase7_project_provider_contracts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agentrun", sa.Column("provider_snapshot", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("agentrun", "provider_snapshot")
