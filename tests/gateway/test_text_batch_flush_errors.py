"""A failed text-batch dispatch is reported to the user, not left as an unretrieved task error."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from gateway.config import Platform, PlatformConfig
from gateway.platforms.base import SessionSource
from gateway.platforms.event import MessageEvent


def _adapter():
    from plugins.platforms.discord.adapter import DiscordAdapter

    adapter = object.__new__(DiscordAdapter)
    adapter._platform = adapter.platform = Platform.DISCORD
    adapter.config = PlatformConfig(enabled=True, token="test-token")
    adapter._pending_text_batches = {}
    adapter._pending_text_batch_tasks = {}
    adapter._text_batch_delay_seconds = adapter._text_batch_split_delay_seconds = 0.01
    adapter.handle_message = AsyncMock(side_effect=RuntimeError("admission_conflict"))
    adapter._notify_turn_error = AsyncMock()
    return adapter


@pytest.mark.asyncio
async def test_dispatch_error_notifies_user_and_task_ends_cleanly():
    adapter = _adapter()
    event = MessageEvent(text="hello", source=SessionSource(platform=Platform.DISCORD, chat_id="1", chat_type="dm"))

    adapter._enqueue_text_event(event)
    task = next(iter(adapter._pending_text_batch_tasks.values()))
    await asyncio.wait_for(task, 2)

    assert task.exception() is None
    adapter._notify_turn_error.assert_awaited_once()
    assert adapter._notify_turn_error.await_args.args[0].text == "hello"
    assert adapter._pending_text_batch_tasks == {}
