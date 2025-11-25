# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda.cli.main import main_sourced
from conda.common.compat import on_win

if TYPE_CHECKING:
    from conda.testing.fixtures import CondaCLIFixture


def test_main():
    with pytest.raises(SystemExit):
        __import__("conda.__main__")


@pytest.mark.parametrize("option", ("--trace", "-v", "--debug", "--json"))
def test_ensure_no_command_provided_returns_help(
    conda_cli: CondaCLIFixture, capsys, option
):
    """
    Regression test to make sure that invoking with just any of the options listed as parameters
    will not return a traceback.
    """
    with pytest.raises(SystemExit):
        conda_cli(option)

    captured = capsys.readouterr()

    assert "error: the following arguments are required: COMMAND" in captured.err


@pytest.mark.skipif(not on_win, reason="Windows-specific test")
@pytest.mark.parametrize(
    "shell,expected_patterns",
    [
        ("zsh", ["export"]),
        ("bash", ["export"]),
        ("posix", ["export"]),
        ("ash", ["export"]),
        ("dash", ["export"]),
        ("csh", ["setenv", "unsetenv"]),
        ("tcsh", ["setenv", "unsetenv"]),
        ("fish", ["set -gx", "set -e"]),
    ],
)
def test_main_sourced_shell_line_endings_fix_needed(
    shell: str, expected_patterns: list[str], capsys
) -> None:
    """Test that shells that need line ending fixes get appropriate treatment on Windows."""
    assert main_sourced(shell, "hook") == 0
    output = capsys.readouterr().out

    assert "\r" not in output
    assert any(pattern in output for pattern in expected_patterns)


@pytest.mark.skipif(not on_win, reason="Windows-specific test")
@pytest.mark.parametrize(
    "shell,expected_patterns",
    [
        ("cmd.exe", ["conda activate"]),
        ("powershell", ["$Env:", "Import-Module"]),
        ("xonsh", ["source-cmd", "source-bash"]),
    ],
)
def test_main_sourced_shell_line_endings_no_fix_needed(
    shell: str, expected_patterns: list[str], capsys
) -> None:
    """Test that shells that don't need line ending fixes work correctly on Windows."""
    assert main_sourced(shell, "hook") == 0
    output = capsys.readouterr().out

    assert any(pattern in output for pattern in expected_patterns)


@pytest.mark.skipif(on_win, reason="Unix-specific test")
@pytest.mark.parametrize(
    "shell,expected_patterns",
    [
        ("bash", ["export"]),
        ("zsh", ["export"]),
        ("fish", ["set -gx", "set -e"]),
        ("csh", ["setenv", "unsetenv"]),
        ("tcsh", ["setenv", "unsetenv"]),
        ("xonsh", ["source-bash"]),
    ],
)
def test_main_sourced_unix_shells_no_line_ending_fix(
    shell: str, expected_patterns: list[str], capsys
) -> None:
    """Test that Unix shells work correctly without line ending fixes."""
    assert main_sourced(shell, "hook") == 0
    output = capsys.readouterr().out

    assert any(pattern in output for pattern in expected_patterns)
