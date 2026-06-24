"""Coverage for app.ws.manager edge paths."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.websockets import WebSocketState

from app.ws.manager import ConnectionManager


@pytest.mark.asyncio
async def test_send_event_skips_non_connected_websocket() -> None:
    """If a registered websocket is not in CONNECTED state, send is skipped silently."""
    manager = ConnectionManager()

    ws = MagicMock()
    ws.client_state = WebSocketState.DISCONNECTED
    ws.send_json = AsyncMock()

    # Bypass connect() (which calls accept) and inject directly.
    manager._conns[42].add(ws)

    await manager.send_event(
        42,
        {"type": "run_progress", "data": {"run_id": 1, "progress": 0.5}},
    )

    ws.send_json.assert_not_awaited()


@pytest.mark.asyncio
async def test_send_event_disconnects_websocket_on_send_failure() -> None:
    """If send_json raises, the websocket is removed from the connection set."""
    manager = ConnectionManager()

    ws = MagicMock()
    ws.client_state = WebSocketState.CONNECTED
    ws.send_json = AsyncMock(side_effect=RuntimeError("transport gone"))

    manager._conns[7].add(ws)

    await manager.send_event(
        7,
        {"type": "run_progress", "data": {"run_id": 9, "progress": 0.0}},
    )

    ws.send_json.assert_awaited_once()
    # The exception path should have evicted the broken socket.
    assert 7 not in manager._conns


@pytest.mark.asyncio
async def test_send_event_validates_unknown_type_passes_through() -> None:
    """Events whose type is not in _EVENT_DATA_MODELS should still be sent (no extra validation)."""
    manager = ConnectionManager()

    ws = MagicMock()
    ws.client_state = WebSocketState.CONNECTED
    ws.send_json = AsyncMock()

    manager._conns[99].add(ws)

    # 'pong' is in the WsEventType literal but not in _EVENT_DATA_MODELS,
    # so it skips data validation and is sent as-is.
    await manager.send_event(99, {"type": "pong", "data": {"foo": "bar"}})

    ws.send_json.assert_awaited_once()
    payload = ws.send_json.await_args.args[0]
    assert payload["type"] == "pong"
    assert payload["data"] == {"foo": "bar"}


@pytest.mark.asyncio
async def test_disconnect_removes_empty_project_bucket() -> None:
    """When the last websocket for a project disconnects, the bucket is removed."""
    manager = ConnectionManager()

    ws = MagicMock()
    manager._conns[5].add(ws)

    await manager.disconnect(5, ws)

    assert 5 not in manager._conns


@pytest.mark.asyncio
async def test_disconnect_is_noop_for_unknown_project() -> None:
    """Disconnecting a websocket for a project that's never been registered is a no-op."""
    manager = ConnectionManager()
    ws = MagicMock()

    await manager.disconnect(404, ws)  # should not raise

    assert 404 not in manager._conns
