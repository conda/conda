# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import pytest

from . import SKIPIF_ON_WIN, InteractiveShell

pytestmark = [pytest.mark.integration, SKIPIF_ON_WIN]
PARAMETRIZE_FISH = pytest.mark.parametrize("shell", ["fish"], indirect=True)


@PARAMETRIZE_FISH
def test_shell_available(shell: str) -> None:
    # the fixture does all the work
    pass


@pytest.mark.xfail(reason="fish and pexpect don't seem to work together?")
@PARAMETRIZE_FISH
def test_fish_basic_integration(
    shell_wrapper_integration: tuple[str, str, str], shell: str
) -> None:
    prefix, _, _ = shell_wrapper_integration

    with InteractiveShell(shell) as interactive:
        interactive.sendline("env | sort")
        # We should be seeing environment variable output to terminal with this line, but
        # we aren't.  Haven't experienced this problem yet with any other shell...

        interactive.assert_env_var("CONDA_SHLVL", "0")
        interactive.sendline("conda activate base")
        interactive.assert_env_var("CONDA_SHLVL", "1")
        interactive.sendline(f'conda activate "{prefix}"')
        interactive.assert_env_var("CONDA_SHLVL", "2")
        interactive.assert_env_var("CONDA_PREFIX", prefix, True)
        interactive.sendline("conda deactivate")
        interactive.assert_env_var("CONDA_SHLVL", "1")
        interactive.sendline("conda deactivate")
        interactive.assert_env_var("CONDA_SHLVL", "0")

        interactive.sendline(interactive.print_env_var % "PS1")
        interactive.clear()
        assert "CONDA_PROMPT_MODIFIER" not in str(interactive.p.after)

        interactive.sendline("conda deactivate")
        interactive.assert_env_var("CONDA_SHLVL", "0")
