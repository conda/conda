# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
from pathlib import PurePath

from conda.activate import native_path_to_unix
from conda.plugins import CondaShellPlugins, hookimpl

POSIX_SHELLS = {"ash", "bash", "zsh", "sh", "dash", "ksh"}


@hookimpl
def conda_shell_plugins():
    if (
        PurePath(os.environ.get("SHELL", "")).name in POSIX_SHELLS
    ):  # change to figure out what shell is CURRENTLY in use, not default shell
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
