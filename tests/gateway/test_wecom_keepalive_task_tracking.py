"""WeCom stream keep-alive sends stay referenced until they finish."""

import asyncio

import pytest

from gateway.config import PlatformConfig
from plugins.platforms.wecom.adapter import WeComAdapter
from plugins.platforms.wecom.streaming import StreamTurn


@pytest.mark.asyncio
async def test_keepalive_send_task_is_tracked_until_done():
    adapter = WeComAdapter(PlatformConfig(enabled=True, extra={"stream_keepalive_enabled": True}))
    started, gate = asyncio.Event(), asyncio.Event()

    async def slow_reply(req_id, stream_id, content, *, finish):
        started.set()
        await gate.wait()

    adapter._send_stream_reply = slow_reply
    turn = StreamTurn("chat", "req")
    turn.accumulated_text = "partial answer"

    adapter._on_keepalive_fire(turn, "turn")
    await asyncio.wait_for(started.wait(), timeout=2)

    assert len(adapter._background_tasks) == 1
    task = next(iter(adapter._background_tasks))
    gate.set()
    await asyncio.wait_for(task, timeout=2)
    assert not adapter._background_tasks
    if turn.keepalive_handle is not None:
        turn.keepalive_handle.cancel()
