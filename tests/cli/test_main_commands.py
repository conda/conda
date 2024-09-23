# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

from conda.base.context import context
from conda.cli.conda_argparse import BUILTIN_COMMANDS

if TYPE_CHECKING:
    from conda.testing import CondaCLIFixture


def test_commands(conda_cli: CondaCLIFixture) -> None:
    stdout, stderr, code = conda_cli("commands")

    assert stdout == "\n".join(
        sorted(
            {
                *BUILTIN_COMMANDS,
                *context.plugin_manager.get_subcommands(),
            }
        )
    )
    assert not stderr
    assert not code
