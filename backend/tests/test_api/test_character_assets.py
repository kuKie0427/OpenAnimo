"""CharacterAsset API 路由测试"""
from __future__ import annotations

import pytest


class TestCharacterAssetsRoute:
    @pytest.mark.asyncio
    async def test_list_assets_empty(self, async_client, test_session):
        from tests.factories import create_project
        from app.models.project import Character

        project = await create_project(test_session, title="Asset Test")
        char = Character(name="Test", description="Test", project_id=project.id)
        test_session.add(char)
        await test_session.commit()
        await test_session.refresh(char)

        response = await async_client.get(
            f"/api/v1/characters/{char.id}/assets"
        )
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_get_matrix_default(self, async_client, test_session):
        from tests.factories import create_project
        from app.models.project import Character

        project = await create_project(test_session, title="Matrix Test")
        char = Character(name="Test", description="Test", project_id=project.id)
        test_session.add(char)
        await test_session.commit()
        await test_session.refresh(char)

        response = await async_client.get(
            f"/api/v1/characters/{char.id}/assets/matrix"
        )
        assert response.status_code == 200
        matrix = response.json()
        assert set(matrix.keys()) == {"front", "side", "back", "three_quarter"}
        for angle in matrix:
            assert set(matrix[angle].keys()) == {"smile", "angry", "crying", "surprised"}

    @pytest.mark.asyncio
    async def test_generate_requires_visual_notes(self, async_client, test_session):
        from tests.factories import create_project
        from app.models.project import Character

        project = await create_project(test_session, title="Generate Test")
        char = Character(name="NoNotes", project_id=project.id)
        test_session.add(char)
        await test_session.commit()
        await test_session.refresh(char)

        response = await async_client.post(
            f"/api/v1/characters/{char.id}/assets/generate"
        )
        assert response.status_code == 400
        assert "visual_notes" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_generate_returns_202(self, async_client, test_session):
        from tests.factories import create_project
        from app.models.project import Character

        project = await create_project(test_session, title="Generate Test")
        char = Character(
            name="TestChar", description="A test character",
            visual_notes="Tall, wearing a red cloak",
            project_id=project.id,
        )
        test_session.add(char)
        await test_session.commit()
        await test_session.refresh(char)

        response = await async_client.post(
            f"/api/v1/characters/{char.id}/assets/generate"
        )
        assert response.status_code == 202
        data = response.json()
        assert "generation_id" in data
        assert data["status"] == "started"

    @pytest.mark.asyncio
    async def test_generate_concurrent_returns_409(self, async_client, test_session):
        from tests.factories import create_project
        from app.models.project import Character

        project = await create_project(test_session, title="Concurrent Test")
        char = Character(
            name="ConcurrentChar", description="Test concurrent",
            visual_notes="Tall, wearing a blue hat",
            project_id=project.id,
        )
        test_session.add(char)
        await test_session.commit()
        await test_session.refresh(char)

        response = await async_client.post(
            f"/api/v1/characters/{char.id}/assets/generate"
        )
        assert response.status_code == 202

        response = await async_client.post(
            f"/api/v1/characters/{char.id}/assets/generate"
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_delete_asset_404(self, async_client, test_session):
        from tests.factories import create_project
        from app.models.project import Character

        project = await create_project(test_session, title="Delete Test")
        char = Character(name="Test", description="Test", project_id=project.id)
        test_session.add(char)
        await test_session.commit()
        await test_session.refresh(char)

        response = await async_client.delete(
            f"/api/v1/characters/{char.id}/assets/99999"
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_non_existent_character_404(self, async_client):
        response = await async_client.delete(
            "/api/v1/characters/99999/assets/1"
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_requires_admin_token(
        self, test_session, test_settings, ws_manager
    ):
        from unittest.mock import patch

        from httpx import ASGITransport, AsyncClient

        from tests.factories import create_project
        from app.models.project import Character

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
        char = Character(
            name="AdminTest", description="Test",
            visual_notes="Short, wearing glasses",
            project_id=project.id,
        )
        test_session.add(char)
        await test_session.commit()
        await test_session.refresh(char)

        with patch("app.api.deps.get_settings", return_value=test_settings):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    f"/api/v1/characters/{char.id}/assets/generate"
                )
                assert response.status_code == 403

                response = await client.get(f"/api/v1/characters/{char.id}/assets")
                assert response.status_code == 403

                response = await client.delete(f"/api/v1/characters/{char.id}/assets/1")
                assert response.status_code == 403
