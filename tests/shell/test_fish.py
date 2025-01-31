# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from shutil import which
from typing import TYPE_CHECKING

import pytest

from conda.common.compat import on_win

from . import InteractiveShell

if TYPE_CHECKING:
    from . import Shell

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(on_win, reason="unavailable on Windows"),
]
PARAMETRIZE_FISH = pytest.mark.parametrize("shell", ["fish"], indirect=True)


@PARAMETRIZE_FISH
def test_shell_available(shell: Shell) -> None:
    # the `shell` fixture does all the work
    pass


@pytest.mark.skipif(not which("fish"), reason="fish not installed")
@pytest.mark.xfail(reason="fish and pexpect don't seem to work together?")
def test_fish_basic_integration(shell_wrapper_integration: tuple[str, str, str]):
    prefix, _, _ = shell_wrapper_integration

    with InteractiveShell("fish") as shell:
        shell.sendline("env | sort")
        # We should be seeing environment variable output to terminal with this line, but
        # we aren't.  Haven't experienced this problem yet with any other shell...

        shell.assert_env_var("CONDA_SHLVL", "0")
        shell.sendline("conda activate base")
        shell.assert_env_var("CONDA_SHLVL", "1")
        shell.sendline(f'conda activate "{prefix}"')
        shell.assert_env_var("CONDA_SHLVL", "2")
        shell.assert_env_var("CONDA_PREFIX", prefix, True)
        shell.sendline("conda deactivate")
        shell.assert_env_var("CONDA_SHLVL", "1")
        shell.sendline("conda deactivate")
        shell.assert_env_var("CONDA_SHLVL", "0")

        shell.sendline(shell.print_env_var % "PS1")
        shell.clear()
        assert "CONDA_PROMPT_MODIFIER" not in str(shell.p.after)

        shell.sendline("conda deactivate")
        shell.assert_env_var("CONDA_SHLVL", "0")
