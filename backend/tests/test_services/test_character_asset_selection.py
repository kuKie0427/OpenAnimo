"""CharacterAsset selection tests — select_asset_for_shot nearest-neighbor matching."""

from __future__ import annotations

import pytest


class TestSelectAssetForShot:
    """select_asset_for_shot — exact match / nearest-neighbor / edge cases."""

    @pytest.mark.asyncio
    async def test_exact_match_returns_correct_asset(self, test_session):
        """When an asset with matching angle AND emotion exists, return it."""
        from app.models.character_asset import CharacterAsset
        from app.services.character_asset_service import select_asset_for_shot

        char_id = 42
        asset = CharacterAsset(
            character_id=char_id,
            angle="front",
            emotion="smile",
            image_url="/static/front_smile.png",
        )
        test_session.add(asset)
        await test_session.commit()

        result = await select_asset_for_shot(test_session, char_id, "front", "smile")
        assert result is not None
        assert result.angle == "front"
        assert result.emotion == "smile"
        assert result.image_url == "/static/front_smile.png"
        assert result.character_id == char_id

    @pytest.mark.asyncio
    async def test_nearest_neighbor_fallback(self, test_session):
        """When no exact match, return asset with minimum Manhattan distance.

        ANGLE_ORDER = ("front", "side", "three_quarter", "back")  → indices 0,1,2,3
        EMOTION_ORDER = ("smile", "surprised", "angry", "crying") → indices 0,1,2,3

        Target: angle="front" (idx=0), expression="surprised" (idx=1)
        Assets:
          - (front, smile): idx=(0,0), dist = |0-0| + |1-0| = 1
          - (side, angry):  idx=(1,2), dist = |0-1| + |1-2| = 2
        Should return (front, smile) since distance 1 < 2.
        """
        from app.models.character_asset import CharacterAsset
        from app.services.character_asset_service import select_asset_for_shot

        char_id = 42
        test_session.add_all([
            CharacterAsset(character_id=char_id, angle="front", emotion="smile"),
            CharacterAsset(character_id=char_id, angle="side", emotion="angry"),
        ])
        await test_session.commit()

        result = await select_asset_for_shot(test_session, char_id, "front", "surprised")
        assert result is not None
        assert result.angle == "front"
        assert result.emotion == "smile"

    @pytest.mark.asyncio
    async def test_no_assets_returns_none(self, test_session):
        """When character has no assets, return None."""
        from app.services.character_asset_service import select_asset_for_shot

        result = await select_asset_for_shot(test_session, 999, "front", "smile")
        assert result is None

    @pytest.mark.asyncio
    async def test_angle_is_none_returns_none(self, test_session):
        """When angle parameter is None, return None (fall back to default image)."""
        from app.models.character_asset import CharacterAsset
        from app.services.character_asset_service import select_asset_for_shot

        char_id = 42
        test_session.add(
            CharacterAsset(character_id=char_id, angle="front", emotion="smile")
        )
        await test_session.commit()

        result = await select_asset_for_shot(test_session, char_id, None, "smile")
        assert result is None

    @pytest.mark.asyncio
    async def test_expression_is_none_returns_none(self, test_session):
        """When expression parameter is None, return None (fall back to default image)."""
        from app.models.character_asset import CharacterAsset
        from app.services.character_asset_service import select_asset_for_shot

        char_id = 42
        test_session.add(
            CharacterAsset(character_id=char_id, angle="front", emotion="smile")
        )
        await test_session.commit()

        result = await select_asset_for_shot(test_session, char_id, "front", None)
        assert result is None

    @pytest.mark.asyncio
    async def test_nearest_neighbor_selects_closest_emotion(self, test_session):
        """Multiple assets: nearest neighbor picks the closest emotion.

        EMOTION_ORDER = ("smile", "surprised", "angry", "crying") → indices 0,1,2,3

        Target: angle="front" (idx=0), expression="angry" (idx=2)
        Assets:
          - (front, smile):  idx=(0,0), dist = |0-0| + |2-0| = 2
          - (front, crying): idx=(0,3), dist = |0-0| + |2-3| = 1
        Should return (front, crying) since distance 1 < 2.
        """
        from app.models.character_asset import CharacterAsset
        from app.services.character_asset_service import select_asset_for_shot

        char_id = 42
        test_session.add_all([
            CharacterAsset(character_id=char_id, angle="front", emotion="smile"),
            CharacterAsset(character_id=char_id, angle="front", emotion="crying"),
        ])
        await test_session.commit()

        result = await select_asset_for_shot(test_session, char_id, "front", "angry")
        assert result is not None
        assert result.angle == "front"
        assert result.emotion == "crying"

    @pytest.mark.asyncio
    async def test_nearest_neighbor_selects_closest_angle(self, test_session):
        """Multiple assets: nearest neighbor picks the closest angle.

        ANGLE_ORDER = ("front", "side", "three_quarter", "back") → indices 0,1,2,3

        Target: angle="three_quarter" (idx=2), expression="smile" (idx=0)
        Assets:
          - (front, smile): idx=(0,0), dist = |2-0| + |0-0| = 2
          - (side, smile):  idx=(1,0), dist = |2-1| + |0-0| = 1
        Should return (side, smile) since distance 1 < 2.
        """
        from app.models.character_asset import CharacterAsset
        from app.services.character_asset_service import select_asset_for_shot

        char_id = 42
        test_session.add_all([
            CharacterAsset(character_id=char_id, angle="front", emotion="smile"),
            CharacterAsset(character_id=char_id, angle="side", emotion="smile"),
        ])
        await test_session.commit()

        result = await select_asset_for_shot(
            test_session, char_id, "three_quarter", "smile"
        )
        assert result is not None
        assert result.angle == "side"
        assert result.emotion == "smile"
