# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI reimplementation for run"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace


def execute(args: Namespace, parser: ArgumentParser) -> int:
    import os
    import subprocess
    from pathlib import Path
    from tempfile import TemporaryDirectory

    from rattler import shell

    from conda.base.context import context
    from conda.common.compat import on_win
    from conda.exceptions import ArgumentError
    from conda.utils import quote_for_shell

    # Used to separate subcommand from 'conda run' options
    # e.g. conda run -v -- tar -tvf file.tar
    if args.executable_call and args.executable_call[0] == "--":
        args.executable_call = args.executable_call[1:]

    if not args.executable_call:
        raise ArgumentError("No command specified. Please provide a command to run.")

    activation = shell.activate(
        prefix=context.target_prefix,
        activation_variables=shell.ActivationVariables(
            current_path=os.environ.get("PATH", "").split(os.pathsep),
            current_prefix=os.environ.get("CONDA_PREFIX"),
            path_modification_behavior=shell.PathModificationBehavior.Prepend,
        ),
        shell=shell.Shell.cmd_exe if on_win else shell.Shell.bash,
    )
    # TODO: Deactivation not exposed in py-rattler??

    with TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        script = tmp / f"script.{'bat' if on_win else 'sh'}"
        contents = f"{activation.script}\n\n{quote_for_shell(args.executable_call)}"
        script.write_text(contents)

        p = subprocess.run(["cmd.exe" if on_win else "bash", script], cwd=args.cwd)

    return p.returncode

