# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
from logging import getLogger
from os.path import join
from typing import TYPE_CHECKING

import pytest

from conda import __version__ as CONDA_VERSION
from conda.common.compat import on_win

from . import Shell, dev_arg, install

if TYPE_CHECKING:
    from pathlib import Path

log = getLogger(__name__)
pytestmark = pytest.mark.integration
PARAMETRIZE_POWERSHELL = pytest.mark.parametrize(
    "shell",
    [
        pytest.param(
            ("powershell", "pwsh", "pwsh-preview"),
            id="powershell",
        ),
        *(
            pytest.param(
                Shell(("powershell", "pwsh"), path=path),
                id=str(path),
            )
            for path in filter(None, os.getenv("PWSHPATH", "").split(";"))
        ),
    ],
    indirect=True,
)


@PARAMETRIZE_POWERSHELL
def test_shell_available(shell: Shell) -> None:
    # the `shell` fixture does all the work
    pass


@PARAMETRIZE_POWERSHELL
@pytest.mark.parametrize("force_uppercase", [True, False])
def test_envvars_force_uppercase_integration(
    shell: Shell,
    force_uppercase: bool,
    test_envvars_case,
):
    """
    Integration test for envvars_force_uppercase for PowerShell.

    Regression test for: https://github.com/conda/conda/issues/14934
    Fixed in: https://github.com/conda/conda/pull/14942
    """
    test_envvars_case(shell, force_uppercase)


@PARAMETRIZE_POWERSHELL
def test_powershell_basic_integration(
    shell_wrapper_integration: tuple[str, str, str],
    shell: Shell,
    test_recipes_channel: Path,
) -> None:
    prefix, charizard, venusaur = shell_wrapper_integration

    with shell.interactive() as sh:
        log.debug("## [PowerShell integration] Starting test.")
        sh.sendline("(Get-Command conda).CommandType")
        sh.expect_exact("Alias")
        sh.sendline("(Get-Command conda).Definition")
        sh.expect_exact("Invoke-Conda")
        sh.sendline("(Get-Command Invoke-Conda).Definition")

        log.debug("## [PowerShell integration] Activating.")
        sh.sendline(f'conda activate "{charizard}"')
        sh.assert_env_var("CONDA_SHLVL", "1")
        PATH = sh.get_env_var("PATH")
        assert "charizard" in PATH
        sh.sendline("conda --version")
        sh.expect_exact(f"conda {CONDA_VERSION}")
        sh.sendline(f'conda activate "{prefix}"')
        sh.assert_env_var("CONDA_SHLVL", "2")
        sh.assert_env_var("CONDA_PREFIX", prefix, True)

        sh.sendline("conda deactivate")
        PATH = sh.get_env_var("PATH")
        assert "charizard" in PATH
        sh.sendline(f'conda activate -stack "{venusaur}"')
        PATH = sh.get_env_var("PATH")
        assert "venusaur" in PATH
        assert "charizard" in PATH

        # install local tests/test-recipes/small-executable
        log.debug("## [PowerShell integration] Installing.")
        sh.sendline(
            f"conda {install} "
            f"--yes "
            f"--quiet "
            f"--override-channels "
            f"--channel={test_recipes_channel} "
            f"small-executable"
        )
        sh.expect(r"Executing transaction: ...working... done.*\n")
        sh.sendline("$LASTEXITCODE")
        sh.expect("0")

        # TODO: reactivate does not set envvars?
        sh.sendline(f'conda activate -stack "{venusaur}"')

        # see tests/test-recipes/small-executable
        log.debug("## [PowerShell integration] Checking installed version.")
        sh.sendline("small")
        sh.expect_exact("Hello!")
        sh.assert_env_var("SMALL_EXE", "small-var-pwsh")

        # see tests/test-recipes/small-executable
        log.debug("## [PowerShell integration] Checking conda run.")
        sh.sendline(f"conda run {dev_arg} small")
        sh.expect_exact("Hello!")

        log.debug("## [PowerShell integration] Deactivating")
        sh.sendline("conda deactivate")
        sh.assert_env_var("CONDA_SHLVL", "1")
        sh.sendline("conda deactivate")
        sh.assert_env_var("CONDA_SHLVL", "0")
        sh.sendline("conda deactivate")
        sh.assert_env_var("CONDA_SHLVL", "0")


@pytest.mark.skipif(on_win, reason="unavailable on Windows")
@PARAMETRIZE_POWERSHELL
def test_powershell_PATH_management(
    shell_wrapper_integration: tuple[str, str, str],
    shell: Shell,
) -> None:
    prefix, _, _ = shell_wrapper_integration

    with shell.interactive() as sh:
        prefix = join(prefix, "envs", "test")
        print("## [PowerShell activation PATH management] Starting test.")
        sh.sendline("(Get-Command conda).CommandType")
        sh.expect_exact("Alias")
        sh.sendline("(Get-Command conda).Definition")
        sh.expect_exact("Invoke-Conda")
        sh.sendline("(Get-Command Invoke-Conda).Definition")
        sh.clear()

        sh.sendline("conda deactivate")
        sh.sendline("conda deactivate")

        PATH0 = sh.get_env_var("PATH", "")
        print(f"PATH is {PATH0.split(os.pathsep)}")
        sh.sendline("(Get-Command conda).CommandType")
        sh.expect_exact("Alias")
        sh.sendline(f'conda create -yqp "{prefix}" bzip2')
        sh.expect(r"Executing transaction: ...working... done.*\n")
