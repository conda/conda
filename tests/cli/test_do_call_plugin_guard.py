# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Verify that do_call() skips plugin hooks when the plugin manager is not loaded.

This guard is effective when combined with lazy subcommand parser loading
(A2/A3, #15868), which allows commands like `conda run` to reach do_call()
without triggering plugin discovery.
"""

from __future__ import annotations

from argparse import Namespace

import pytest

from conda.cli.conda_argparse import do_call
from conda.plugins.manager import get_plugin_manager


@pytest.fixture()
def _clear_plugin_manager_cache():
    """Clear get_plugin_manager's LRU cache so do_call sees an unloaded state."""
    get_plugin_manager.cache_clear()
    yield
    get_plugin_manager.cache_clear()


@pytest.mark.usefixtures("_clear_plugin_manager_cache")
def test_plugin_hooks_skipped_when_manager_not_loaded() -> None:
    """When the plugin manager has not been loaded, do_call should not trigger it."""
    assert get_plugin_manager.cache_info().currsize == 0

    executed = []

    def fake_execute(args, parser):
        executed.append(True)
        return 0

    # Patch a minimal args.func to point at our fake module
    import types

    fake_module = types.ModuleType("conda.cli.main_fake")
    fake_module.execute = fake_execute
    import sys

    sys.modules["conda.cli.main_fake"] = fake_module
    try:
        args = Namespace(func="conda.cli.main_fake.execute")
        result = do_call(args, parser=None)
        assert result == 0
        assert executed == [True]
        # The plugin manager should still not be loaded
        assert get_plugin_manager.cache_info().currsize == 0
    finally:
        del sys.modules["conda.cli.main_fake"]
