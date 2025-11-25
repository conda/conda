# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
**EXPERIMENTAL**
Register the conda env spec for explicit files.
"""

from .. import hookimpl
from ..types import CondaEnvironmentSpecifier


@hookimpl
def conda_environment_specifiers():
    from ...env.specs.explicit import ExplicitSpec

    yield CondaEnvironmentSpecifier(
        name="explicit",
        environment_spec=ExplicitSpec,
    )
