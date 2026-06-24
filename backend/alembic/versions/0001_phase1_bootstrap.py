"""phase1 bootstrap schema

Revision ID: 0001_phase1_bootstrap
Revises:
Create Date: 2026-04-11 00:00:00

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_phase1_bootstrap"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("story", sa.String(), nullable=True),
        sa.Column("style", sa.String(), nullable=False),
        sa.Column("summary", sa.String(), nullable=True),
        sa.Column("video_url", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "agentrun",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("current_agent", sa.String(), nullable=True),
        sa.Column("progress", sa.Float(), nullable=False),
        sa.Column("route_decision", sa.Text(), nullable=True),
        sa.Column("patch_plan", sa.Text(), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("resource_type", sa.String(), nullable=True),
        sa.Column("resource_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agentrun_project_id"), "agentrun", ["project_id"], unique=False)
    op.create_index(op.f("ix_agentrun_resource_id"), "agentrun", ["resource_id"], unique=False)
    op.create_index(op.f("ix_agentrun_resource_type"), "agentrun", ["resource_type"], unique=False)
    op.create_index(op.f("ix_agentrun_status"), "agentrun", ["status"], unique=False)
    op.create_table(
        "agentmessage",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("agent", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["agentrun.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agentmessage_run_id"), "agentmessage", ["run_id"], unique=False)
    op.create_table(
        "message",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=True),
        sa.Column("agent", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("progress", sa.Float(), nullable=True),
        sa.Column("is_loading", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"]),
        sa.ForeignKeyConstraint(["run_id"], ["agentrun.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_message_project_id"), "message", ["project_id"], unique=False)
    op.create_index(op.f("ix_message_run_id"), "message", ["run_id"], unique=False)
    op.create_table(
        "configitem",
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_index(
        op.f("ix_configitem_is_sensitive"), "configitem", ["is_sensitive"], unique=False
    )
    op.create_table(
        "character",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_character_project_id"), "character", ["project_id"], unique=False)
    op.create_table(
        "shot",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("prompt", sa.String(), nullable=True),
        sa.Column("image_prompt", sa.String(), nullable=True),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.Column("video_url", sa.String(), nullable=True),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_shot_order"), "shot", ["order"], unique=False)
    op.create_index(op.f("ix_shot_project_id"), "shot", ["project_id"], unique=False)

    op.create_table(
        "run",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("thread_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_run_project_id"), "run", ["project_id"], unique=False)
    op.create_index(op.f("ix_run_status"), "run", ["status"], unique=False)
    op.create_index(op.f("ix_run_thread_id"), "run", ["thread_id"], unique=True)

    op.create_table(
        "stage",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"]),
        sa.ForeignKeyConstraint(["run_id"], ["run.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_stage_name"), "stage", ["name"], unique=False)
    op.create_index(op.f("ix_stage_project_id"), "stage", ["project_id"], unique=False)
    op.create_index(op.f("ix_stage_run_id"), "stage", ["run_id"], unique=False)
    op.create_index(op.f("ix_stage_status"), "stage", ["status"], unique=False)

    op.create_table(
        "artifact",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("stage_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("artifact_type", sa.String(), nullable=False),
        sa.Column("uri", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"]),
        sa.ForeignKeyConstraint(["run_id"], ["run.id"]),
        sa.ForeignKeyConstraint(["stage_id"], ["stage.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_artifact_artifact_type"), "artifact", ["artifact_type"], unique=False)
    op.create_index(op.f("ix_artifact_name"), "artifact", ["name"], unique=False)
    op.create_index(op.f("ix_artifact_project_id"), "artifact", ["project_id"], unique=False)
    op.create_index(op.f("ix_artifact_run_id"), "artifact", ["run_id"], unique=False)
    op.create_index(op.f("ix_artifact_stage_id"), "artifact", ["stage_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_artifact_stage_id"), table_name="artifact")
    op.drop_index(op.f("ix_artifact_run_id"), table_name="artifact")
    op.drop_index(op.f("ix_artifact_project_id"), table_name="artifact")
    op.drop_index(op.f("ix_artifact_name"), table_name="artifact")
    op.drop_index(op.f("ix_artifact_artifact_type"), table_name="artifact")
    op.drop_table("artifact")
    op.drop_index(op.f("ix_stage_status"), table_name="stage")
    op.drop_index(op.f("ix_stage_run_id"), table_name="stage")
    op.drop_index(op.f("ix_stage_project_id"), table_name="stage")
    op.drop_index(op.f("ix_stage_name"), table_name="stage")
    op.drop_table("stage")
    op.drop_index(op.f("ix_run_thread_id"), table_name="run")
    op.drop_index(op.f("ix_run_status"), table_name="run")
    op.drop_index(op.f("ix_run_project_id"), table_name="run")
    op.drop_table("run")
    op.drop_index(op.f("ix_shot_project_id"), table_name="shot")
    op.drop_index(op.f("ix_shot_order"), table_name="shot")
    op.drop_table("shot")
    op.drop_index(op.f("ix_character_project_id"), table_name="character")
    op.drop_table("character")
    op.drop_index(op.f("ix_configitem_is_sensitive"), table_name="configitem")
    op.drop_table("configitem")
    op.drop_index(op.f("ix_message_run_id"), table_name="message")
    op.drop_index(op.f("ix_message_project_id"), table_name="message")
    op.drop_table("message")
    op.drop_index(op.f("ix_agentmessage_run_id"), table_name="agentmessage")
    op.drop_table("agentmessage")
    op.drop_index(op.f("ix_agentrun_status"), table_name="agentrun")
    op.drop_index(op.f("ix_agentrun_resource_type"), table_name="agentrun")
    op.drop_index(op.f("ix_agentrun_resource_id"), table_name="agentrun")
    op.drop_index(op.f("ix_agentrun_project_id"), table_name="agentrun")
    op.drop_table("agentrun")
    op.drop_table("project")
