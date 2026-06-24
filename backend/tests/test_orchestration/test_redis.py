from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from app.orchestration.redis import (
    get_awaiting_payload_key,
    get_confirm_channel,
    get_confirm_event_key,
    get_redis,
    wait_for_confirm_redis,
)


# ---------------------------------------------------------------------------
# Key helper functions (pure sync, no mocking needed)
# ---------------------------------------------------------------------------


class TestKeyHelpers:
    def test_confirm_event_key(self):
        assert get_confirm_event_key(42) == "openanimo:confirm:42"

    def test_confirm_channel(self):
        assert get_confirm_channel(99) == "openanimo:confirm_channel:99"

    def test_awaiting_payload_key(self):
        assert get_awaiting_payload_key(7) == "openanimo:awaiting:7"


# ---------------------------------------------------------------------------
# get_redis singleton test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_redis_returns_singleton(monkeypatch):
    """get_redis() should reuse one client instance across calls."""
    import app.orchestration.redis as redis_mod

    monkeypatch.setattr(redis_mod, "_redis_client", None)

    created: list[Any] = []

    class _FakeClient:
        async def ping(self):
            return True

    def _from_url(*_a, **_kw):
        c = _FakeClient()
        created.append(c)
        return c

    fake_redis_module = SimpleNamespace(from_url=_from_url, Redis=object)
    monkeypatch.setattr(redis_mod, "redis", fake_redis_module)

    a = await get_redis()
    b = await get_redis()
    assert a is b
    assert len(created) == 1


# ---------------------------------------------------------------------------
# wait_for_confirm_redis timeout test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wait_for_confirm_redis_returns_false_on_timeout(monkeypatch):
    """wait_for_confirm_redis should return False when timeout expires with no confirm."""
    import app.orchestration.redis as redis_mod

    fake_client = _FakeRedisWithPubSub(
        store={},
        pubsub_get_message_returns=None,  # Never receives a message
    )

    async def _get_redis():
        return fake_client

    monkeypatch.setattr(redis_mod, "get_redis", _get_redis)

    result = await wait_for_confirm_redis(1, timeout=0.01)
    assert result is False
    # Verify pubsub was cleaned up
    assert fake_client._pubsub.closed


class _FakeRedisWithPubSub:
    """Minimal async redis stub with configurable pubsub behavior."""

    def __init__(self, store: dict[str, str], pubsub_get_message_returns: Any = None) -> None:
        self.store = store
        self._pubsub_get_message_returns = pubsub_get_message_returns
        self._pubsub: _FakePubSub | None = None  # noqa: SLF001

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def delete(self, key: str) -> int:
        return 1 if self.store.pop(key, None) is not None else 0

    def pubsub(self):
        self._pubsub = _FakePubSub(self._pubsub_get_message_returns)  # noqa: SLF001
        return self._pubsub


class _FakePubSub:
    def __init__(self, get_message_returns: Any = None) -> None:
        self._get_message_returns = get_message_returns
        self._subscribed: set[str] = set()
        self.closed = False

    async def subscribe(self, *channels: str) -> None:
        self._subscribed.update(channels)

    async def unsubscribe(self, *channels: str) -> None:
        self._subscribed.clear()

    async def get_message(self, ignore_subscribe_messages: bool = True, timeout: float = 1.0):
        await asyncio.sleep(0)
        return self._get_message_returns

    async def close(self) -> None:
        self.closed = True
