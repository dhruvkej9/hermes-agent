"""The TimeoutStopSec check reads the manager that has the unit, not the 90s default of one that doesn't."""

import subprocess

from gateway import shutdown_forensics


def _systemctl(user_out, system_out):
    def run(cmd, **_):
        return subprocess.CompletedProcess(cmd, 0, stdout=user_out if "--user" in cmd else system_out, stderr="")
    return run


def test_system_unit_value_wins_over_user_manager_default(monkeypatch):
    # A system unit asked via --user: systemd answers "not-found" with its 90s default.
    monkeypatch.setattr(shutdown_forensics.subprocess, "run", _systemctl(
        "LoadState=not-found\nTimeoutStopUSec=1min 30s\n", "LoadState=loaded\nTimeoutStopUSec=3min 30s\n"))

    assert shutdown_forensics._systemd_timeout_stop_us("hermes-gateway.service") == 210_000_000


def test_loaded_user_unit_is_read_first(monkeypatch):
    monkeypatch.setattr(shutdown_forensics.subprocess, "run", _systemctl(
        "LoadState=loaded\nTimeoutStopUSec=4min\n", "LoadState=not-found\nTimeoutStopUSec=1min 30s\n"))

    assert shutdown_forensics._systemd_timeout_stop_us("hermes-gateway.service") == 240_000_000
