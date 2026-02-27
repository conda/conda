# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda.activate import FishActivator
from conda.common.compat import on_win

if TYPE_CHECKING:
    from . import Shell

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(on_win, reason="unavailable on Windows"),
]
PARAMETRIZE_FISH = pytest.mark.parametrize("shell", ["fish"], indirect=True)


@PARAMETRIZE_FISH
def test_shell_available(shell: Shell) -> None:
    # the `shell` fixture does all the work
    pass


@PARAMETRIZE_FISH
def test_fish_basic_integration(shell: Shell) -> None:
    """Test basic Fish shell integration with conda activation/deactivation."""
    with shell.interactive() as sh:
        # Verify initial state
        sh.assert_env_var("CONDA_SHLVL", "0")

        # Test activation
        sh.sendline("conda activate base")
        sh.assert_env_var("CONDA_SHLVL", "1")
        sh.assert_env_var("CONDA_DEFAULT_ENV", "base")

        # Test deactivation
        sh.sendline("conda deactivate")
        sh.assert_env_var("CONDA_SHLVL", "0")


def test_fish_disable_prompt(monkeypatch):
    """Test that CONDA_DISABLE_FISH_PROMPT prevents prompt function redefinition."""

    monkeypatch.setenv("CONDA_DISABLE_FISH_PROMPT", "1")

    activator = FishActivator()
    hook_script = activator.hook()

    # Verify the script checks for CONDA_DISABLE_FISH_PROMPT
    assert "CONDA_DISABLE_FISH_PROMPT" in hook_script
    assert "if not set -q CONDA_DISABLE_FISH_PROMPT" in hook_script

    # Verify prompt functions are wrapped in the conditional
    assert "__conda_add_prompt" in hook_script
    assert "fish_prompt" in hook_script


def test_fish_prompt_functions_in_hook():
    """Test that Fish hook script contains prompt modification code."""

    activator = FishActivator()
    hook_script = activator.hook()

    # Verify the hook contains the prompt modification code
    assert "function __conda_add_prompt" in hook_script
    assert "function fish_prompt" in hook_script
    assert "function fish_right_prompt" in hook_script
    assert "__fish_prompt_orig" in hook_script
    assert "__fish_right_prompt_orig" in hook_script
