# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Built-in health fixes for `conda fix`.

These health fixes remediate issues detected by `conda doctor` health checks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import (
    altered_files,
    environment_txt,
    inconsistent_packages,
    malformed_pinned,
    missing_files,
)

if TYPE_CHECKING:
    from argparse import Namespace

# The list of health fix plugins for easier registration with pluggy
plugins = [
    altered_files,
    environment_txt,
    inconsistent_packages,
    malformed_pinned,
    missing_files,
]


def reinstall_packages(args: Namespace, specs: list[str], **kwargs) -> int:
    """Reinstall packages using conda install.

    Common helper for health fixes that need to reinstall packages.

    :param args: Parsed arguments namespace
    :param specs: Package specs to reinstall
    :param kwargs: Override default install options (e.g., force_reinstall=True)
    :return: Exit code from install
    """
    from .....cli.install import install

    args.packages = specs
    args.channel = kwargs.get("channel", None)
    args.override_channels = kwargs.get("override_channels", False)
    args.force_reinstall = kwargs.get("force_reinstall", False)
    args.satisfied_skip_solve = kwargs.get("satisfied_skip_solve", False)
    args.update_deps = kwargs.get("update_deps", False)
    args.only_deps = kwargs.get("only_deps", False)
    args.no_deps = kwargs.get("no_deps", False)
    args.prune = kwargs.get("prune", False)
    args.freeze_installed = kwargs.get("freeze_installed", False)
    args.solver_retries = kwargs.get("solver_retries", 0)

    return install(args)
