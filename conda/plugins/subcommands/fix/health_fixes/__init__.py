# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Built-in health fixes for `conda fix`.

These health fixes remediate issues detected by `conda doctor` health checks.
"""

from . import (
    altered_files,
    environment_txt,
    inconsistent_packages,
    malformed_pinned,
    missing_files,
)

#: The list of health fix plugins for easier registration with pluggy
plugins = [
    altered_files,
    environment_txt,
    inconsistent_packages,
    malformed_pinned,
    missing_files,
]
