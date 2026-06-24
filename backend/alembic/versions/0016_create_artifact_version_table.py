"""create artifact version table

Revision ID: 0016
Revises: 0015
"""
from alembic import op
import sqlalchemy as sa

revision = "0016_create_artifact_version_table"
down_revision = "0015_add_exports_to_project"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "artifactversion",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=True),
        sa.Column("trigger", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"]),
        sa.ForeignKeyConstraint(["run_id"], ["agentrun.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_artifactversion_project_id"), "artifactversion", ["project_id"], unique=False)
    op.create_index(op.f("ix_artifactversion_entity_type"), "artifactversion", ["entity_type"], unique=False)
    op.create_index(op.f("ix_artifactversion_entity_id"), "artifactversion", ["entity_id"], unique=False)
    op.create_index(op.f("ix_artifactversion_run_id"), "artifactversion", ["run_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_artifactversion_run_id"), table_name="artifactversion")
    op.drop_index(op.f("ix_artifactversion_entity_id"), table_name="artifactversion")
    op.drop_index(op.f("ix_artifactversion_entity_type"), table_name="artifactversion")
    op.drop_index(op.f("ix_artifactversion_project_id"), table_name="artifactversion")
    op.drop_table("artifactversion")
