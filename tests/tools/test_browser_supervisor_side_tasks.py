"""CDP supervisor fire-and-forget tasks stay referenced until they finish."""

import asyncio

import pytest

from tools.browser_supervisor import CDPSupervisor
from tools.browser_supervisor_dialogs import DIALOG_POLICY_AUTO_DISMISS


@pytest.mark.asyncio
async def test_auto_policy_dialog_response_task_is_tracked_until_done():
    sup = CDPSupervisor("task", "ws://127.0.0.1:9/devtools/browser/x", dialog_policy=DIALOG_POLICY_AUTO_DISMISS)
    started, gate = asyncio.Event(), asyncio.Event()

    async def slow_respond(dialog, *, accept, prompt_text):
        started.set()
        await gate.wait()

    sup._respond_quiet = slow_respond
    sup._admit_dialog(type="alert", message="hi", default_prompt="", session_id="s1", frame_id=None)
    await asyncio.wait_for(started.wait(), timeout=2)

    assert len(sup._side_tasks) == 1
    task = next(iter(sup._side_tasks))
    gate.set()
    await asyncio.wait_for(task, timeout=2)
    assert not sup._side_tasks
