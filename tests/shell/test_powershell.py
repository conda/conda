# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
import platform
from functools import cache
from logging import getLogger
from os.path import join
from shutil import which
from typing import TYPE_CHECKING

import pytest

from conda import __version__ as conda_version
from conda.common.compat import on_win

from . import InteractiveShell, dev_arg, install

if TYPE_CHECKING:
    from pathlib import Path

log = getLogger(__name__)
pytestmark = pytest.mark.integration


@cache
def which_powershell(path: str | None = None) -> tuple[str, str] | None:
    r"""
    Since we don't know whether PowerShell is installed as powershell, pwsh, or pwsh-preview,
    it's helpful to have a utility function that returns the name of the best PowerShell
    executable available, or `None` if there's no PowerShell installed.

    If PowerShell is found, this function returns both the kind of PowerShell install
    found and a path to its main executable.
    E.g.: ('pwsh', r'C:\Program Files\PowerShell\6.0.2\pwsh.exe)
    """
    if on_win:
        posh = which("powershell.exe", path=path)
        if posh:
            return "powershell", posh

    posh = which("pwsh", path=path)
    if posh:
        return "pwsh", posh

    posh = which("pwsh-preview", path=path)
    if posh:
        return "pwsh-preview", posh


@cache
def latest_powershell() -> tuple[str, str] | None:
    if not (path := os.getenv("PWSHPATH")):
        return None
    return which_powershell(path)


parametrize_pwsh = pytest.mark.parametrize(
    "pwsh_name,pwsh_path",
    [
        *([which_powershell()] if which_powershell() else []),
        *([latest_powershell()] if latest_powershell() else []),
    ],
)


@pytest.mark.skipif(
    not which_powershell() or platform.machine() == "arm64",
    reason="PowerShell not installed or not supported on platform",
)
@parametrize_pwsh
def test_powershell_basic_integration(
    shell_wrapper_integration: tuple[str, str, str],
    pwsh_name: str,
    pwsh_path: str,
    test_recipe_channel: Path,
):
    prefix, charizard, venusaur = shell_wrapper_integration

    log.debug(f"## [PowerShell integration] Using {pwsh_path}.")
    with InteractiveShell(pwsh_name, shell_path=pwsh_path) as sh:
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
        sh.expect_exact("conda " + conda_version)
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

        log.debug("## [PowerShell integration] Installing.")
        sh.sendline(
            f"conda {install} "
            f"--yes "
            f"--quiet "
            f"--override-channels "
            f"--channel={test_recipe_channel} "
            f"small-executable"
        )
        sh.expect(r"Executing transaction: ...working... done.*\n", timeout=100)
        sh.sendline("$LASTEXITCODE")
        sh.expect("0")
        # TODO: assert that reactivate worked correctly

        log.debug("## [PowerShell integration] Checking installed version.")
        sh.sendline("small")
        sh.expect_exact("Hello!")

        # conda run integration test
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


@pytest.mark.skipif(
    not which_powershell() or not on_win,
    reason="Windows, PowerShell specific test",
)
@parametrize_pwsh
def test_powershell_PATH_management(
    shell_wrapper_integration: tuple[str, str, str],
    pwsh_name: str,
    pwsh_path: str,
):
    prefix, _, _ = shell_wrapper_integration

    print(f"## [PowerShell activation PATH management] Using {pwsh_path}.")
    with InteractiveShell(pwsh_name, shell_path=pwsh_path) as sh:
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
