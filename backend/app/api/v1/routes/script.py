# pyright: reportArgumentType=false, reportAttributeAccessIssue=false
"""Script markdown API routes"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminDep, SessionDep, get_or_404
from app.db.utils import utcnow
from app.models.project import Project
from app.services.anchor_service import parse_anchors


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
