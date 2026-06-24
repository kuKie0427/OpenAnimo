# pyright: reportArgumentType=false, reportAttributeAccessIssue=false
"""Script markdown API routes"""
from __future__ import annotations

import asyncio
import re

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentContext
from app.agents.plan import PlanAgent
from app.api.deps import AdminDep, SessionDep, SettingsDep, WsManagerDep, get_or_404
from app.api.v1.routes.generation import _start_project_task
from app.config import Settings
from app.db.session import async_session_maker
from app.db.utils import utcnow
from app.models.agent_run import AgentRun
from app.models.project import Project, Shot
from app.services.anchor_service import parse_anchors
from app.services.image_factory import create_image_service
from app.services.task_manager import task_manager
from app.services.text_factory import create_text_service
from app.services.video_factory import create_video_service
from app.ws.manager import ConnectionManager


class ScriptMarkdownResponse(BaseModel):
    script_markdown: str


class ScriptMarkdownUpdate(BaseModel):
    script_markdown: str


class AnchorItem(BaseModel):
    shot_id: int
    paragraph_index: int
    line_number: int


class AnchorsResponse(BaseModel):
    anchors: list[AnchorItem]


class SyncMapEntry(BaseModel):
    shot_id: int
    paragraph_index: int
    line_number: int
    shot_order: int
    shot_description: str
    shot_image_url: str | None
    is_synced: bool


class SyncMapResponse(BaseModel):
    sync_map: list[SyncMapEntry]


class SyncParagraphRequest(BaseModel):
    paragraph_index: int
    paragraph_text: str = Field(max_length=100_000)


class SyncParagraphResponse(BaseModel):
    status: str = "syncing"
    paragraph_index: int


async def _run_shot_sync(
    project_id: int,
    paragraph_index: int,
    settings: Settings,
    ws: ConnectionManager,
) -> None:
    """Background task: re-plan shots for a single paragraph via PlanAgent."""
    run_id: int | None = None
    try:
        async with async_session_maker() as task_session:
            project = await task_session.get(Project, project_id)
            if not project:
                return

            run = AgentRun(
                project_id=project_id,
                status="running",
                current_agent="plan",
                progress=0.0,
            )
            task_session.add(run)
            await task_session.commit()
            await task_session.refresh(run)
            run_id = run.id

            await ws.send_event(
                project_id,
                {
                    "type": "shot_sync_progress",
                    "data": {"paragraph_index": paragraph_index, "status": "starting"},
                },
            )

            script = project.script_markdown
            paragraphs = re.split(r"\n\s*\n", script)
            if 0 <= paragraph_index < len(paragraphs):
                para = re.sub(r"<!--\s*shot:\s*\d+\s*-->", "", paragraphs[paragraph_index])
                para = f"<!-- shot:replanning -->\n{para}"
                paragraphs[paragraph_index] = para
                project.script_markdown = "\n\n".join(paragraphs)
                project.updated_at = utcnow()
                task_session.add(project)
                await task_session.commit()

            ctx = AgentContext(
                settings=settings,
                session=task_session,
                ws=ws,
                project=project,
                run=run,
                llm=create_text_service(settings),
                image=create_image_service(settings),
                video=create_video_service(settings),
                rerun_mode="incremental",
            )

            await PlanAgent().run_shots(ctx)

            await ws.send_event(
                project_id,
                {
                    "type": "shot_sync_progress",
                    "data": {"paragraph_index": paragraph_index, "status": "completed"},
                },
            )

            run.status = "succeeded"
            run.updated_at = utcnow()
            task_session.add(run)
            await task_session.commit()
    except asyncio.CancelledError:
        if run_id is not None:
            async with async_session_maker() as cancel_session:
                run_obj = await cancel_session.get(AgentRun, run_id)
                if run_obj and run_obj.status not in ("cancelled", "failed", "succeeded"):
                    run_obj.status = "cancelled"
                    await cancel_session.commit()
        raise
    except Exception:
        if run_id is not None:
            async with async_session_maker() as err_session:
                run_obj = await err_session.get(AgentRun, run_id)
                if run_obj and run_obj.status not in ("failed", "succeeded"):
                    run_obj.status = "failed"
                    run_obj.updated_at = utcnow()
                    await err_session.commit()
        raise
    finally:
        task_manager.remove(project_id)


router = APIRouter(prefix="/{project_id}/script", tags=["script"])


@router.get("", response_model=ScriptMarkdownResponse)
async def get_script_markdown(
    project_id: int,
    session: AsyncSession = SessionDep,
):
    """Get the script markdown for a project."""
    project = await get_or_404(session, Project, project_id)
    return ScriptMarkdownResponse(script_markdown=project.script_markdown)


@router.put("", response_model=ScriptMarkdownResponse)
async def update_script_markdown(
    project_id: int,
    data: ScriptMarkdownUpdate,
    session: AsyncSession = SessionDep,
    _: None = AdminDep,
):
    """Update the script markdown for a project (admin only)."""
    project = await get_or_404(session, Project, project_id)
    project.script_markdown = data.script_markdown
    project.updated_at = utcnow()
    session.add(project)
    await session.commit()
    return ScriptMarkdownResponse(script_markdown=project.script_markdown)


@router.get("/anchors", response_model=AnchorsResponse)
async def get_script_anchors(
    project_id: int,
    session: AsyncSession = SessionDep,
):
    """Parse shot anchors from script markdown.

    Scans `<!-- shot:{shot_id} -->` markers in the project's script_markdown
    and returns their locations by paragraph index and line number.
    """
    project = await get_or_404(session, Project, project_id)
    anchors = parse_anchors(project.script_markdown)
    return AnchorsResponse(anchors=[AnchorItem(**a) for a in anchors])


@router.get("/sync", response_model=SyncMapResponse)
async def get_script_sync_map(
    project_id: int,
    session: AsyncSession = SessionDep,
    _: None = AdminDep,
):
    """Return shot↔paragraph sync map for the project's script.

    Parses ``<!-- shot:N -->`` anchors from script_markdown, cross-references
    with the Shot table, and returns a sorted list of entries with shot metadata
    and ``is_synced`` flags.
    """
    project = await get_or_404(session, Project, project_id)
    anchors = parse_anchors(project.script_markdown)

    stmt = select(Shot).where(Shot.project_id == project_id)
    result = await session.execute(stmt)
    shots = result.scalars().all()
    shot_dict: dict[int, Shot] = {s.id: s for s in shots if s.id is not None}

    sync_map: list[SyncMapEntry] = []
    for anchor in anchors:
        shot_id = anchor["shot_id"]
        shot = shot_dict.get(shot_id)
        sync_map.append(
            SyncMapEntry(
                shot_id=shot_id,
                paragraph_index=anchor["paragraph_index"],
                line_number=anchor["line_number"],
                shot_order=shot.order if shot else -1,
                shot_description=shot.description if shot else "",
                shot_image_url=shot.image_url if shot else None,
                is_synced=shot_id in shot_dict,
            )
        )

    sync_map.sort(key=lambda e: e.paragraph_index)
    return SyncMapResponse(sync_map=sync_map)


@router.post("/sync/paragraph", response_model=SyncParagraphResponse)
async def sync_paragraph(
    project_id: int,
    data: SyncParagraphRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = SessionDep,
    settings: Settings = SettingsDep,
    ws: ConnectionManager = WsManagerDep,
    _: None = AdminDep,
):
    """Trigger paragraph-to-shots re-planning for a single paragraph.

    Replaces the paragraph text in script_markdown and launches a background
    task that calls PlanAgent.run_shots() in incremental mode.
    """
    project = await get_or_404(session, Project, project_id)

    script = project.script_markdown
    paragraphs = re.split(r"\n\s*\n", script)
    if 0 <= data.paragraph_index < len(paragraphs):
        paragraphs[data.paragraph_index] = data.paragraph_text
        project.script_markdown = "\n\n".join(paragraphs)
        project.updated_at = utcnow()
        session.add(project)
        await session.commit()

    background_tasks.add_task(
        _start_project_task,
        project_id,
        _run_shot_sync(project_id, data.paragraph_index, settings, ws),
    )

    return SyncParagraphResponse(status="syncing", paragraph_index=data.paragraph_index)
