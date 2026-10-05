#!/usr/bin/env python3
"""The external cron worker must not write the double-import RuntimeWarning to stderr.

Regression for the "exited before ownership acknowledgement (exit 0)" alert: the
worker completed correctly, but runpy's "cron.scheduler found in sys.modules after
import of package" warning landed in the captured stderr stream, which the
dispatcher treats as a failed dispatch.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path("/home/ubuntu/.hermes/hermes-agent")


def test_worker_env_suppresses_runtime_warning():
    """The dispatcher must set PYTHONWARNINGS for the worker it spawns."""
    src = (ROOT / "cron" / "scheduler.py").read_text()
    assert "PYTHONWARNINGS" in src, (
        "cron/scheduler.py no longer sets PYTHONWARNINGS for the external worker — "
        "the runpy double-import warning will fail dispatch again"
    )
    assert "ignore::RuntimeWarning" in src, "the warning must be suppressed by category"


def test_worker_runs_clean_with_the_env_applied():
    """End-to-end: `-m cron.scheduler` under this env writes nothing to stderr."""
    env = dict(os.environ)
    env["PYTHONWARNINGS"] = "ignore::RuntimeWarning"
    env["PYTHONPATH"] = str(ROOT)

    proc = subprocess.run(
        [sys.executable, "-W", "error::RuntimeWarning", "-c",
         "import cron.scheduler; print('imported')"],
        capture_output=True, text=True, env=env, cwd=str(ROOT), timeout=180,
    )
    assert "imported" in proc.stdout, f"import failed: {proc.stderr[-400:]}"
    assert "RuntimeWarning" not in proc.stderr, (
        f"warning still reaches stderr: {proc.stderr[-300:]}"
    )


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"PASS {name}")
    print("OK: external cron worker stderr stays clean")
