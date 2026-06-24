from __future__ import annotations

from collections.abc import AsyncGenerator
import secrets
from typing import TypeVar

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.session import get_session
from app.models.agent_run import AgentRun
from app.ws.manager import ConnectionManager, ws_manager

T = TypeVar("T")


async def get_app_settings() -> Settings:
    return get_settings()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_session():
        yield session


async def get_ws_manager() -> ConnectionManager:
    return ws_manager


async def require_admin(
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> None:
    settings = get_settings()
    if not settings.admin_token:
        return
    if not x_admin_token or not secrets.compare_digest(x_admin_token, settings.admin_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")


def require_run_id(run: AgentRun) -> int:
    run_id = run.id
    if run_id is None:
        raise RuntimeError("Persisted AgentRun is missing an id")
    return run_id


async def get_or_404(
    session: AsyncSession, model: type[T], id: int, detail: str | None = None
) -> T:
    """Fetch a DB object by primary key or raise 404."""
    obj = await session.get(model, id)
    if not obj:
        raise HTTPException(status_code=404, detail=detail or f"{model.__name__} not found")
    return obj


SettingsDep = Depends(get_app_settings)
SessionDep = Depends(get_db_session)
WsManagerDep = Depends(get_ws_manager)
AdminDep = Depends(require_admin)
