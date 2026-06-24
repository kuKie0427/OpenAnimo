"""Script markdown API 路由测试"""
from __future__ import annotations

import pytest


class TestScriptMarkdownRoute:
    """脚本 Markdown API 路由测试"""

    @pytest.mark.asyncio
    async def test_get_script_empty(self, async_client, test_session):
        """新项目返回空 script_markdown"""
        from tests.factories import create_project

        project = await create_project(test_session, title="Script Test")
        assert project.id is not None

        response = await async_client.get(
            f"/api/v1/projects/{project.id}/script",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["script_markdown"] == ""

    @pytest.mark.asyncio
    async def test_put_script_updates(self, async_client, test_session):
        """PUT 更新 script_markdown，返回更新后的内容"""
        from tests.factories import create_project

        project = await create_project(test_session, title="Update Script Test")
        assert project.id is not None

        # Initial state: empty
        response = await async_client.get(
            f"/api/v1/projects/{project.id}/script",
        )
        assert response.json()["script_markdown"] == ""

        # PUT to update
        new_content = "## Scene 1\n\nSome story text"
        response = await async_client.put(
            f"/api/v1/projects/{project.id}/script",
            json={"script_markdown": new_content},
        )
        assert response.status_code == 200
        assert response.json()["script_markdown"] == new_content

        # Verify GET reflects the update
        response = await async_client.get(
            f"/api/v1/projects/{project.id}/script",
        )
        assert response.json()["script_markdown"] == new_content

    @pytest.mark.asyncio
    async def test_put_script_requires_admin(
        self, test_session, test_settings, ws_manager
    ):
        """无 X-Admin-Token header → 403（admin_token 已设置时）"""
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
                # Without token → 403
                response = await client.put(
                    f"/api/v1/projects/{project.id}/script",
                    json={"script_markdown": "test"},
                )
                assert response.status_code == 403

                # With token → 200
                response = await client.put(
                    f"/api/v1/projects/{project.id}/script",
                    json={"script_markdown": "updated"},
                    headers={"X-Admin-Token": "secret-admin-token"},
                )
                assert response.status_code == 200
                assert response.json()["script_markdown"] == "updated"

    @pytest.mark.asyncio
    async def test_get_script_anchors(self, async_client, test_session):
        """GET /anchors 返回解析后的锚点"""
        from tests.factories import create_project

        project = await create_project(test_session, title="Anchors Test")
        assert project.id is not None

        # Set up script_markdown with anchors
        script = (
            "<!-- shot:1 -->\n"
            "Scene one description\n"
            "\n"
            "<!-- shot:2 -->\n"
            "Scene two description\n"
        )
        response = await async_client.put(
            f"/api/v1/projects/{project.id}/script",
            json={"script_markdown": script},
        )
        assert response.status_code == 200

        # Fetch anchors
        response = await async_client.get(
            f"/api/v1/projects/{project.id}/script/anchors",
        )
        assert response.status_code == 200
        data = response.json()
        assert "anchors" in data
        assert len(data["anchors"]) == 2
        assert data["anchors"][0]["shot_id"] == 1
        assert data["anchors"][1]["shot_id"] == 2

    @pytest.mark.asyncio
    async def test_get_script_project_not_found(self, async_client):
        """不存在的项目 → 404"""
        response = await async_client.get(
            "/api/v1/projects/99999/script",
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_script_anchors_project_not_found(self, async_client):
        """不存在的项目 anchors → 404"""
        response = await async_client.get(
            "/api/v1/projects/99999/script/anchors",
        )
        assert response.status_code == 404
