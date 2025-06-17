# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
import sys
from logging import getLogger
from pathlib import Path
from re import escape
from typing import TYPE_CHECKING

import pytest

from conda import CONDA_PACKAGE_ROOT
from conda import __version__ as CONDA_VERSION
from conda.base.context import context
from conda.common.compat import on_win

from . import activate, deactivate, dev_arg, install

if TYPE_CHECKING:
    from . import Shell

log = getLogger(__name__)
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not on_win, reason="cmd.exe only available on Windows"),
]
PARAMETRIZE_CMD_EXE = pytest.mark.parametrize("shell", ["cmd.exe"], indirect=True)


@PARAMETRIZE_CMD_EXE
def test_shell_available(shell: Shell) -> None:
    # the `shell` fixture does all the work
    pass


@PARAMETRIZE_CMD_EXE
@pytest.mark.parametrize("force_uppercase", [True, False])
def test_envvars_force_uppercase_integration(
    shell: Shell,
    force_uppercase: bool,
    test_envvars_case,
):
    """
    Integration test for envvars_force_uppercase for CMD.exe shell.

    Regression test for: https://github.com/conda/conda/issues/14934
    Fixed in: https://github.com/conda/conda/pull/14942
    """
    test_envvars_case(shell, force_uppercase)


@PARAMETRIZE_CMD_EXE
def test_cmd_exe_basic_integration(
    shell_wrapper_integration: tuple[str, str, str],
    shell: Shell,
    test_recipes_channel: Path,
) -> None:
    prefix, charizard, _ = shell_wrapper_integration
    conda_bat = str(Path(CONDA_PACKAGE_ROOT, "shell", "condabin", "conda.bat"))

    with shell.interactive() as sh:
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
        sh.assert_env_var("PROMPT", "(charizard).*")
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
        sh.assert_env_var("PROMPT", f"({os.path.basename(prefix)}).*")

        # install local tests/test-recipes/small-executable
        sh.sendline(
            f"conda {install} "
            f"--yes "
            f"--quiet "
            f"--override-channels "
            f"--channel={test_recipes_channel} "
            f"small-executable"
        )
        sh.expect(r"Executing transaction: ...working... done.*\n")
        sh.assert_env_var("errorlevel", "0", True)
        # TODO: assert that reactivate worked correctly

        # see tests/test-recipes/small-executable
        sh.sendline("small")
        sh.expect_exact("Hello!")
        sh.assert_env_var("SMALL_EXE", "small-var-cmd")

        # see tests/test-recipes/small-executable
        sh.sendline(f"conda run {dev_arg} small")
        sh.expect_exact("Hello!")

        sh.sendline(f"conda {deactivate}")
        sh.assert_env_var("CONDA_SHLVL", "1")
        sh.sendline(f"conda {deactivate}")
        sh.assert_env_var("CONDA_SHLVL", "0")
        sh.sendline(f"conda {deactivate}")
        sh.assert_env_var("CONDA_SHLVL", "0")


@PARAMETRIZE_CMD_EXE
def test_cmd_exe_activate_error(
    shell_wrapper_integration: tuple[str, str, str],
    shell: Shell,
) -> None:
    context.dev = True
    with shell.interactive() as sh:
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


@PARAMETRIZE_CMD_EXE
def test_legacy_activate_deactivate_cmd_exe(
    shell_wrapper_integration: tuple[str, str, str],
    shell: Shell,
) -> None:
    prefix, prefix2, prefix3 = shell_wrapper_integration

    with shell.interactive() as sh:
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
        sh.expect_exact(f"conda {CONDA_VERSION}")

        sh.sendline(f'activate.bat --dev "{prefix3}"')
        PATH = sh.get_env_var("PATH")
        assert "venusaur" in PATH

        sh.sendline("deactivate.bat --dev")
        PATH = sh.get_env_var("PATH")
        assert "charizard" in PATH

        sh.sendline("deactivate --dev")
        conda_shlvl = sh.get_env_var("CONDA_SHLVL")
        assert conda_shlvl == "0", conda_shlvl
