"""Project aspect_ratio 字段测试"""
from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestProjectAspectRatio:
    """Project 模型 aspect_ratio 字段测试（不需要数据库）"""

    def test_default_value_is_16_9(self):
        from app.models.project import Project

        proj = Project(title="Test")
        assert proj.aspect_ratio == "16:9"

    def test_valid_value_9_16(self):
        from app.models.project import Project

        proj = Project(title="Test", aspect_ratio="9:16")
        assert proj.aspect_ratio == "9:16"

    def test_valid_value_1_1(self):
        from app.models.project import Project

        proj = Project(title="Test", aspect_ratio="1:1")
        assert proj.aspect_ratio == "1:1"

    def test_valid_value_4_3(self):
        from app.models.project import Project

        proj = Project(title="Test", aspect_ratio="4:3")
        assert proj.aspect_ratio == "4:3"

    def test_invalid_value_raises_validation_error(self):
        from app.models.project import Project

        with pytest.raises(ValidationError):
            Project.model_validate({"title": "Test", "aspect_ratio": "invalid"})
