# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
**EXPERIMENTAL**
Register the conda env spec for requirements.txt files.
"""

from .. import hookimpl
from ..types import CondaEnvironmentSpecifier


@hookimpl
def conda_environment_specifiers():
    from ...env.specs.requirements import RequirementsSpec

    yield CondaEnvironmentSpecifier(
        name="requirements.txt",
        aliases=("requirements", "reqs"),
        environment_spec=RequirementsSpec,
        default_filenames=("requirements.txt", "spec.txt"),
        description="Simple text file with package specifications",
    )
