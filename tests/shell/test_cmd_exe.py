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
PARAMETRIZE_WINDOWS_PROBLEMATIC_CHARS = pytest.mark.parametrize(
    "special_char", WINDOWS_PROBLEMATIC_CHARS
)


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


# =============================================================================
# Special Character Tests (Issue #12558)
# =============================================================================
# These tests characterize the behavior of environment names containing special
# characters that are problematic in Windows CMD.EXE batch scripts.
#
# Background:
# - PR #13975 tried to disallow these characters but was reverted in #14065
# - The `!` character was historically broken due to EnableDelayedExpansion
# - PR #14607 rewrote the batch scripts to use static INI-style files
# - These tests verify current behavior and will inform the fix for #12558
# =============================================================================


@PARAMETRIZE_CMD_EXE
@PARAMETRIZE_WINDOWS_PROBLEMATIC_CHARS
def test_cmd_exe_special_char_env_activate_by_path(
    shell: Shell,
    special_char: str,
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
    with tmp_env(path_infix=special_char) as env_path, shell.interactive() as sh:
        # Try to activate by path (should work even if name validation fails)
        sh.sendline(f'conda {activate} "{env_path}"')

        # Give it time to process
        sh.sendline("echo ACTIVATION_COMPLETE")
        sh.expect("ACTIVATION_COMPLETE")

        # Check if activation succeeded by checking CONDA_PREFIX
        prefix = sh.get_env_var("CONDA_PREFIX", "")

        # Normalize paths for comparison
        expected_path = str(env_path).lower().replace("/", "\\")
        actual_path = prefix.lower().replace("/", "\\") if prefix else ""

        # Log the result for debugging
        log.info(
            f"Special char '{special_char}': "
            f"expected={expected_path}, actual={actual_path}"
        )

        # Assert activation worked
        assert actual_path == expected_path, (
            f"Activation failed for env with '{special_char}' in name. "
            f"Expected CONDA_PREFIX='{expected_path}', got '{actual_path}'"
        )

        # Deactivate
        sh.sendline(f"conda {deactivate}")
        sh.assert_env_var("CONDA_SHLVL", "0")


@PARAMETRIZE_CMD_EXE
@PARAMETRIZE_WINDOWS_PROBLEMATIC_CHARS
def test_cmd_exe_special_char_prompt_display(
    shell: Shell,
    special_char: str,
    tmp_env: TmpEnvFixture,
    monkeypatch: MonkeyPatch,
) -> None:
    """
    Test that prompts display correctly with special characters in env names.

    The = character was known to cause prompt corruption like:
        (python=3.12) 3.12) ==3.12) C:\\path>

    See: https://github.com/conda/conda/issues/12558
    """
    # Set env_prompt via environment variable and reload context
    # (this is the standard pattern used in test_activate.py)
    monkeypatch.setenv("CONDA_ENV_PROMPT", "({default_env}) ")
    reset_context()

    with tmp_env(path_infix=special_char) as env_path, shell.interactive() as sh:
        # Activate the environment
        sh.sendline(f'conda {activate} "{env_path}"')
        sh.sendline("echo ACTIVATION_COMPLETE")
        sh.expect("ACTIVATION_COMPLETE")

        # Get the prompt - it should contain the env name in parentheses
        prompt = sh.get_env_var("PROMPT", "")

        # Log for debugging
        log.info(f"Prompt with '{special_char}': {prompt!r}")

        # The prompt should start with the env name in parentheses
        # and should NOT have the corruption pattern
        expected_prefix = f"({env_path.name})"

        # Check for corruption patterns (e.g., repeated fragments)
        # The = sign was known to cause: (python=3.12) 3.12) ==3.12)
        corruption_indicators = [
            f"{special_char}{special_char}",  # doubled special char
            f") {env_path.name.split(special_char)[-1]})",  # partial name repeated
        ]

        has_corruption = any(
            indicator in prompt for indicator in corruption_indicators if indicator
        )

        # Log corruption detection
        if has_corruption:
            log.warning(f"Prompt corruption detected for '{special_char}': {prompt!r}")

        # Assert no corruption (this test documents current behavior)
        assert expected_prefix in prompt or not has_corruption, (
            f"Prompt corruption with '{special_char}' in env name. Prompt: {prompt!r}"
        )

        sh.sendline(f"conda {deactivate}")


@PARAMETRIZE_CMD_EXE
def test_cmd_exe_exclamation_mark_not_stripped(
    shell: Shell,
    tmp_env: TmpEnvFixture,
) -> None:
    """
    Regression test: Verify that '!' is not stripped from environment paths.

    The original issue (#12558) was that EnableDelayedExpansion in batch
    scripts would consume the '!' character, causing activation to fail
    because the path would be mangled.

    PR #14607 rewrote the scripts to avoid this issue.
    """
    env_name = "test!important!env"
    with tmp_env(name=env_name) as env_path, shell.interactive() as sh:
        # The key test: does the ! survive through activation?
        sh.sendline(f'conda {activate} "{env_path}"')
        sh.sendline("echo CHECK_EXCLAMATION")
        sh.expect("CHECK_EXCLAMATION")

        # Get CONDA_PREFIX and verify ! is present
        prefix = sh.get_env_var("CONDA_PREFIX", "")

        assert Path(prefix).name == env_name, (
            f"Environment name mangled. Expected 'test!important!env' in path, "
            f"got: {prefix!r}"
        )


@PARAMETRIZE_CMD_EXE
def test_cmd_exe_existing_env_with_equals_remains_usable(
    shell: Shell,
    tmp_env,
) -> None:
    """
    Regression test: Existing environments with '=' must remain usable.

    This was a key concern when PR #13975 was reverted - users had existing
    environments with names like 'python=3.12' that would become unusable.

    Even if we disallow creating NEW environments with '=', existing ones
    must continue to work when accessed by path.
    """
    # Simulate an existing environment named "python=3.12"
    env_name = "python=3.12"
    with tmp_env(name=env_name) as env_path, shell.interactive() as sh:
        # Activate by path (this should always work)
        sh.sendline(f'conda {activate} "{env_path}"')
        sh.sendline("echo ACTIVATION_DONE")
        sh.expect("ACTIVATION_DONE")

        # Verify we're in the environment
        shlvl = sh.get_env_var("CONDA_SHLVL", "0")

        # Should be at shell level 1 if activation succeeded
        assert shlvl == "1", (
            "Failed to activate existing env with '=' in name. "
            f"CONDA_SHLVL={shlvl}, expected 1"
        )

        # Verify CONDA_PREFIX points to our env
        prefix = sh.get_env_var("CONDA_PREFIX", "")
        assert Path(prefix).name == env_name, (
            f"CONDA_PREFIX doesn't contain env name. Got: {prefix!r}"
        )

        sh.sendline(f"conda {deactivate}")
