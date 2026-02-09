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
from conda.common.compat import on_linux, on_mac

from . import activate, deactivate, dev_arg, install

if TYPE_CHECKING:
    from . import Shell

log = getLogger(__name__)
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(on_linux, reason="unavailable on Linux"),
    pytest.mark.skipif(on_mac, reason="unavailable on macOS"),
]
PARAMETRIZE_CMD_EXE = pytest.mark.parametrize("shell", ["cmd.exe"], indirect=True)


@PARAMETRIZE_CMD_EXE
def test_shell_available(shell: Shell) -> None:
    # the `shell` fixture does all the work
    pass


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
def test_cmd_exe_activate_error(shell: Shell) -> None:
    context.dev = True
    with shell.interactive() as sh:
        sh.sendline("set")
        sh.expect(".*")
        sh.sendline(f"conda {activate} environment-not-found-doesnt-exist")
        sh.expect(
            "Could not find conda environment: environment-not-found-doesnt-exist"
        )
        sh.expect(".*")
        sh.assert_env_var("errorlevel", "2")

        sh.sendline("conda activate -h blah blah")
        sh.expect("usage: conda activate")


@PARAMETRIZE_CMD_EXE
def test_cmd_exe_activate_invalid_temp(shell: Shell) -> None:
    """Test that activation fails gracefully with an invalid TEMP directory."""
    with shell.interactive() as sh:
        # Set TEMP to invalid path
        sh.sendline("set TEMP=C:\\path\\that\\does\\not\\exist")

        # Try to activate - should fail with TEMP error
        sh.sendline(f"conda {activate} base")
        sh.expect("ERROR: Failed to create temp file")
        sh.expect("TEMP directory issue")
        sh.assert_env_var("errorlevel", "1")


@PARAMETRIZE_CMD_EXE
def test_cmd_exe_activate_script_failure(
    shell_wrapper_integration: tuple[str, str, str],
    shell: Shell,
) -> None:
    """Test that activation fails gracefully when an activation script fails."""
    prefix, _, _ = shell_wrapper_integration

    # Create a failing activation script in the environment
    activate_d = Path(prefix) / "etc" / "conda" / "activate.d"
    activate_d.mkdir(parents=True, exist_ok=True)
    failing_script = activate_d / "fail.bat"
    failing_script.write_text("@echo Failing activation script\n@exit /b 1\n")

    with shell.interactive() as sh:
        sh.sendline(f'conda {activate} "{prefix}"')
        sh.expect("ERROR: Activation script")
        sh.expect("failed with code")
        sh.assert_env_var("errorlevel", "4")


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
