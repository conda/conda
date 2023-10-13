# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""DEPRECATED: Use `conda.env.env` instead.

Environment object describing the conda environment.yaml file.
"""
# Import from conda.env.env since this module is deprecated.
import os

from conda.deprecations import deprecated
from conda.env.env import (  # noqa
    VALID_KEYS,
    Dependencies,
    Environment,
    from_environment,
    from_file,
    from_yaml,
    validate_keys,
)
from conda.exceptions import EnvironmentFileNotFound

deprecated.module("24.3", "24.9", addendum="Use `conda.env.env` instead.")


@deprecated("23.9", "24.3")
def load_from_directory(directory):
    """Load and return an ``Environment`` from a given ``directory``"""
    files = ["environment.yml", "environment.yaml"]
    while True:
        for f in files:
            try:
                return from_file(os.path.join(directory, f))
            except EnvironmentFileNotFound:
                pass
        old_directory = directory
        directory = os.path.dirname(directory)
        if directory == old_directory:
            break
    raise EnvironmentFileNotFound(files[0])
