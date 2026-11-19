"""Matrix background read receipts stay referenced until they finish."""

import asyncio

import pytest

from gateway.config import PlatformConfig


@pytest.mark.asyncio
async def test_background_read_receipt_task_is_tracked_until_done():
    from plugins.platforms.matrix.adapter import MatrixAdapter

    adapter = MatrixAdapter(PlatformConfig(
        enabled=True, token="syt_test_token",
        extra={"homeserver": "https://matrix.example.org", "user_id": "@bot:example.org"},
    ))
    started, gate = asyncio.Event(), asyncio.Event()

    async def slow_receipt(room_id, event_id):
        started.set()
        await gate.wait()
        return True

    adapter.send_read_receipt = slow_receipt
    adapter._background_read_receipt("!room:example.org", "$event")
    await asyncio.wait_for(started.wait(), timeout=2)

    assert len(adapter._background_tasks) == 1
    task = next(iter(adapter._background_tasks))
    gate.set()
    await asyncio.wait_for(task, timeout=2)
    assert not adapter._background_tasks
