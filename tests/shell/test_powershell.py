# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
import os.path
from logging import getLogger

import pytest

from conda import __version__ as CONDA_VERSION

from . import DEV_ARG, HDF5_VERSION, SKIPIF_ON_WIN, InteractiveShell

log = getLogger(__name__)
pytestmark = pytest.mark.integration
PARAMETRIZE_POWERSHELL = pytest.mark.parametrize(
    "shell",
    [pytest.param(("powershell", "pwsh", "pwsh-preview"), id="powershell")],
    indirect=True,
)


@PARAMETRIZE_POWERSHELL
def test_shell_available(shell: str) -> None:
    # the fixture does all the work
    pass


@PARAMETRIZE_POWERSHELL
def test_powershell_basic_integration(
    shell_wrapper_integration: tuple[str, str, str], shell: str
) -> None:
    prefix, charizard, venusaur = shell_wrapper_integration

    with InteractiveShell(shell) as interactive:
        log.debug("## [PowerShell integration] Starting test.")
        interactive.sendline("(Get-Command conda).CommandType")
        interactive.expect_exact("Alias")
        interactive.sendline("(Get-Command conda).Definition")
        interactive.expect_exact("Invoke-Conda")
        interactive.sendline("(Get-Command Invoke-Conda).Definition")

        log.debug("## [PowerShell integration] Activating.")
        interactive.sendline(f'conda activate "{charizard}"')
        interactive.assert_env_var("CONDA_SHLVL", "1")
        PATH = interactive.get_env_var("PATH")
        assert "charizard" in PATH
        interactive.sendline("conda --version")
        interactive.expect_exact(f"conda {CONDA_VERSION}")
        interactive.sendline(f'conda activate "{prefix}"')
        interactive.assert_env_var("CONDA_SHLVL", "2")
        interactive.assert_env_var("CONDA_PREFIX", prefix, True)

        interactive.sendline("conda deactivate")
        PATH = interactive.get_env_var("PATH")
        assert "charizard" in PATH
        interactive.sendline(f'conda activate -stack "{venusaur}"')
        PATH = interactive.get_env_var("PATH")
        assert "venusaur" in PATH
        assert "charizard" in PATH

        log.debug("## [PowerShell integration] Installing.")
        interactive.sendline(f"conda install -yq hdf5={HDF5_VERSION}")
        interactive.expect(
            r"Executing transaction: ...working... done.*\n", timeout=100
        )
        interactive.sendline("$LASTEXITCODE")
        interactive.expect("0")
        # TODO: assert that reactivate worked correctly

        log.debug("## [PowerShell integration] Checking installed version.")
        interactive.sendline("h5stat --version")
        interactive.expect(rf".*h5stat: Version {HDF5_VERSION}.*")

        # conda run integration test
        log.debug("## [PowerShell integration] Checking conda run.")
        interactive.sendline(f"conda run {DEV_ARG} h5stat --version")
        interactive.expect(rf".*h5stat: Version {HDF5_VERSION}.*")

        log.debug("## [PowerShell integration] Deactivating")
        interactive.sendline("conda deactivate")
        interactive.assert_env_var("CONDA_SHLVL", "1")
        interactive.sendline("conda deactivate")
        interactive.assert_env_var("CONDA_SHLVL", "0")
        interactive.sendline("conda deactivate")
        interactive.assert_env_var("CONDA_SHLVL", "0")


@SKIPIF_ON_WIN
@PARAMETRIZE_POWERSHELL
def test_powershell_PATH_management(
    shell_wrapper_integration: tuple[str, str, str], shell: str
) -> None:
    prefix, _, _ = shell_wrapper_integration

    with InteractiveShell(shell) as interactive:
        prefix = os.path.join(prefix, "envs", "test")
        print("## [PowerShell activation PATH management] Starting test.")
        interactive.sendline("(Get-Command conda).CommandType")
        interactive.expect_exact("Alias")
        interactive.sendline("(Get-Command conda).Definition")
        interactive.expect_exact("Invoke-Conda")
        interactive.sendline("(Get-Command Invoke-Conda).Definition")
        interactive.clear()

        interactive.sendline("conda deactivate")
        interactive.sendline("conda deactivate")

        PATH0 = interactive.get_env_var("PATH", "")
        print(f"PATH is {PATH0.split(os.pathsep)}")
        interactive.sendline("(Get-Command conda).CommandType")
        interactive.expect_exact("Alias")
        interactive.sendline(f'conda create -yqp "{prefix}" bzip2')
        interactive.expect(r"Executing transaction: ...working... done.*\n")
