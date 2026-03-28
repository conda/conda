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

__all__ = ["plugins"]
