# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda.common.compat import on_win

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


@pytest.mark.xfail(reason="fish and pexpect don't seem to work together?")
@PARAMETRIZE_FISH
def test_fish_basic_integration(
    shell_wrapper_integration: tuple[str, str, str],
    shell: Shell,
) -> None:
    prefix, _, _ = shell_wrapper_integration

    with shell.interactive() as sh:
        sh.sendline("env | sort")
        # We should be seeing environment variable output to terminal with this line, but
        # we aren't.  Haven't experienced this problem yet with any other shell...

        sh.assert_env_var("CONDA_SHLVL", "0")
        sh.sendline("conda activate base")
        sh.assert_env_var("CONDA_SHLVL", "1")
        sh.sendline(f'conda activate "{prefix}"')
        sh.assert_env_var("CONDA_SHLVL", "2")
        sh.assert_env_var("CONDA_PREFIX", prefix, True)
        sh.sendline("conda deactivate")
        sh.assert_env_var("CONDA_SHLVL", "1")
        sh.sendline("conda deactivate")
        sh.assert_env_var("CONDA_SHLVL", "0")

        sh.sendline(sh.print_env_var % "PS1")
        sh.clear()
        assert "CONDA_PROMPT_MODIFIER" not in str(sh.p.after)

        sh.sendline("conda deactivate")
        sh.assert_env_var("CONDA_SHLVL", "0")
