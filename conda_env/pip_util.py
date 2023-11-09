# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""DEPRECATED: Use `conda.env.pip_util` instead.

Environment object describing the conda environment.yaml file.
"""
# Import from conda.env.pip_util since this module is deprecated.

from conda.deprecations import deprecated
from conda.env.pip_util import (  # noqa
    PipPackage,
    add_pip_installed,
    get_pip_installed_packages,
    get_pip_version,
    installed,
    pip_subprocess,
)

deprecated.module("24.3", "24.9", addendum="Use `conda.env.pip_util` instead.")
