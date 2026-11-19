"""`>&` / `<&` / `&>` redirections are not background separators in the lifecycle guard walk."""

from __future__ import annotations

from cron import lifecycle_guard


def test_sourcing_rc_file_with_fd_redirect_is_not_blocked(tmp_path):
    # The stock Ubuntu ~/.bashrc line; `/dev/null` is a redirect target, not a script.
    rc = tmp_path / "bashrc"
    rc.write_text("if [ -x /usr/bin/tput ] && tput setaf 1 >&/dev/null; then\n  color=yes\nfi\n")

    assert lifecycle_guard.scan_gateway_lifecycle(f"source {rc}") == (False, None)
    assert lifecycle_guard.scan_gateway_lifecycle(f"bash -c 'source {rc} 2>/dev/null; echo hi'") == (False, None)


def test_script_run_with_fd_redirect_is_still_scanned(tmp_path):
    script = tmp_path / "restart.sh"
    script.write_text("hermes gateway restart\n")

    for command in (f"bash {script} >&/dev/null", f"bash {script} 2>&1", f"bash {script} &>/dev/null"):
        assert lifecycle_guard.scan_gateway_lifecycle(command)[0] is True, command
