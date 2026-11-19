"""Inbound Weixin messages run as adapter-tracked tasks, so a running handler stays referenced."""

import asyncio
from unittest.mock import Mock

from gateway.config import PlatformConfig
from plugins.platforms.weixin import adapter as weixin
from plugins.platforms.weixin.adapter import WeixinAdapter


def test_polled_message_task_is_tracked_until_done(monkeypatch):
    adapter = WeixinAdapter(PlatformConfig(enabled=True, token="t", extra={"account_id": "acct"}))
    adapter._running = True
    adapter._poll_session = Mock()
    polls = iter([{"ret": 0, "msgs": [{"message_id": 1}]}])

    async def get_updates(*args, **kwargs):
        try:
            return next(polls)
        except StopIteration:
            adapter._running = False
            return {"ret": 0, "msgs": []}

    monkeypatch.setattr(weixin, "_get_updates", get_updates)
    monkeypatch.setattr(weixin, "_load_sync_buf", lambda *a: "")
    monkeypatch.setattr(weixin, "_save_sync_buf", lambda *a: None)

    async def scenario():
        release = asyncio.Event()

        async def process(message):
            await release.wait()

        adapter._process_message_safe = process
        await adapter._poll_loop()
        tracked = [t for t in adapter._background_tasks if not t.done()]
        release.set()
        await asyncio.gather(*tracked)
        return tracked, set(adapter._background_tasks)

    tracked, left = asyncio.run(scenario())
    assert len(tracked) == 1
    assert not left
