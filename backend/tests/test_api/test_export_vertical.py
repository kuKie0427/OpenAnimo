"""竖屏视频导出 API 路由测试"""
from __future__ import annotations

import pytest


class TestExportVerticalSchema:
    """ExportVerticalRequest Schema 测试"""

    def test_export_vertical_request_defaults(self):
        from app.schemas.export import ExportVerticalRequest
        req = ExportVerticalRequest()
        assert req.reframe_mode == "smart"
        assert req.target_aspect == "9:16"

    def test_export_vertical_request_custom(self):
        from app.schemas.export import ExportVerticalRequest
        req = ExportVerticalRequest(reframe_mode="center", target_aspect="9:16")
        assert req.reframe_mode == "center"
        assert req.target_aspect == "9:16"


class TestExportVerticalRoute:
    """竖屏导出 API 路由测试"""

    @pytest.mark.asyncio
    async def test_api_export_vertical_returns_202(
        self, async_client, test_session, ws_manager
    ):
        from tests.factories import create_project

        project = await create_project(test_session, title="Vertical Export Test")
        assert project.id is not None

        response = await async_client.post(
            f"/api/v1/projects/{project.id}/export/vertical",
            json={"target_aspect": "9:16", "reframe_mode": "smart"},
        )
        assert response.status_code == 202
        data = response.json()
        assert data["format"] == "vertical"
        assert data["status"] == "processing"
        assert data["project_id"] == project.id

    @pytest.mark.asyncio
    async def test_api_export_vertical_project_not_found(self, async_client):
        response = await async_client.post(
            "/api/v1/projects/99999/export/vertical",
            json={"target_aspect": "9:16", "reframe_mode": "smart"},
        )
        assert response.status_code == 404
