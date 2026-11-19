"""Inbound QQ messages run as adapter-tracked tasks: kept alive while running, cancelled on disconnect."""

import asyncio

import pytest

from gateway.config import PlatformConfig


@pytest.mark.asyncio
async def test_inbound_message_task_is_tracked_until_done():
    from plugins.platforms.qqbot.adapter import QQAdapter

    adapter = QQAdapter(PlatformConfig(enabled=True, extra={"app_id": "a", "client_secret": "b"}))
    release = asyncio.Event()

    async def on_message(event_type, data):
        await release.wait()

    adapter._on_message = on_message
    adapter._dispatch_payload({"op": 0, "t": "C2C_MESSAGE_CREATE", "s": 1, "d": {"id": "m1"}})

    tracked = [t for t in adapter._background_tasks if not t.done()]
    assert len(tracked) == 1
    release.set()
    await asyncio.wait_for(tracked[0], 2)
    assert tracked[0] not in adapter._background_tasks
