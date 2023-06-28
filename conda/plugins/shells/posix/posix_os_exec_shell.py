# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
from pathlib import PurePath

import psutil

from conda.activate import native_path_to_unix
from conda.plugins import CondaShellPlugins, hookimpl

POSIX_SHELLS = {"ash", "bash", "dash", "ksh", "sh", "zsh"}


def determine_posix_shell() -> bool:
    """
    Determine whether the final path component of the shell process executable is in
    the set of compatible shells.
    """
    shell_process = psutil.Process(psutil.Process().ppid()).exe()

    return PurePath(shell_process).name in POSIX_SHELLS


@hookimpl
def conda_shell_plugins():
    if determine_posix_shell():
        yield CondaShellPlugins(
            name="posixp",
            summary="Plugin for POSIX shells used for activate, deactivate, and reactivate",
            script_path=os.path.abspath(
                "conda/plugins/shells/shell_scripts/posix_os_exec_shell.sh"
            ),
            pathsep_join=":".join,
            sep="/",
            path_conversion=native_path_to_unix,
            script_extension=".sh",
            tempfile_extension=None,
            command_join="\n",
            run_script_tmpl='. "%s"',
        )
