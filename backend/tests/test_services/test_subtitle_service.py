"""测试字幕服务"""
from __future__ import annotations

from unittest.mock import MagicMock

from app.services.subtitle_service import (
    _format_timestamp,
    build_srt,
)


class TestFormatTimestamp:
    """测试 _format_timestamp 时间戳格式化"""

    def test_zero_seconds(self):
        assert _format_timestamp(0.0) == "00:00:00,000"

    def test_normal_seconds(self):
        assert _format_timestamp(3.5) == "00:00:03,500"

    def test_hour_overflow(self):
        """3661.5s = 1h 1m 1s 500ms"""
        assert _format_timestamp(3661.5) == "01:01:01,500"

    def test_milliseconds(self):
        assert _format_timestamp(1.500) == "00:00:01,500"
        assert _format_timestamp(1.250) == "00:00:01,250"
        assert _format_timestamp(1.125) == "00:00:01,125"


class TestBuildSrt:
    """测试 build_srt SRT 生成"""

    def _make_shot(
        self,
        order: int,
        dialogue: str | None,
        approved_dialogue: str | None = None,
        duration: float | None = None,
    ):
        """创建 mock Shot 对象（只设置 build_srt 需要的字段）"""
        shot = MagicMock()
        shot.order = order
        shot.dialogue = dialogue
        shot.approved_dialogue = (
            approved_dialogue if approved_dialogue is not None else dialogue
        )
        shot.duration = duration
        return shot

    def test_empty_list_returns_empty(self):
        """空列表返回空字符串"""
        assert build_srt([]) == ""

    def test_single_shot(self):
        """单条字幕"""
        shots = [self._make_shot(1, "你好", duration=3.0)]
        result = build_srt(shots)
        expected = "1\r\n00:00:00,000 --> 00:00:03,000\r\n你好\r\n"
        assert result == expected

    def test_multiple_shots_sequential_timestamps(self):
        """多条字幕，时间戳顺序累加"""
        shots = [
            self._make_shot(1, "第一句", duration=3.0),
            self._make_shot(2, "第二句", duration=2.0),
            self._make_shot(3, "第三句", duration=4.0),
        ]
        result = build_srt(shots)
        assert "00:00:00,000 --> 00:00:03,000" in result
        assert "00:00:03,000 --> 00:00:05,000" in result
        assert "00:00:05,000 --> 00:00:09,000" in result

    def test_duration_fallback_to_5(self):
        """duration 为 None 时使用 5.0 秒 fallback"""
        shots = [self._make_shot(1, "测试", duration=None)]
        result = build_srt(shots)
        assert "00:00:00,000 --> 00:00:05,000" in result

    def test_skip_empty_dialogue(self):
        """空 dialogue 或无 approved_dialogue 的 shot 被跳过，不占用时间轴"""
        shots = [
            self._make_shot(1, "第一句", approved_dialogue="第一句-审批", duration=3.0),
            self._make_shot(2, "", approved_dialogue="", duration=3.0),
            self._make_shot(3, "第三句", approved_dialogue="第三句-审批", duration=3.0),
        ]
        result = build_srt(shots)
        # Only 2 subtitle entries (shot 2 has empty dialogue, skipped)
        entry_count = result.count("\r\n\r\n") + 1
        assert entry_count == 2
        # Shot 2 skipped, shot 3 starts at same time as if shot 2 didn't exist
        assert "00:00:03,000" in result

    def test_order_sorting(self):
        """按 order 字段排序"""
        shots = [
            self._make_shot(3, "第三", duration=2.0),
            self._make_shot(1, "第一", duration=2.0),
            self._make_shot(2, "第二", duration=2.0),
        ]
        result = build_srt(shots)
        first_idx = result.index("第一")
        second_idx = result.index("第二")
        third_idx = result.index("第三")
        assert first_idx < second_idx < third_idx

    def test_include_unapproved_uses_dialogue(self):
        """include_unapproved=True 时使用 shot.dialogue 而不是 approved_dialogue"""
        shots = [
            self._make_shot(1, "原始对话", approved_dialogue="审批对话", duration=3.0)
        ]
        result_approved = build_srt(shots, include_unapproved=False)
        assert "审批对话" in result_approved
        assert "原始对话" not in result_approved

        result_raw = build_srt(shots, include_unapproved=True)
        assert "原始对话" in result_raw
        assert "审批对话" not in result_raw

    def test_approved_dialogue_is_default(self):
        """默认使用 approved_dialogue（include_unapproved=False）"""
        shots = [
            self._make_shot(1, "原始", approved_dialogue="审批版", duration=3.0)
        ]
        result = build_srt(shots)
        assert "审批版" in result
        assert "原始" not in result

    def test_crlf_line_endings(self):
        """SRT 文件使用 CRLF 换行"""
        shots = [self._make_shot(1, "测试", duration=3.0)]
        result = build_srt(shots)
        assert "\r\n" in result
        assert not result.startswith("\n")

    def test_trailing_newline(self):
        """SRT 输出以 CRLF 结尾"""
        shots = [self._make_shot(1, "测试", duration=3.0)]
        result = build_srt(shots)
        assert result.endswith("\r\n")
