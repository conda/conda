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

    with InteractiveShell("cmd.exe") as sh:
        sh.assert_env_var("_CE_CONDA", "conda")
        sh.assert_env_var("_CE_M", "-m")
        sh.assert_env_var("CONDA_EXE", escape(sys.executable))

        # We use 'PowerShell' here because 'where conda' returns all of them and
        # shell.expect_exact does not do what you would think it does given its name.
        sh.sendline('powershell -NoProfile -c "(Get-Command conda).Source"')
        sh.expect_exact(conda_bat)

        sh.sendline("chcp")
        sh.clear()

        PATH0 = sh.get_env_var("PATH", "").split(os.pathsep)
        log.debug(f"{PATH0=}")
        sh.sendline(f'conda {activate} "{charizard}"')

        sh.sendline("chcp")
        sh.clear()
        sh.assert_env_var("CONDA_SHLVL", "1")

        PATH1 = sh.get_env_var("PATH", "").split(os.pathsep)
        log.debug(f"{PATH1=}")
        sh.sendline('powershell -NoProfile -c "(Get-Command conda).Source"')
        sh.expect_exact(conda_bat)

        sh.assert_env_var("_CE_CONDA", "conda")
        sh.assert_env_var("_CE_M", "-m")
        sh.assert_env_var("CONDA_EXE", escape(sys.executable))
        sh.assert_env_var("CONDA_PREFIX", charizard, True)
        PATH2 = sh.get_env_var("PATH", "").split(os.pathsep)
        log.debug(f"{PATH2=}")

        sh.sendline('powershell -NoProfile -c "(Get-Command conda -All).Source"')
        sh.expect_exact(conda_bat)

        sh.sendline(f'conda {activate} "{prefix}"')
        sh.assert_env_var("_CE_CONDA", "conda")
        sh.assert_env_var("_CE_M", "-m")
        sh.assert_env_var("CONDA_EXE", escape(sys.executable))
        sh.assert_env_var("CONDA_SHLVL", "2")
        sh.assert_env_var("CONDA_PREFIX", prefix, True)

        # TODO: Make a dummy package and release it (somewhere?)
        #       should be a relatively light package, but also
        #       one that has activate.d or deactivate.d scripts.
        #       More imporant than size or script though, it must
        #       not require an old or incompatible version of any
        #       library critical to the correct functioning of
        #       Python (e.g. OpenSSL).
        sh.sendline(f"conda install --yes --quiet hdf5={HDF5_VERSION}")
        sh.expect(r"Executing transaction: ...working... done.*\n", timeout=100)
        sh.assert_env_var("errorlevel", "0", True)
        # TODO: assert that reactivate worked correctly

        sh.sendline("h5stat --version")
        sh.expect(rf".*h5stat: Version {HDF5_VERSION}.*")

        # conda run integration test
        sh.sendline(f"conda run {dev_arg} h5stat --version")
        sh.expect(rf".*h5stat: Version {HDF5_VERSION}.*")

        sh.sendline(f"conda {deactivate}")
        sh.assert_env_var("CONDA_SHLVL", "1")
        sh.sendline(f"conda {deactivate}")
        sh.assert_env_var("CONDA_SHLVL", "0")
        sh.sendline(f"conda {deactivate}")
        sh.assert_env_var("CONDA_SHLVL", "0")


@pytest.mark.skipif(not which("cmd.exe"), reason="cmd.exe not installed")
def test_cmd_exe_activate_error(shell_wrapper_integration: tuple[str, str, str]):
    context.dev = True
    with InteractiveShell("cmd.exe") as sh:
        sh.sendline("set")
        sh.expect(".*")
        sh.sendline(f"conda {activate} environment-not-found-doesnt-exist")
        sh.expect(
            "Could not find conda environment: environment-not-found-doesnt-exist"
        )
        sh.expect(".*")
        sh.assert_env_var("errorlevel", "1")

        sh.sendline("conda activate -h blah blah")
        sh.expect("usage: conda activate")


@pytest.mark.skipif(not which("cmd.exe"), reason="cmd.exe not installed")
def test_legacy_activate_deactivate_cmd_exe(
    shell_wrapper_integration: tuple[str, str, str],
):
    prefix, prefix2, prefix3 = shell_wrapper_integration

    with InteractiveShell("cmd.exe") as sh:
        sh.sendline("echo off")

        conda__ce_conda = sh.get_env_var("_CE_CONDA")
        assert conda__ce_conda == "conda"

        PATH = f"{CONDA_PACKAGE_ROOT}\\shell\\Scripts;%PATH%"

        sh.sendline("SET PATH=" + PATH)

        sh.sendline(f'activate --dev "{prefix2}"')
        sh.clear()

        conda_shlvl = sh.get_env_var("CONDA_SHLVL")
        assert conda_shlvl == "1", conda_shlvl

        PATH = sh.get_env_var("PATH")
        assert "charizard" in PATH

        conda__ce_conda = sh.get_env_var("_CE_CONDA")
        assert conda__ce_conda == "conda"

        sh.sendline("conda --version")
        sh.expect_exact("conda " + conda_version)

        sh.sendline(f'activate.bat --dev "{prefix3}"')
        PATH = sh.get_env_var("PATH")
        assert "venusaur" in PATH

        sh.sendline("deactivate.bat --dev")
        PATH = sh.get_env_var("PATH")
        assert "charizard" in PATH

        sh.sendline("deactivate --dev")
        conda_shlvl = sh.get_env_var("CONDA_SHLVL")
        assert conda_shlvl == "0", conda_shlvl
