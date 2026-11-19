"""One planned stop logs one shutdown context and spawns one diagnostic."""

import logging
import signal


def _handler(monkeypatch, planned_stop_markers):
    import gateway.run as run_mod
    import gateway.shutdown_forensics as forensics
    from gateway import status

    markers = iter(planned_stop_markers)
    monkeypatch.setattr(status, "consume_takeover_marker_for_self", lambda: False)
    monkeypatch.setattr(status, "consume_planned_stop_marker_for_self", lambda: next(markers, False))
    diagnostics = []
    monkeypatch.setattr(forensics, "spawn_async_diagnostic", lambda *a, **k: diagnostics.append(a))
    monkeypatch.setattr(run_mod.asyncio, "create_task", lambda coro: coro.close())

    class _Runner:
        async def stop(self):
            return None

    return run_mod._start_gateway_make_shutdown_signal_handler(_Runner(), [False]), diagnostics


def _contexts(caplog):
    return [r.getMessage() for r in caplog.records if r.getMessage().startswith("Shutdown context:")]


def test_marker_then_sigterm_logs_one_context_and_one_diagnostic(monkeypatch, caplog):
    handler, diagnostics = _handler(monkeypatch, [True])
    with caplog.at_level(logging.INFO):
        handler(None)  # planned-stop watcher
        handler(signal.SIGTERM)  # the CLI's own SIGTERM right after

    assert len(_contexts(caplog)) == 1
    assert len(diagnostics) == 1
    assert caplog.text.count("as a planned gateway stop") == 2  # both still take the planned path


def test_single_sigterm_still_logs_its_context(monkeypatch, caplog):
    handler, diagnostics = _handler(monkeypatch, [])
    with caplog.at_level(logging.INFO):
        handler(signal.SIGTERM)
    contexts = _contexts(caplog)
    assert len(contexts) == 1 and "signal=SIGTERM" in contexts[0]
    assert len(diagnostics) == 1
