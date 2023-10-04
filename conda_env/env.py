# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""DEPRECATED: Use `conda.env.env` instead.

Environment object describing the conda environment.yaml file.
"""
# Import from conda.env.env since this module is deprecated.
from conda.env.env import (  # noqa
    Environment,
    Dependencies,
    from_environment,
    from_file,
    from_yaml,
    load_from_directory,
    validate_keys,
    VALID_KEYS,
)
from conda.deprecations import deprecated

deprecated.module("23.9", "24.3", addendum="Use `conda.env.env` instead.")
