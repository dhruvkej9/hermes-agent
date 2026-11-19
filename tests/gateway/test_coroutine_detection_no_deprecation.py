"""Sync-or-async dispatch must not use asyncio.iscoroutinefunction (deprecated in Python 3.14)."""

import asyncio
import warnings

from gateway.platforms.api_server import _call_verifier
from hermes_cli.plugin_host_profiles import _as_method


async def _double(value):
    return value * 2


def test_async_callables_are_detected_without_deprecation_warning():
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        assert asyncio.run(_call_verifier(_double, 3)) == 6
        assert asyncio.run(_as_method(_double)(object(), 4)) == 8
