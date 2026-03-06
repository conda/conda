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
from conda.base.constants import WINDOWS_PROBLEMATIC_CHARS
from conda.base.context import context, reset_context
from conda.common.compat import on_linux, on_mac

from . import activate, deactivate, dev_arg, install

if TYPE_CHECKING:
    from pytest import MonkeyPatch

    from conda.testing.fixtures import TmpEnvFixture

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
        sh.assert_env_var("PROMPT", r"\(charizard\).*")
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
        sh.assert_env_var("PROMPT", rf"\({escape(prefix)}\).*")

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
    _, prefix2, prefix3 = shell_wrapper_integration

    with shell.interactive() as sh:
        sh.sendline("echo off")

        sh.assert_env_var("_CE_CONDA", "conda")

        PATH = f"{CONDA_PACKAGE_ROOT}\\shell\\Scripts;%PATH%"

        sh.sendline("SET PATH=" + PATH)

        sh.sendline(f'activate --dev "{prefix2}"')
        sh.clear()

        sh.assert_env_var("CONDA_SHLVL", "1")

        PATH = sh.get_env_var("PATH")
        assert "charizard" in PATH

        sh.assert_env_var("_CE_CONDA", "conda")

        sh.sendline("conda --version")
        sh.expect_exact(f"conda {CONDA_VERSION}")

        sh.sendline(f'activate.bat --dev "{prefix3}"')
        PATH = sh.get_env_var("PATH")
        assert "venusaur" in PATH

        sh.sendline("deactivate.bat --dev")
        PATH = sh.get_env_var("PATH")
        assert "charizard" in PATH

        sh.sendline("deactivate --dev")
        sh.assert_env_var("CONDA_SHLVL", "0")


@PARAMETRIZE_CMD_EXE
@pytest.mark.parametrize("char", WINDOWS_PROBLEMATIC_CHARS)
def test_cmd_exe_special_char_env_activate_by_path(
    shell: Shell,
    char: str,
    tmp_env: TmpEnvFixture,
) -> None:
    """
    Test activation of environments with special characters by path.

    This test creates environments with special characters in their names
    and attempts to activate them using the -p/--prefix flag (by path).

    See: https://github.com/conda/conda/issues/12558

    These tests characterize current behavior. Some may fail, indicating
    which characters are truly problematic vs which work correctly.
    """
    with tmp_env(path_infix=char) as prefix, shell.interactive() as sh:
        # Activation by path should work for most special chars.
        # Caret is explicitly unsupported in cmd.exe activation.
        sh.sendline(f'conda {activate} "{prefix}"')
        if char == "^":
            sh.expect(
                r"Cannot activate environments with '^' in their path from cmd.exe"
            )
            sh.assert_env_var("errorlevel", "2")
            return

        sh.clear()

        # Check if activation succeeded by checking CONDA_PREFIX
        conda_prefix = sh.get_env_var("CONDA_PREFIX", "")

        # Assert activation worked
        assert prefix.samefile(conda_prefix)

        # Deactivate
        sh.sendline(f"conda {deactivate}")
        sh.assert_env_var("CONDA_SHLVL", "0")


@PARAMETRIZE_CMD_EXE
@pytest.mark.parametrize("char", WINDOWS_PROBLEMATIC_CHARS)
def test_cmd_exe_special_char_prompt_display(
    shell: Shell,
    char: str,
    tmp_env: TmpEnvFixture,
    monkeypatch: MonkeyPatch,
) -> None:
    """
    Test that prompts display correctly with special characters in env names.

    The = character was known to cause prompt corruption like:
        (python=3.12) 3.12) ==3.12) C:\\path>

    See: https://github.com/conda/conda/issues/12558
    """
    # NOTE: leading/trailing space doesn't work when setting CONDA_ENV_PROMPT since the
    # EnvRawParameter strips spaces
    modifier = "(<conda>{default_env})"
    monkeypatch.setenv("CONDA_ENV_PROMPT", modifier)
    reset_context()
    assert context.env_prompt == modifier

    prompt = "[prompt> "
    with (
        tmp_env(path_infix=char) as prefix,
        shell.interactive(env={"PROMPT": prompt}) as sh,
    ):
        sh.assert_env_var("PROMPT", escape(prompt))

        # Activate the environment
        sh.sendline(f'conda {activate} "{prefix}"')
        if char == "^":
            sh.expect(
                r"Cannot activate environments with '^' in their path from cmd.exe"
            )
            sh.assert_env_var("errorlevel", "2")
            return

        sh.clear()

        # Get the prompt - it should contain the env name in parentheses
        expected = f"{modifier}{prompt}".format(default_env=prefix)
        sh.assert_env_var("PROMPT", escape(expected))

        # Deactivate
        sh.sendline(f"conda {deactivate}")
        sh.assert_env_var("CONDA_SHLVL", "0")


@PARAMETRIZE_CMD_EXE
@pytest.mark.parametrize(
    "env_name",
    [
        # Verify that '!' is not stripped from environment paths.
        # When EnableDelayedExpansion is enabled in batch scripts, the '!' character is
        # consumed, causing activation to fail because the path would be mangled.
        # See: https://github.com/conda/conda/issues/12558 (! issue)
        # See: https://github.com/conda/conda/pull/14607 (removed EnableDelayedExpansion)
        "test!important!env",
        # Existing environments with '=' must remain usable.
        # While we may disallow creating new environments with '=', existing ones
        # must continue to work when accessed by path.
        # See: https://github.com/conda/conda/issues/13975 (existing envs with '=' issue)
        "python=3.12",
    ],
)
def test_cmd_exe_existing_env_with_special_chars(
    shell: Shell,
    tmp_env: TmpEnvFixture,
    env_name: str,
) -> None:
    """
    Regression tests for special characters in environment names.
    """
    # Simulate an existing environment
    with tmp_env(name=env_name) as env_path, shell.interactive() as sh:
        # Activate by path (this should always work)
        sh.sendline(f'conda {activate} "{env_path}"')
        sh.clear()

        # Verify we're in the environment
        sh.assert_env_var("CONDA_SHLVL", "1")

        # Verify CONDA_PREFIX points to our env
        prefix = sh.get_env_var("CONDA_PREFIX", "")

        assert Path(prefix).name == env_name

        # Deactivate
        sh.sendline(f"conda {deactivate}")
        sh.assert_env_var("CONDA_SHLVL", "0")
