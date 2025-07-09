# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
**EXPERIMENTAL**
Register the conda env spec for binstar specs.
"""

import warnings

from .. import CondaEnvironmentSpecifier, hookimpl


@hookimpl
def conda_environment_specifiers():
    # FUTURE: conda 26.3+, remove ignore BinstarSpec deprecation
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="conda.env.specs.binstar")
        from ...env.specs.binstar import BinstarSpec

    yield CondaEnvironmentSpecifier(
        name="binstar",
        environment_spec=BinstarSpec,
    )
