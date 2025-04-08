# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Register the conda env spec for requirements.txt files."""

from .. import CondaEnvironmentSpecifier, hookimpl


@hookimpl
def conda_environment_specifiers():
    from ...env.specs.binstar import BinstarSpec

    yield CondaEnvironmentSpecifier(
        name="binstar",
        handler_class=BinstarSpec,
    )
