# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from conda.plugins import hookimpl
from conda.plugins.hookspec import CondaSpecs
from conda.plugins.manager import CondaPluginManager
from conda.plugins.types import CondaPreCommand


def test_pre_command_priority_and_stable_name_order() -> None:
    calls = []

    class Plugin:
        @hookimpl
        def conda_pre_commands(self):
            yield CondaPreCommand("z-last", lambda _: calls.append("z"), {"install"})
            yield CondaPreCommand("a-first", lambda _: calls.append("a"), {"install"})
            yield CondaPreCommand(
                "prepare", lambda _: calls.append("prepare"), {"install"}, priority=-10
            )
            yield CondaPreCommand(
                "other", lambda _: calls.append("other"), {"remove"}, priority=-20
            )

    manager = CondaPluginManager()
    manager.add_hookspecs(CondaSpecs)
    manager.register(Plugin())
    manager.invoke_pre_commands("install")
    assert calls == ["prepare", "a", "z"]
