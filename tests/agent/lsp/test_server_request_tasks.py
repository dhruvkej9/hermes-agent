"""Server-to-client LSP requests run as tasks the client keeps until they finish."""

import asyncio

import pytest

from agent.lsp.client import LSPClient


@pytest.mark.asyncio
async def test_server_request_task_is_held_until_it_finishes(tmp_path):
    client = LSPClient(server_id="mock", workspace_root=str(tmp_path), command=["true"])
    gate = asyncio.Event()
    handled = []

    async def handler(key, msg):
        await gate.wait()
        handled.append(key)

    client._dispatch_request = handler
    client._dispatch({"jsonrpc": "2.0", "id": 7, "method": "workspace/configuration", "params": {}})

    (task,) = client._request_tasks  # the loop alone holds tasks only weakly
    gate.set()
    await task
    assert handled and not client._request_tasks
