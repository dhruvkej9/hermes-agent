"""Process watchers armed after a turn run as tasks the gateway keeps until they finish."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from gateway.run import GatewayRunner
from tools.process_registry import process_registry


@pytest.mark.asyncio
async def test_post_turn_process_watcher_task_is_held_until_done(monkeypatch):
    runner = object.__new__(GatewayRunner)
    runner.hooks = SimpleNamespace(emit=AsyncMock())
    runner._drain_watch_notifications = AsyncMock()
    gate = asyncio.Event()
    seen = []

    async def watch(watcher):
        seen.append(watcher)
        await gate.wait()

    runner._run_process_watcher = watch
    monkeypatch.setattr(process_registry, "pending_watchers", [{"session_id": "proc_1"}])

    await runner._hmwa_post_turn_hooks({}, {}, "done")
    await asyncio.sleep(0)

    assert seen == [{"session_id": "proc_1"}]
    (task,) = runner._background_tasks  # the loop alone holds tasks only weakly
    gate.set()
    await task
    await asyncio.sleep(0)
    assert not runner._background_tasks
