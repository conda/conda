# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda import __version__ as CONDA_VERSION
from conda.common.compat import on_win

if TYPE_CHECKING:
    from . import Shell

pytestmark = [
    pytest.mark.integration,
    # skip on Windows since it's harder to install correctly
    pytest.mark.skipif(on_win, reason="unavailable on Windows"),
]
PARAMETRIZE_XONSH = pytest.mark.parametrize("shell", ["xonsh"], indirect=True)


@PARAMETRIZE_XONSH
def test_shell_available(shell: Shell) -> None:
    # the `shell` fixture does all the work
    pass


@PARAMETRIZE_XONSH
def test_basic_integration(
    shell_wrapper_integration: tuple[str, str, str],
    shell: Shell,
) -> None:
    prefix, _, _ = shell_wrapper_integration
    with shell.interactive() as sh:
        sh.sendline("conda --version")
        sh.expect_exact(f"conda {CONDA_VERSION}")

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


@PARAMETRIZE_XONSH
@pytest.mark.parametrize("force_uppercase", [True, False])
def test_envvars_force_uppercase_integration(
    shell: Shell,
    force_uppercase: bool,
    test_envvars_case,
):
    """
    Integration test for envvars_force_uppercase for XonSH shell.

    Regression test for: https://github.com/conda/conda/issues/14934
    Fixed in: https://github.com/conda/conda/pull/14942
    """
    test_envvars_case(shell, force_uppercase)
