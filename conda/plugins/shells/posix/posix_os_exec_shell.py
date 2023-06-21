# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
import subprocess
from pathlib import PurePath

from conda.activate import native_path_to_unix
from conda.plugins import CondaShellPlugins, hookimpl

POSIX_SHELLS = {"ash", "bash", "dash", "ksh", "sh", "zsh"}


def determine_shell(command: str) -> bool:
    """
    Execute the specified command as a Python subprocess, through the shell.
    Determine whether the final path component of the output is in the set of
        compatible shells.
    """
    s = subprocess.run(command, shell=True, capture_output=True)

    output = s.stdout.decode().strip("\n")

    return PurePath(output).name in POSIX_SHELLS


@hookimpl
def conda_shell_plugins():
    if determine_shell("echo $0") or determine_shell(
        "shellPID=$$; ps -ocomm= $shellPID"
    ):
        yield CondaShellPlugins(
            name="posixp",
            summary="Plugin for POSIX shells used for activate, deactivate, and reactivate",
            script_path=os.path.abspath(
                "conda/plugins/shells/shell_scripts/posix_os_exec_shell.sh"
            ),
            pathsep_join=":".join,
            sep="/",
            path_conversion=staticmethod(native_path_to_unix),
            script_extension=".sh",
            tempfile_extension=None,
            command_join="\n",
            run_script_tmpl='. "%s"',
        )
