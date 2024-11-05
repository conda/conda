# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
import re
import sys
from logging import getLogger
from pathlib import Path

import pytest

from conda import CONDA_PACKAGE_ROOT
from conda import __version__ as CONDA_VERSION
from conda.base.context import context

from . import (
    ACTIVATE_ARGS,
    DEACTIVATE_ARGS,
    DEV_ARG,
    HDF5_VERSION,
    SKIPIF_ON_LINUX,
    SKIPIF_ON_MAC,
    InteractiveShell,
)

log = getLogger(__name__)
pytestmark = [pytest.mark.integration, SKIPIF_ON_LINUX, SKIPIF_ON_MAC]
PARAMETRIZE_CMD_EXE = pytest.mark.parametrize("shell", ["cmd.exe"], indirect=True)


@PARAMETRIZE_CMD_EXE
def test_shell_available(shell: str) -> None:
    # the fixture does all the work
    pass


@PARAMETRIZE_CMD_EXE
def test_cmd_exe_basic_integration(
    shell_wrapper_integration: tuple[str, str, str], shell: str
) -> None:
    prefix, charizard, _ = shell_wrapper_integration
    conda_bat = str(Path(CONDA_PACKAGE_ROOT, "shell", "condabin", "conda.bat"))

    with InteractiveShell(shell) as interactive:
        interactive.assert_env_var("_CE_CONDA", "conda")
        interactive.assert_env_var("_CE_M", "-m")
        interactive.assert_env_var("CONDA_EXE", re.escape(sys.executable))

        # We use 'PowerShell' here because 'where conda' returns all of them and
        # shell.expect_exact does not do what you would think it does given its name.
        interactive.sendline('powershell -NoProfile -c "(Get-Command conda).Source"')
        interactive.expect_exact(conda_bat)

        interactive.sendline("chcp")
        interactive.clear()

        PATH0 = interactive.get_env_var("PATH", "").split(os.pathsep)
        log.debug(f"{PATH0=}")
        interactive.sendline(f'conda {ACTIVATE_ARGS} "{charizard}"')

        interactive.sendline("chcp")
        interactive.clear()
        interactive.assert_env_var("CONDA_SHLVL", "1")

        PATH1 = interactive.get_env_var("PATH", "").split(os.pathsep)
        log.debug(f"{PATH1=}")
        interactive.sendline('powershell -NoProfile -c "(Get-Command conda).Source"')
        interactive.expect_exact(conda_bat)

        interactive.assert_env_var("_CE_CONDA", "conda")
        interactive.assert_env_var("_CE_M", "-m")
        interactive.assert_env_var("CONDA_EXE", re.escape(sys.executable))
        interactive.assert_env_var("CONDA_PREFIX", charizard, True)
        PATH2 = interactive.get_env_var("PATH", "").split(os.pathsep)
        log.debug(f"{PATH2=}")

        interactive.sendline(
            'powershell -NoProfile -c "(Get-Command conda -All).Source"'
        )
        interactive.expect_exact(conda_bat)

        interactive.sendline(f'conda {ACTIVATE_ARGS} "{prefix}"')
        interactive.assert_env_var("_CE_CONDA", "conda")
        interactive.assert_env_var("_CE_M", "-m")
        interactive.assert_env_var("CONDA_EXE", re.escape(sys.executable))
        interactive.assert_env_var("CONDA_SHLVL", "2")
        interactive.assert_env_var("CONDA_PREFIX", prefix, True)

        # TODO: Make a dummy package and release it (somewhere?)
        #       should be a relatively light package, but also
        #       one that has activate.d or deactivate.d scripts.
        #       More imporant than size or script though, it must
        #       not require an old or incompatible version of any
        #       library critical to the correct functioning of
        #       Python (e.g. OpenSSL).
        interactive.sendline(f"conda install --yes --quiet hdf5={HDF5_VERSION}")
        interactive.expect(
            r"Executing transaction: ...working... done.*\n", timeout=100
        )
        interactive.assert_env_var("errorlevel", "0", True)
        # TODO: assert that reactivate worked correctly

        interactive.sendline("h5stat --version")
        interactive.expect(rf".*h5stat: Version {HDF5_VERSION}.*")

        # conda run integration test
        interactive.sendline(f"conda run {DEV_ARG} h5stat --version")
        interactive.expect(rf".*h5stat: Version {HDF5_VERSION}.*")

        interactive.sendline(f"conda {DEACTIVATE_ARGS}")
        interactive.assert_env_var("CONDA_SHLVL", "1")
        interactive.sendline(f"conda {DEACTIVATE_ARGS}")
        interactive.assert_env_var("CONDA_SHLVL", "0")
        interactive.sendline(f"conda {DEACTIVATE_ARGS}")
        interactive.assert_env_var("CONDA_SHLVL", "0")


@PARAMETRIZE_CMD_EXE
def test_cmd_exe_activate_error(
    shell_wrapper_integration: tuple[str, str, str], shell: str
) -> None:
    context.dev = True
    with InteractiveShell(shell) as interactive:
        interactive.sendline("set")
        interactive.expect(".*")
        interactive.sendline(
            f"conda {ACTIVATE_ARGS} environment-not-found-doesnt-exist"
        )
        interactive.expect(
            "Could not find conda environment: environment-not-found-doesnt-exist"
        )
        interactive.expect(".*")
        interactive.assert_env_var("errorlevel", "1")

        interactive.sendline("conda activate -h blah blah")
        interactive.expect("usage: conda activate")


@PARAMETRIZE_CMD_EXE
def test_legacy_activate_deactivate_cmd_exe(
    shell_wrapper_integration: tuple[str, str, str], shell: str
) -> None:
    prefix, prefix2, prefix3 = shell_wrapper_integration

    with InteractiveShell(shell) as interactive:
        interactive.sendline("echo off")

        conda__ce_conda = interactive.get_env_var("_CE_CONDA")
        assert conda__ce_conda == "conda"

        PATH = f"{CONDA_PACKAGE_ROOT}\\shell\\Scripts;%PATH%"

        interactive.sendline("SET PATH=" + PATH)

        interactive.sendline(f'activate --dev "{prefix2}"')
        interactive.clear()

        conda_shlvl = interactive.get_env_var("CONDA_SHLVL")
        assert conda_shlvl == "1", conda_shlvl

        PATH = interactive.get_env_var("PATH")
        assert "charizard" in PATH

        conda__ce_conda = interactive.get_env_var("_CE_CONDA")
        assert conda__ce_conda == "conda"

        interactive.sendline("conda --version")
        interactive.expect_exact(f"conda {CONDA_VERSION}")

        interactive.sendline(f'activate.bat --dev "{prefix3}"')
        PATH = interactive.get_env_var("PATH")
        assert "venusaur" in PATH

        interactive.sendline("deactivate.bat --dev")
        PATH = interactive.get_env_var("PATH")
        assert "charizard" in PATH

        interactive.sendline("deactivate --dev")
        conda_shlvl = interactive.get_env_var("CONDA_SHLVL")
        assert conda_shlvl == "0", conda_shlvl
