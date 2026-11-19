# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

from conda.base.context import context
from conda.cli.conda_argparse import BUILTIN_COMMANDS

if TYPE_CHECKING:
    from conda.testing import CondaCLIFixture


def test_commands(conda_cli: CondaCLIFixture) -> None:
    stdout, stderr, rc = conda_cli("commands")

    assert rc == 0, f"conda commands failed ({rc}): {stderr}"
    plugin_commands = {
        name
        for subcommand in context.plugin_manager.get_subcommands().values()
        for name in (subcommand.name, *subcommand.aliases)
    }
    assert stdout.splitlines() == sorted(BUILTIN_COMMANDS | plugin_commands)
    assert not stderr
