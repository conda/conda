# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
import sys
from logging import getLogger
from pathlib import Path
from re import escape
from shutil import which

import pytest

from conda import CONDA_PACKAGE_ROOT
from conda import __version__ as conda_version
from conda.base.context import context

from . import HDF5_VERSION, InteractiveShell, activate, deactivate, dev_arg

log = getLogger(__name__)
pytestmark = pytest.mark.integration


@pytest.mark.skipif(not which("cmd.exe"), reason="cmd.exe not installed")
def test_cmd_exe_basic_integration(shell_wrapper_integration: tuple[str, str, str]):
    prefix, charizard, _ = shell_wrapper_integration
    conda_bat = str(Path(CONDA_PACKAGE_ROOT, "shell", "condabin", "conda.bat"))

    with InteractiveShell("cmd.exe") as shell:
        shell.assert_env_var("_CE_CONDA", "conda")
        shell.assert_env_var("_CE_M", "-m")
        shell.assert_env_var("CONDA_EXE", escape(sys.executable))

        # We use 'PowerShell' here because 'where conda' returns all of them and
        # shell.expect_exact does not do what you would think it does given its name.
        shell.sendline('powershell -NoProfile -c "(Get-Command conda).Source"')
        shell.expect_exact(conda_bat)

        shell.sendline("chcp")
        shell.clear()

        PATH0 = shell.get_env_var("PATH", "").split(os.pathsep)
        log.debug(f"{PATH0=}")
        shell.sendline(f'conda {activate} "{charizard}"')

        shell.sendline("chcp")
        shell.clear()
        shell.assert_env_var("CONDA_SHLVL", "1")

        PATH1 = shell.get_env_var("PATH", "").split(os.pathsep)
        log.debug(f"{PATH1=}")
        shell.sendline('powershell -NoProfile -c "(Get-Command conda).Source"')
        shell.expect_exact(conda_bat)

        shell.assert_env_var("_CE_CONDA", "conda")
        shell.assert_env_var("_CE_M", "-m")
        shell.assert_env_var("CONDA_EXE", escape(sys.executable))
        shell.assert_env_var("CONDA_PREFIX", charizard, True)
        PATH2 = shell.get_env_var("PATH", "").split(os.pathsep)
        log.debug(f"{PATH2=}")

        shell.sendline('powershell -NoProfile -c "(Get-Command conda -All).Source"')
        shell.expect_exact(conda_bat)

        shell.sendline(f'conda {activate} "{prefix}"')
        shell.assert_env_var("_CE_CONDA", "conda")
        shell.assert_env_var("_CE_M", "-m")
        shell.assert_env_var("CONDA_EXE", escape(sys.executable))
        shell.assert_env_var("CONDA_SHLVL", "2")
        shell.assert_env_var("CONDA_PREFIX", prefix, True)

        # TODO: Make a dummy package and release it (somewhere?)
        #       should be a relatively light package, but also
        #       one that has activate.d or deactivate.d scripts.
        #       More imporant than size or script though, it must
        #       not require an old or incompatible version of any
        #       library critical to the correct functioning of
        #       Python (e.g. OpenSSL).
        shell.sendline(f"conda install --yes --quiet hdf5={HDF5_VERSION}")
        shell.expect(r"Executing transaction: ...working... done.*\n", timeout=100)
        shell.assert_env_var("errorlevel", "0", True)
        # TODO: assert that reactivate worked correctly

        shell.sendline("h5stat --version")
        shell.expect(rf".*h5stat: Version {HDF5_VERSION}.*")

        # conda run integration test
        shell.sendline(f"conda run {dev_arg} h5stat --version")
        shell.expect(rf".*h5stat: Version {HDF5_VERSION}.*")

        shell.sendline(f"conda {deactivate}")
        shell.assert_env_var("CONDA_SHLVL", "1")
        shell.sendline(f"conda {deactivate}")
        shell.assert_env_var("CONDA_SHLVL", "0")
        shell.sendline(f"conda {deactivate}")
        shell.assert_env_var("CONDA_SHLVL", "0")


@pytest.mark.skipif(not which("cmd.exe"), reason="cmd.exe not installed")
def test_cmd_exe_activate_error(shell_wrapper_integration: tuple[str, str, str]):
    context.dev = True
    with InteractiveShell("cmd.exe") as shell:
        shell.sendline("set")
        shell.expect(".*")
        shell.sendline(f"conda {activate} environment-not-found-doesnt-exist")
        shell.expect(
            "Could not find conda environment: environment-not-found-doesnt-exist"
        )
        shell.expect(".*")
        shell.assert_env_var("errorlevel", "1")

        shell.sendline("conda activate -h blah blah")
        shell.expect("usage: conda activate")


@pytest.mark.skipif(not which("cmd.exe"), reason="cmd.exe not installed")
def test_legacy_activate_deactivate_cmd_exe(
    shell_wrapper_integration: tuple[str, str, str],
):
    prefix, prefix2, prefix3 = shell_wrapper_integration

    with InteractiveShell("cmd.exe") as shell:
        shell.sendline("echo off")

        conda__ce_conda = shell.get_env_var("_CE_CONDA")
        assert conda__ce_conda == "conda"

        PATH = f"{CONDA_PACKAGE_ROOT}\\shell\\Scripts;%PATH%"

        shell.sendline("SET PATH=" + PATH)

        shell.sendline(f'activate --dev "{prefix2}"')
        shell.clear()

        conda_shlvl = shell.get_env_var("CONDA_SHLVL")
        assert conda_shlvl == "1", conda_shlvl

        PATH = shell.get_env_var("PATH")
        assert "charizard" in PATH

        conda__ce_conda = shell.get_env_var("_CE_CONDA")
        assert conda__ce_conda == "conda"

        shell.sendline("conda --version")
        shell.expect_exact("conda " + conda_version)

        shell.sendline(f'activate.bat --dev "{prefix3}"')
        PATH = shell.get_env_var("PATH")
        assert "venusaur" in PATH

        shell.sendline("deactivate.bat --dev")
        PATH = shell.get_env_var("PATH")
        assert "charizard" in PATH

        shell.sendline("deactivate --dev")
        conda_shlvl = shell.get_env_var("CONDA_SHLVL")
        assert conda_shlvl == "0", conda_shlvl
