from __future__ import annotations

import pytest
from unittest.mock import patch

from app.api.deps import require_admin, get_app_settings, get_ws_manager

from fastapi import HTTPException


@pytest.mark.asyncio
async def test_get_app_settings_returns_settings():
    result = await get_app_settings()
    assert result is not None


@pytest.mark.asyncio
async def test_get_ws_manager_returns_manager():
    result = await get_ws_manager()
    assert result is not None


@pytest.mark.asyncio
async def test_require_admin_no_token_configured():
    with patch("app.api.deps.get_settings", return_value=type("S", (), {"admin_token": ""})()):
        result = await require_admin(x_admin_token=None)
        assert result is None


@pytest.mark.asyncio
async def test_require_admin_no_token_allows_any_header():
    with patch("app.api.deps.get_settings", return_value=type("S", (), {"admin_token": ""})()):
        result = await require_admin(x_admin_token="anything")
        assert result is None


@pytest.mark.asyncio
async def test_require_admin_wrong_token():
    with patch(
        "app.api.deps.get_settings", return_value=type("S", (), {"admin_token": "secret"})()
    ):
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(x_admin_token="wrong")
        assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_admin_correct_token():
    with patch(
        "app.api.deps.get_settings", return_value=type("S", (), {"admin_token": "secret"})()
    ):
        result = await require_admin(x_admin_token="secret")
        assert result is None


@pytest.mark.asyncio
async def test_require_admin_no_header():
    with patch(
        "app.api.deps.get_settings", return_value=type("S", (), {"admin_token": "secret"})()
    ):
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(x_admin_token=None)
        assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_or_404_returns_object(test_session):
    from app.api.deps import get_or_404
    from app.models.project import Project

    project = Project(title="Test", story="s", style="anime", status="draft")
    test_session.add(project)
    await test_session.commit()
    await test_session.refresh(project)

    assert project.id is not None
    result = await get_or_404(test_session, Project, project.id)
    assert result.id == project.id


@pytest.mark.asyncio
async def test_get_or_404_raises_404(test_session):
    from app.api.deps import get_or_404
    from app.models.project import Project

    with pytest.raises(HTTPException) as exc_info:
        await get_or_404(test_session, Project, 999999)
    assert exc_info.value.status_code == 404
    assert "Project not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_or_404_custom_detail(test_session):
    from app.api.deps import get_or_404
    from app.models.project import Project

    with pytest.raises(HTTPException) as exc_info:
        await get_or_404(test_session, Project, 999999, detail="Custom message")
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Custom message"
