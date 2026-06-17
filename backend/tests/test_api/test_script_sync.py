"""Script sync API 路由测试"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_db_session, get_ws_manager
from app.main import create_app
from app.models.project import Shot
from tests.factories import create_project


class TestScriptSyncRoute:
    """脚本同步 API 路由测试"""

    @pytest.mark.asyncio
    async def test_get_sync_map(self, async_client, test_session):
        """GET /sync 返回 shot↔paragraph 映射，包含正确的 shot 元数据"""
        project = await create_project(test_session, title="Sync Map Test")
        assert project.id is not None

        project.script_markdown = "<!-- shot:1 -->\nFirst paragraph text\n\nSecond paragraph"
        test_session.add(project)
        await test_session.commit()

        # 创建 id=1 的 Shot 以匹配锚点
        shot = Shot(
            id=1,
            project_id=project.id,
            order=1,
            description="A test shot description",
            prompt="Test prompt",
        )
        test_session.add(shot)
        await test_session.commit()

        response = await async_client.get(
            f"/api/v1/projects/{project.id}/script/sync",
        )
        assert response.status_code == 200
        data = response.json()
        assert "sync_map" in data
        assert isinstance(data["sync_map"], list)
        assert len(data["sync_map"]) == 1

        entry = data["sync_map"][0]
        assert entry["shot_id"] == 1
        assert entry["paragraph_index"] == 0
        assert entry["shot_order"] == 1
        assert entry["shot_description"] == "A test shot description"
        assert entry["is_synced"] is True

    @pytest.mark.asyncio
    async def test_get_sync_map_empty(self, async_client, test_session):
        """脚本无锚点 → 返回空 sync_map"""
        project = await create_project(test_session, title="Empty Sync Map")
        project.script_markdown = "Just some text\n\nNo anchors here"
        test_session.add(project)
        await test_session.commit()

        response = await async_client.get(
            f"/api/v1/projects/{project.id}/script/sync",
        )
        assert response.status_code == 200
        data = response.json()
        assert "sync_map" in data
        assert data["sync_map"] == []

    @pytest.mark.asyncio
    async def test_sync_paragraph_triggers_replan(self, async_client, test_session):
        """POST /sync/paragraph 替换段落文本并触发后台任务"""
        project = await create_project(test_session, title="Replan Test")
        project.script_markdown = "First paragraph\n\nSecond paragraph\n\nThird paragraph"
        test_session.add(project)
        await test_session.commit()

        async def _mock_start_project_task(project_id, coro):
            coro.close()

        with patch(
            "app.api.v1.routes.script._start_project_task",
            _mock_start_project_task,
        ):
            response = await async_client.post(
                f"/api/v1/projects/{project.id}/script/sync/paragraph",
                json={"paragraph_index": 0, "paragraph_text": "New paragraph text"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "syncing"
            assert data["paragraph_index"] == 0

        # 验证 script_markdown 已更新（在后台任务启动前完成）
        response = await async_client.get(
            f"/api/v1/projects/{project.id}/script",
        )
        assert response.status_code == 200
        updated = response.json()["script_markdown"]
        assert "New paragraph text" in updated
        assert "Second paragraph" in updated
        assert "Third paragraph" in updated

    @pytest.mark.asyncio
    async def test_sync_paragraph_requires_admin(
        self, test_session, test_settings, ws_manager
    ):
        """无 X-Admin-Token header → 403"""
        from tests.factories import create_project

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
                    f"/api/v1/projects/{project.id}/script/sync/paragraph",
                    json={"paragraph_index": 0, "paragraph_text": "New text"},
                )
                assert response.status_code == 403
