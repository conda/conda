# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
from pathlib import PurePath

import psutil

from conda.activate import native_path_to_unix
from conda.plugins import CondaShellPlugins, hookimpl


def confirm_fish_shell() -> bool:
    """
    Return True if the final path component of the shell process executable is "fish".
    """
    shell_process = psutil.Process(psutil.Process().ppid()).exe()

    return PurePath(shell_process).name == "fish"


@hookimpl
def conda_shell_plugins():
    if confirm_fish_shell():
        yield CondaShellPlugins(
            name="fish_shell_plugin",
            summary="Plugin for fish used for activate, deactivate, and reactivate",
            script_path=os.path.abspath(
                "conda/plugins/shells/shell_scripts/fish_shell.fish"
            ),
            pathsep_join='" "'.join,
            sep="/",
            path_conversion=native_path_to_unix,
            script_extension=".fish",
            tempfile_extension=None,
            command_join=";\n",
            run_script_tmpl='source "%s"',
        )
