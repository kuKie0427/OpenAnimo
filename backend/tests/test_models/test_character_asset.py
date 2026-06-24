"""CharacterAsset 模型字段验证测试（不需要数据库）"""
from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestCharacterAssetValidation:
    def _make_asset(self, **overrides):
        from app.models.character_asset import CharacterAsset

        data = {"character_id": 1, "angle": "front", "emotion": "smile", **overrides}
        return CharacterAsset.model_validate(data)

    def test_valid_angle_front(self):
        asset = self._make_asset(angle="front")
        assert asset.angle == "front"

    def test_valid_angle_side(self):
        asset = self._make_asset(angle="side")
        assert asset.angle == "side"

    def test_valid_angle_back(self):
        asset = self._make_asset(angle="back")
        assert asset.angle == "back"

    def test_valid_angle_three_quarter(self):
        asset = self._make_asset(angle="three_quarter")
        assert asset.angle == "three_quarter"

    def test_valid_emotion_smile(self):
        asset = self._make_asset(emotion="smile")
        assert asset.emotion == "smile"

    def test_valid_emotion_angry(self):
        asset = self._make_asset(emotion="angry")
        assert asset.emotion == "angry"

    def test_valid_emotion_crying(self):
        asset = self._make_asset(emotion="crying")
        assert asset.emotion == "crying"

    def test_valid_emotion_surprised(self):
        asset = self._make_asset(emotion="surprised")
        assert asset.emotion == "surprised"

    def test_invalid_angle_raises_validation_error(self):
        with pytest.raises(ValidationError, match="angle must be one of"):
            self._make_asset(angle="invalid_angle")

    def test_invalid_emotion_raises_validation_error(self):
        with pytest.raises(ValidationError, match="emotion must be one of"):
            self._make_asset(emotion="invalid_emotion")

    def test_default_is_approved_false(self):
        asset = self._make_asset()
        assert asset.is_approved is False

    def test_created_at_auto_populated(self):
        asset = self._make_asset()
        assert asset.created_at is not None

    def test_optional_fields_default_to_none(self):
        asset = self._make_asset()
        assert asset.image_url is None
        assert asset.face_embedding is None
        assert asset.prompt is None
        assert asset.seed is None
