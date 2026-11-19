"""A blank or non-numeric per-call `speed` keeps the configured speed instead of failing."""

from __future__ import annotations

import pytest

from tools import tts_tool


@pytest.mark.parametrize("speed", ["", "  ", "fast"])
def test_invalid_call_speed_keeps_configured_speed(speed):
    config, _ = tts_tool._apply_call_overrides({"provider": "edge", "speed": 1.5}, speed)
    assert config["speed"] == 1.5


def test_numeric_call_speed_is_applied_and_clamped():
    assert tts_tool._apply_call_overrides({"provider": "edge"}, "2")[0]["speed"] == 2.0
    assert tts_tool._apply_call_overrides({"provider": "edge"}, 9)[0]["speed"] == 4.0
