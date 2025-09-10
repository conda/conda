# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
**EXPERIMENTAL**
Register the conda env spec for environment.yml files.
"""

from .. import hookimpl
from ..types import CondaEnvironmentSpecifier


@hookimpl(tryfirst=True)
def conda_environment_specifiers():
    from ...env.specs.yaml_file import YamlFileSpec

    yield CondaEnvironmentSpecifier(
        name="environment.yml",
        environment_spec=YamlFileSpec,
    )
