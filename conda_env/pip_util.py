# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""DEPRECATED: Use `conda.env.pip_util.py` instead.

Environment object describing the conda environment.yaml file.
"""
# Import from conda.env.pip_util since this module is deprecated.
from conda.env.pip_util import (  # noqa
    get_pip_installed_packages,
    get_pip_version,
    pip_subprocess,
)
from conda.deprecations import deprecated

deprecated.module("23.9", "24.3", addendum="Use `conda.env.pip_util.py` instead.")
