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

    @pytest.mark.asyncio
    async def test_api_export_vertical_requires_admin(
        self, test_session, test_settings, ws_manager
    ):
        from unittest.mock import patch

        from httpx import ASGITransport, AsyncClient

        from tests.factories import create_project

        from app.api.deps import get_db_session, get_ws_manager
        from app.main import create_app

        test_settings.admin_token = "secret-admin-token"
        app = create_app()

        async def override_get_session():
            yield test_session

        async def override_get_ws():
            return ws_manager

        app.dependency_overrides[get_db_session] = override_get_session
        app.dependency_overrides[get_ws_manager] = override_get_ws

        project = await create_project(test_session, title="Admin Auth Test")
        assert project.id is not None

        with patch("app.api.deps.get_settings", return_value=test_settings):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    f"/api/v1/projects/{project.id}/export/vertical",
                    json={"target_aspect": "9:16", "reframe_mode": "smart"},
                )
                assert response.status_code == 403

                response = await client.post(
                    f"/api/v1/projects/{project.id}/export/vertical",
                    json={"target_aspect": "9:16", "reframe_mode": "smart"},
                    headers={"X-Admin-Token": "secret-admin-token"},
                )
                assert response.status_code == 202


@pytest.mark.skip(reason="Requires FFmpeg on PATH + real video file (full end-to-end)")
class TestExportVerticalIntegration:
    @pytest.mark.asyncio
    async def test_full_vertical_export_pipeline(self, test_session, tmp_path):
        import asyncio

        from tests.factories import create_project

        from app.services.export_service import ExportService

        project = await create_project(test_session, title="Integration Test")
        assert project.id is not None

        src = tmp_path / "src.mp4"
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=1920x1080:d=3",
            "-c:v",
            "libx264",
            "-t",
            "3",
            str(src),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.communicate()
        assert proc.returncode == 0, "Failed to create test source video"

        out = tmp_path / "out.mp4"
        service = ExportService()
        await service.export_vertical_video(
            video_url=str(src),
            target_aspect="9:16",
            reframe_mode="smart",
        )
        assert out.exists()

