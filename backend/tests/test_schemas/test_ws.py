from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.ws import (
    EVENT_DATA_MODELS,
    WsEvent,
    WsEventType,
)


class TestWsSchema:
    """WS Schema 回归测试"""

    def test_all_known_event_types_have_schema(self):
        """确认所有发出的事件类型在 ws.py 中有对应 Pydantic model（或显式标记为 None）"""
        event_types: tuple[str, ...] = WsEventType.__args__  # type: ignore[attr-defined]

        for evt in event_types:
            assert evt in EVENT_DATA_MODELS, (
                f"Event '{evt}' is not in EVENT_DATA_MODELS mapping. "
                f"Add it to EVENT_DATA_MODELS in ws.py"
            )

    def test_event_validation_rejects_invalid_payload(self):
        """Schema 校验拒绝对非法 payload（错误类型而非格式）"""
        with pytest.raises(ValidationError):
            WsEvent(type="invalid_event_type", data={})  # type: ignore[arg-type]

    def test_valid_event_passes_validation(self):
        """合法的 WsEvent 通过校验"""
        event = WsEvent(type="pong", data={})
        assert event.type == "pong"
        assert event.data == {}

    def test_error_event_roundtrip(self):
        """ErrorEvent 可正常构建"""
        event = WsEvent(type="error", data={"code": "TEST_ERR", "message": "test"})
        assert event.type == "error"
        assert event.data["code"] == "TEST_ERR"
