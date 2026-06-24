from __future__ import annotations

import asyncio
import json as _json
import logging

import redis.asyncio as redis

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        from app.config import get_settings

        settings = get_settings()
        _redis_client = redis.from_url(settings.redis_url)
    return _redis_client


def get_confirm_event_key(run_id: int) -> str:
    return f"openanimo:confirm:{run_id}"


def get_confirm_channel(run_id: int) -> str:
    return f"openanimo:confirm_channel:{run_id}"


def get_awaiting_payload_key(run_id: int) -> str:
    """Redis 缓存 run 当前 gate 的 awaiting payload，用于 WS 重连补发"""
    return f"openanimo:awaiting:{run_id}"


async def store_awaiting_payload(run_id: int, payload: dict) -> None:
    """记录当前 run 在 gate 等待，附带 run_awaiting_confirm 事件 payload"""
    try:
        r = await get_redis()
        await r.set(get_awaiting_payload_key(run_id), _json.dumps(payload), ex=7200)
    except Exception:  # noqa: BLE001 - redis unreachable is non-fatal for orchestration flow
        logger.exception("store_awaiting_payload failed run_id=%s", run_id)


async def clear_awaiting_payload(run_id: int) -> None:
    try:
        r = await get_redis()
        await r.delete(get_awaiting_payload_key(run_id))
    except Exception:  # noqa: BLE001
        logger.exception("clear_awaiting_payload failed run_id=%s", run_id)


async def get_awaiting_payload(run_id: int) -> dict | None:
    try:
        r = await get_redis()
        raw = await r.get(get_awaiting_payload_key(run_id))
    except Exception:  # noqa: BLE001
        logger.exception("get_awaiting_payload failed run_id=%s", run_id)
        return None
    if not raw:
        return None
    try:
        return _json.loads(raw)
    except (_json.JSONDecodeError, TypeError, ValueError):
        return None


async def clear_confirm_event_redis(run_id: int) -> None:
    r = await get_redis()
    await r.delete(get_confirm_event_key(run_id))


async def trigger_confirm_redis(run_id: int) -> bool:
    """通过 Redis 发布 confirm 信号（用于多 worker 共享）"""
    r = await get_redis()
    await r.set(get_confirm_event_key(run_id), "1", ex=3600)
    await r.publish(get_confirm_channel(run_id), "confirm")
    return True


async def wait_for_confirm_redis(run_id: int, timeout: int = 1800) -> bool:
    """通过 Redis 订阅等待 confirm 信号"""
    r = await get_redis()
    key = get_confirm_event_key(run_id)
    channel = get_confirm_channel(run_id)

    pubsub = r.pubsub()
    await pubsub.subscribe(channel)
    try:
        if await r.get(key):
            await r.delete(key)
            return True

        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                return False

            msg = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=min(1.0, remaining),
            )
            if msg is not None:
                await r.delete(key)
                return True

            if await r.get(key):
                await r.delete(key)
                return True
    finally:
        try:
            await pubsub.unsubscribe(channel)
        finally:
            await pubsub.close()
