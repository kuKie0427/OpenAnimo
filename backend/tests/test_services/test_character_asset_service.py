"""CharacterAsset 服务单元测试"""
from __future__ import annotations

import pytest


class TestCharacterAssetService:
    """generate_matrix / list_assets / get_matrix / delete_asset 测试"""

    @pytest.mark.asyncio
    async def test_generate_matrix_all_succeed(self, test_session, monkeypatch):
        from app.models.project import Character
        from app.services.character_asset_service import generate_matrix

        char = Character(name="Test", description="A test character", project_id=1)
        test_session.add(char)
        await test_session.commit()
        await test_session.refresh(char)

        async def fake_generate(prompt, seed):
            return f"/static/images/{seed}.png"

        async def fake_embedding(url):
            return [0.1] * 512

        monkeypatch.setattr(
            "app.services.character_bible.compute_face_embedding",
            fake_embedding,
        )

        result = await generate_matrix(test_session, char, fake_generate)
        assert result["total"] == 16
        assert result["succeeded"] == 16
        assert result["failed"] == 0
        assert len(result["assets"]) == 16

    @pytest.mark.asyncio
    async def test_generate_matrix_partial_failure(self, test_session, monkeypatch):
        from app.models.project import Character
        from app.services.character_asset_service import generate_matrix

        char = Character(name="Test", description="A test character", project_id=1)
        test_session.add(char)
        await test_session.commit()
        await test_session.refresh(char)

        call_count = 0

        async def fake_generate_fail_some(prompt, seed):
            nonlocal call_count
            call_count += 1
            if call_count == 5:  # Make the 5th call fail
                raise RuntimeError("Image generation failed")
            return f"/static/images/{seed}.png"

        async def fake_embedding(url):
            return [0.1] * 512

        monkeypatch.setattr(
            "app.services.character_bible.compute_face_embedding",
            fake_embedding,
        )

        result = await generate_matrix(test_session, char, fake_generate_fail_some)
        assert result["total"] == 16
        assert result["succeeded"] == 15
        assert result["failed"] == 1
        assert len(result["assets"]) == 15

    @pytest.mark.asyncio
    async def test_list_assets_with_filters(self, test_session):
        from app.models.character_asset import CharacterAsset
        from app.services.character_asset_service import list_assets

        char_id = 1
        test_session.add_all([
            CharacterAsset(character_id=char_id, angle="front", emotion="smile"),
            CharacterAsset(character_id=char_id, angle="front", emotion="angry"),
            CharacterAsset(character_id=char_id, angle="side", emotion="smile"),
        ])
        await test_session.commit()

        # No filter: all 3
        all_assets = await list_assets(test_session, char_id)
        assert len(all_assets) == 3

        # Filter by angle
        front_assets = await list_assets(test_session, char_id, angle="front")
        assert len(front_assets) == 2

        side_assets = await list_assets(test_session, char_id, angle="side")
        assert len(side_assets) == 1

        # Filter by emotion
        smile_assets = await list_assets(test_session, char_id, emotion="smile")
        assert len(smile_assets) == 2

        # Filter by both
        specific = await list_assets(test_session, char_id, angle="front", emotion="smile")
        assert len(specific) == 1

    @pytest.mark.asyncio
    async def test_get_matrix_4x4(self, test_session):
        from app.models.character_asset import CharacterAsset
        from app.services.character_asset_service import get_matrix

        char_id = 1
        test_session.add(CharacterAsset(
            character_id=char_id, angle="front", emotion="smile",
            image_url="/static/front_smile.png", is_approved=True,
        ))
        await test_session.commit()

        matrix = await get_matrix(test_session, char_id)

        # Should have all 4 angles
        assert set(matrix.keys()) == {"front", "side", "back", "three_quarter"}

        # Each angle should have all 4 emotions
        for angle in matrix:
            assert set(matrix[angle].keys()) == {"smile", "angry", "crying", "surprised"}

        # The front→smile cell should have data
        assert matrix["front"]["smile"]["id"] is not None
        assert matrix["front"]["smile"]["image_url"] == "/static/front_smile.png"
        assert matrix["front"]["smile"]["is_approved"] is True

        # Empty cells should have None/False
        assert matrix["front"]["angry"]["id"] is None
        assert matrix["front"]["angry"]["image_url"] is None
        assert matrix["front"]["angry"]["is_approved"] is False

    @pytest.mark.asyncio
    async def test_delete_asset_existing(self, test_session):
        from app.models.character_asset import CharacterAsset
        from app.services.character_asset_service import delete_asset, list_assets

        asset = CharacterAsset(character_id=1, angle="front", emotion="smile")
        test_session.add(asset)
        await test_session.commit()
        await test_session.refresh(asset)
        asset_id = asset.id

        result = await delete_asset(test_session, asset_id)
        assert result is True

        remaining = await list_assets(test_session, 1)
        assert len(remaining) == 0

    @pytest.mark.asyncio
    async def test_delete_asset_not_found(self, test_session):
        from app.services.character_asset_service import delete_asset

        result = await delete_asset(test_session, 99999)
        assert result is False
