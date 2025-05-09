# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Register the conda env spec for explicit environment files."""

from .. import CondaEnvironmentSpecifier, hookimpl


@hookimpl
def conda_environment_specifiers():
    from ...env.specs.explicit import ExplicitFileSpec

    yield CondaEnvironmentSpecifier(
        name="explicit",
        environment_spec=ExplicitFileSpec,
    )
