# pyright: reportArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SessionDep
from app.db.utils import utcnow
from app.models.style_template import StyleTemplate
from app.schemas.style_template import (
    StyleTemplateCreate,
    StyleTemplateListRead,
    StyleTemplateRead,
    StyleTemplateUpdate,
)

router = APIRouter()


async def _get_by_slug(session: AsyncSession, slug: str) -> StyleTemplate | None:
    res = await session.execute(select(StyleTemplate).where(StyleTemplate.slug == slug))
    return res.scalar_one_or_none()


@router.get("", response_model=StyleTemplateListRead)
async def list_style_templates(
    session: AsyncSession = SessionDep,
    category: str | None = Query(default=None, description="Filter by category: builtin / custom"),
):
    """List all active style templates, optionally filtered by category."""
    query = select(StyleTemplate).where(StyleTemplate.is_active.is_(True))
    if category is not None:
        query = query.where(StyleTemplate.category == category)
    query = query.order_by(StyleTemplate.sort_order.desc(), StyleTemplate.name.asc())
    res = await session.execute(query)
    items = res.scalars().all()
    return StyleTemplateListRead(
        items=[StyleTemplateRead.model_validate(t) for t in items],
        total=len(items),
    )


@router.get("/{slug}", response_model=StyleTemplateRead)
async def get_style_template(
    slug: str,
    session: AsyncSession = SessionDep,
):
    """Get a single style template by slug."""
    template = await _get_by_slug(session, slug)
    if not template:
        raise HTTPException(status_code=404, detail=f"Style template '{slug}' not found")
    return StyleTemplateRead.model_validate(template)


@router.post("", response_model=StyleTemplateRead, status_code=status.HTTP_201_CREATED)
async def create_style_template(
    payload: StyleTemplateCreate,
    session: AsyncSession = SessionDep,
):
    """Create a custom style template."""
    # Check slug uniqueness
    existing = await _get_by_slug(session, payload.slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Style template with slug '{payload.slug}' already exists",
        )
    template = StyleTemplate(
        name=payload.name,
        slug=payload.slug,
        category="custom",
        description=payload.description,
        style_prompt=payload.style_prompt,
        color_palette=payload.color_palette,
        negative_prompt=payload.negative_prompt,
        preview_image_url=payload.preview_image_url,
        sort_order=0,
        is_active=True,
    )
    session.add(template)
    await session.commit()
    await session.refresh(template)
    return StyleTemplateRead.model_validate(template)


@router.put("/{slug}", response_model=StyleTemplateRead)
async def update_style_template(
    slug: str,
    payload: StyleTemplateUpdate,
    session: AsyncSession = SessionDep,
):
    """Update a custom style template. Builtin templates cannot be modified."""
    template = await _get_by_slug(session, slug)
    if not template:
        raise HTTPException(status_code=404, detail=f"Style template '{slug}' not found")
    if template.category == "builtin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify builtin style templates",
        )
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(template, key, value)
    template.updated_at = utcnow()
    session.add(template)
    await session.commit()
    await session.refresh(template)
    return StyleTemplateRead.model_validate(template)


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_style_template(
    slug: str,
    session: AsyncSession = SessionDep,
):
    """Delete a custom style template. Builtin templates cannot be deleted."""
    template = await _get_by_slug(session, slug)
    if not template:
        raise HTTPException(status_code=404, detail=f"Style template '{slug}' not found")
    if template.category == "builtin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete builtin style templates",
        )
    await session.delete(template)
    await session.commit()
