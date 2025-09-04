# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
**EXPERIMENTAL**
Register the conda env spec for binstar specs.
"""

from .. import hookimpl
from ..types import CondaEnvironmentSpecifier


@hookimpl
def conda_environment_specifiers():
    from ...env.specs.binstar import BinstarSpec

    yield CondaEnvironmentSpecifier(
        name="binstar",
        environment_spec=BinstarSpec,
    )
