"""Shot anchor parsing service 测试"""
from __future__ import annotations

from app.services.anchor_service import parse_anchors


class TestParseAnchors:
    """parse_anchors 单元测试"""

    def test_no_anchors(self):
        """不含 shot 标记的文本返回空列表"""
        text = "Some plain text\nwithout any anchors\nhere."
        result = parse_anchors(text)
        assert result == []

    def test_single_anchor(self):
        """基本 <!-- shot:N --> 解析"""
        text = "Some text\n<!-- shot:5 -->\nMore text"
        result = parse_anchors(text)
        assert len(result) == 1
        assert result[0]["shot_id"] == 5
        assert result[0]["paragraph_index"] == 0
        assert result[0]["line_number"] == 2

    def test_multiple_anchors(self):
        """不同段落中的多个锚点"""
        text = (
            "<!-- shot:1 -->\n"
            "First paragraph content\n"
            "\n"
            "<!-- shot:2 -->\n"
            "Second paragraph content\n"
        )
        result = parse_anchors(text)
        assert len(result) == 2
        assert result[0]["shot_id"] == 1
        assert result[0]["paragraph_index"] == 0
        assert result[1]["shot_id"] == 2
        assert result[1]["paragraph_index"] == 1

    def test_anchors_with_whitespace(self):
        """<!--  shot:  42  --> 空白容错"""
        text = "<!--  shot:  42  -->\nContent"
        result = parse_anchors(text)
        assert len(result) == 1
        assert result[0]["shot_id"] == 42

    def test_anchors_in_same_paragraph(self):
        """同一段落中的两个锚点"""
        text = "<!-- shot:10 -->Line one\n<!-- shot:20 -->Line two\nLine three"
        result = parse_anchors(text)
        assert len(result) == 2
        assert result[0]["shot_id"] == 10
        assert result[0]["paragraph_index"] == 0
        assert result[0]["line_number"] == 1
        assert result[1]["shot_id"] == 20
        assert result[1]["paragraph_index"] == 0
        assert result[1]["line_number"] == 2

    def test_empty_string(self):
        """空字符串返回空列表"""
        result = parse_anchors("")
        assert result == []
