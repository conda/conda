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


@pytest.mark.skipif(
    not on_win, reason="MSYS2 shells line ending fix only applies on Windows"
)
@pytest.mark.parametrize("shell", ["zsh", "bash", "posix"])
def test_main_sourced_msys2_shell_line_endings(shell: str, capsys) -> None:
    """Test that main_sourced produces clean output for MSYS2 shells."""
    assert main_sourced(shell, "hook") == 0
    output = capsys.readouterr().out
    assert "\r" not in output
    assert "export" in output


@pytest.mark.skipif(
    not on_win, reason="MSYS2 shells line ending fix only applies on Windows"
)
def test_main_sourced_stdout_reconfiguration(capsys) -> None:
    """Test that main_sourced reconfigures stdout for MSYS2 shells."""
    assert main_sourced("zsh", "hook") == 0
    assert "\r" not in capsys.readouterr().out


@pytest.mark.skipif(not on_win, reason="Windows-specific test")
def test_main_sourced_cmd_exe_unchanged(capsys) -> None:
    """Test that cmd.exe is not affected by our MSYS2 line ending fix."""
    assert main_sourced("cmd.exe", "hook") == 0
    output = capsys.readouterr().out
    assert "conda activate" in output


@pytest.mark.skipif(not on_win, reason="Windows-specific test")
def test_main_sourced_powershell_unchanged(capsys) -> None:
    """Test that PowerShell is not affected by our MSYS2 line ending fix."""
    assert main_sourced("powershell", "hook") == 0
    output = capsys.readouterr().out
    assert "$Env:" in output
    assert "Import-Module" in output
