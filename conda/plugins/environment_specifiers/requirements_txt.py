# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Register the conda env spec for requirements.txt files."""

from .. import CondaEnvironmentSpecifier, hookimpl


@hookimpl
def conda_environment_specifiers():
    from ...env.specs.requirements import RequirementsSpec

    yield CondaEnvironmentSpecifier(
        name="requirements.txt",
        environment_spec=RequirementsSpec,
    )
