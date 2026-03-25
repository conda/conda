# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI reimplementation for activate"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace


def execute(args: Namespace, parser: ArgumentParser) -> int:
    import os
    import re
    from pathlib import Path

    from rattler import shell

    from conda.base.constants import RESERVED_ENV_NAMES
    from conda.base.context import context, locate_prefix_by_name
    from conda.common.compat import on_win
    from conda.exceptions import ArgumentError, EnvironmentLocationNotFound

    if len(args.args) != 1:
        raise ArgumentError("Must provide an environment name or prefix to activate")
    env_name_or_prefix = args.args[0]

    if re.search(r"\\|/", env_name_or_prefix):
        prefix = Path(env_name_or_prefix).expanduser()
        if not (prefix / "conda-meta" / "history").is_file():
            raise EnvironmentLocationNotFound(prefix)
    elif env_name_or_prefix in RESERVED_ENV_NAMES:
        prefix = context.root_prefix
    else:
        prefix = locate_prefix_by_name(env_name_or_prefix)

    activation = shell.activate(
        prefix=prefix,
        activation_variables=shell.ActivationVariables(
            current_path=os.environ.get("PATH", "").split(os.pathsep),
            current_prefix=os.environ.get("CONDA_PREFIX"),
            path_modification_behavior=shell.PathModificationBehavior.Prepend,
        ),
        # TODO: Use Shellingham or similar to autodetect; or contribute .current() to rattler
        shell=shell.Shell.cmd_exe if on_win else shell.Shell.bash,
    )
    print(activation.script)
    # TODO: Missing PS1 modifications; contribute
    if not on_win:
        print(f'PS1="({Path(prefix).name}) ${{PS1:-}}"')
    return 0
