# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
from pathlib import PurePath

import psutil

from conda.activate import native_path_to_unix
from conda.plugins import CondaShellPlugins, hookimpl

COMPATIBLE_SHELLS = {"csh", "tcsh"}


def confirm_csh_tcsh_shell() -> bool:
    """
    Determine whether the final path component of the shell process executable is in
    the set of compatible shells. Return True if the shell is csh or tcsh.
    """
    shell_process = psutil.Process(psutil.Process().ppid()).exe()

    return PurePath(shell_process).name in COMPATIBLE_SHELLS


@hookimpl
def conda_shell_plugins():
    if confirm_csh_tcsh_shell():
        yield CondaShellPlugins(
            name="csh_tcsh_plugin",
            summary="Plugin for csh and tcsh shells used for activate, deactivate, and reactivate",
            script_path=os.path.abspath(
                "conda/plugins/shells/shell_scripts/csh_tcsh_shell.csh"
            ),
            pathsep_join=":".join,
            sep="/",
            path_conversion=native_path_to_unix,
            script_extension=".csh",
            tempfile_extension=None,
            command_join=";\n",
            run_script_tmpl='source "%s"',
        )
