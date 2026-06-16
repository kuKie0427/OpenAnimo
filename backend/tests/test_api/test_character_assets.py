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
