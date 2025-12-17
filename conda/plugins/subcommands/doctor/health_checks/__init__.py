# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Health checks for `conda doctor`.

This package contains individual health check modules that are registered
via the conda_health_checks plugin hook.
"""

from __future__ import annotations

from . import (
    altered_files,
    consistency,
    environment_txt,
    file_locking,
    missing_files,
    pinned,
    requests_ca_bundle,
)

# The list of health check plugins for easier registration with pluggy
plugins = [
    altered_files,
    consistency,
    environment_txt,
    file_locking,
    missing_files,
    pinned,
    requests_ca_bundle,
]

# Re-export common utilities
from ._common import OK_MARK, X_MARK, excluded_files_check, reinstall_packages

# Re-export public symbols for backward compatibility
from .altered_files import altered_files as altered_files_action
from .altered_files import find_altered_packages, fix_altered_files
from .consistency import (
    consistent_env_check,
    find_inconsistent_packages,
    fix_inconsistent_packages,
)
from .environment_txt import check_envs_txt_file, env_txt_check, fix_env_txt
from .file_locking import file_locking_check
from .missing_files import find_packages_with_missing_files, fix_missing_files
from .missing_files import missing_files as missing_files_action
from .pinned import (
    find_malformed_pinned_specs,
    fix_malformed_pinned,
    pinned_well_formatted_check,
)
from .requests_ca_bundle import requests_ca_bundle_check

# Backward compatibility aliases
altered_files = altered_files_action
missing_files = missing_files_action

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
    # Plugin list
    "plugins",
]
