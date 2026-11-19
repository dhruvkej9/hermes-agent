"""The stop task started by the shutdown signal handler is kept until it finishes."""

import asyncio
import gc
import signal
import weakref


def test_stop_task_survives_garbage_collection(monkeypatch):
    import gateway.run as run_mod
    import gateway.shutdown_forensics as forensics
    from gateway import status

    monkeypatch.setattr(status, "consume_takeover_marker_for_self", lambda: False)
    monkeypatch.setattr(status, "consume_planned_stop_marker_for_self", lambda: False)
    monkeypatch.setattr(forensics, "spawn_async_diagnostic", lambda *a, **k: None)
    waiting, finished = [], []

    class _Runner:
        async def stop(self):
            fut = asyncio.get_running_loop().create_future()  # held only by this task
            waiting.append(weakref.ref(fut))
            await fut
            finished.append(True)

    async def scenario():
        handler = run_mod._start_gateway_make_shutdown_signal_handler(_Runner(), [False])
        handler(signal.SIGTERM)
        await asyncio.sleep(0)
        gc.collect()  # the loop holds tasks only weakly
        fut = waiting[0]()
        assert fut is not None, "the stop task was garbage-collected mid-stop"
        fut.set_result(None)
        await asyncio.sleep(0)

    asyncio.run(scenario())
    assert finished == [True]
