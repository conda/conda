# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Health checks for `conda doctor`.

This package contains individual health check modules that are registered
via the conda_health_checks plugin hook.
"""

from __future__ import annotations

from logging import getLogger
from typing import TYPE_CHECKING

from .... import hookimpl
from ....types import CondaHealthCheck

if TYPE_CHECKING:
    from argparse import Namespace

logger = getLogger(__name__)

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


# Import check/fix functions for backward compatibility
from .altered_files import altered_files, find_altered_packages, fix_altered_files
from .consistency import consistent_env_check, find_inconsistent_packages, fix_inconsistent_packages
from .environment_txt import check_envs_txt_file, env_txt_check, fix_env_txt
from .file_locking import file_locking_check
from .missing_files import find_packages_with_missing_files, fix_missing_files, missing_files
from .pinned import find_malformed_pinned_specs, fix_malformed_pinned, pinned_well_formatted_check
from .requests_ca_bundle import requests_ca_bundle_check

# Re-export all public symbols
__all__ = [
    # Constants
    "OK_MARK",
    "X_MARK",
    # Helpers
    "reinstall_packages",
    "excluded_files_check",
    # Missing files
    "find_packages_with_missing_files",
    "missing_files",
    "fix_missing_files",
    # Altered files
    "find_altered_packages",
    "altered_files",
    "fix_altered_files",
    # Environment.txt
    "check_envs_txt_file",
    "env_txt_check",
    "fix_env_txt",
    # Consistency
    "find_inconsistent_packages",
    "consistent_env_check",
    "fix_inconsistent_packages",
    # Pinned
    "find_malformed_pinned_specs",
    "pinned_well_formatted_check",
    "fix_malformed_pinned",
    # File locking
    "file_locking_check",
    # CA bundle
    "requests_ca_bundle_check",
]


@hookimpl
def conda_health_checks():
    """Register all built-in health checks."""
    from .....base.constants import PREFIX_PINNED_FILE

    yield CondaHealthCheck(
        name="Missing Files",
        action=missing_files,
        fix=fix_missing_files,
        summary="Reinstall packages with missing files",
    )
    yield CondaHealthCheck(
        name="Altered Files",
        action=altered_files,
        fix=fix_altered_files,
        summary="Reinstall packages with altered files",
    )
    yield CondaHealthCheck(
        name="Environment.txt File Check",
        action=env_txt_check,
        fix=fix_env_txt,
        summary="Register environment in environments.txt",
    )
    yield CondaHealthCheck(
        name="REQUESTS_CA_BUNDLE Check",
        action=requests_ca_bundle_check,
        # No fix - user must configure this manually
    )
    yield CondaHealthCheck(
        name="Consistent Environment Check",
        action=consistent_env_check,
        fix=fix_inconsistent_packages,
        summary="Resolve missing or inconsistent dependencies",
    )
    yield CondaHealthCheck(
        name=f"{PREFIX_PINNED_FILE} Well Formatted Check",
        action=pinned_well_formatted_check,
        fix=fix_malformed_pinned,
        summary="Clean up invalid specs in pinned file",
    )
    yield CondaHealthCheck(
        name="File Locking Supported Check",
        action=file_locking_check,
        # No fix - system-level issue
    )

