# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Experimental features for conda."""

from . import hookimpl
from .types import CondaExperimentalFeature


@hookimpl
def conda_experimental_features():
    yield CondaExperimentalFeature(
        name="jlap",
        help="Download incremental package index data from repodata.jlap; implies 'lock'.",
    )
    yield CondaExperimentalFeature(
        name="lock",
        help="Use locking when reading, updating index (repodata.json) cache. Now enabled.",
    )
