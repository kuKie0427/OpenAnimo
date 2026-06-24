from __future__ import annotations

import asyncio

import pytest

from app.services.task_manager import TaskManager


@pytest.mark.asyncio
async def test_register_cancels_old_task():
    mgr = TaskManager()
    cancelled = asyncio.Event()

    async def old_coro():
        try:
            await asyncio.sleep(100)
        except asyncio.CancelledError:
            cancelled.set()
            raise

    old_task = asyncio.create_task(old_coro())
    await asyncio.sleep(0)  # let it start
    mgr.register(1, old_task)
    assert mgr.is_running(1)

    async def new_coro():
        await asyncio.sleep(100)

    new_task = asyncio.create_task(new_coro())
    await asyncio.sleep(0)
    mgr.register(1, new_task)

    await asyncio.sleep(0)  # let cancel propagate
    assert cancelled.is_set()
    assert mgr._tasks[1] is new_task
    new_task.cancel()


@pytest.mark.asyncio
async def test_cancel_returns_true_when_running():
    mgr = TaskManager()

    async def coro():
        await asyncio.sleep(100)

    task = asyncio.create_task(coro())
    await asyncio.sleep(0)
    mgr.register(1, task)

    assert mgr.cancel(1) is True
    await asyncio.sleep(0)  # let cancel propagate
    assert task.done() or task.cancelling() > 0


def test_cancel_returns_false_when_no_task():
    mgr = TaskManager()
    assert mgr.cancel(999) is False


def test_cancel_returns_false_when_already_done():
    mgr = TaskManager()

    async def done_coro():
        return 42

    loop = asyncio.new_event_loop()
    task = loop.create_task(done_coro())
    loop.run_until_complete(task)
    mgr._tasks[1] = task

    assert mgr.cancel(1) is False
    loop.close()


def test_is_running_returns_true():
    mgr = TaskManager()

    async def coro():
        await asyncio.sleep(100)

    loop = asyncio.new_event_loop()
    task = loop.create_task(coro())
    loop.run_until_complete(asyncio.sleep(0))
    mgr._tasks[1] = task

    assert mgr.is_running(1) is True
    task.cancel()
    loop.close()


def test_is_running_returns_false_for_missing():
    mgr = TaskManager()
    assert mgr.is_running(999) is False


def test_is_running_returns_false_for_done():
    mgr = TaskManager()

    async def done_coro():
        return 42

    loop = asyncio.new_event_loop()
    task = loop.create_task(done_coro())
    loop.run_until_complete(task)
    mgr._tasks[1] = task

    assert mgr.is_running(1) is False
    loop.close()


def test_remove():
    mgr = TaskManager()
    mgr._tasks[1] = "fake"
    mgr.remove(1)
    assert 1 not in mgr._tasks


def test_remove_nonexistent():
    mgr = TaskManager()
    mgr.remove(999)  # should not raise
