# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Built-in plugin settings for repodata behavior shared across solvers.
"""

from __future__ import annotations

from conda.common.configuration import PrimitiveParameter
from conda.plugins import hookimpl
from conda.plugins.types import CondaSetting


@hookimpl
def conda_settings():
    yield CondaSetting(
        name="use_sharded_repodata",
        description="Enable use of sharded repodata when available.",
        parameter=PrimitiveParameter(True, element_type=bool),
    )
