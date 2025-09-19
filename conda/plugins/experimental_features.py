# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Experimental features for conda."""

from . import hookimpl
from .types import CondaExperimentalFeaturePlugin


@hookimpl
def conda_experimental_features():
    yield CondaExperimentalFeaturePlugin(
        name="jlap",
        help="Download incremental package index data from repodata.jlap; implies 'lock'.",
    )
    yield CondaExperimentalFeaturePlugin(
        name="lock",
        help="Use locking when reading, updating index (repodata.json) cache. Now enabled.",
    )
