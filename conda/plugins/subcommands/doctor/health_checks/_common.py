# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Common utilities for health checks."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import Namespace

# Status marks for health check output
OK_MARK = "✅"
X_MARK = "❌"


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


def excluded_files_check(filename: str) -> bool:
    """Check if a file should be excluded from health checks."""
    excluded_extensions = (".pyc", ".pyo")
    return filename.endswith(excluded_extensions)
