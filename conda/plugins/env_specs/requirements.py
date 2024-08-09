# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Register the conda env spec for requirements.txt files."""

from .. import CondaEnvSpec, hookimpl


@hookimpl
def conda_env_specs():
    from ...env.specs.requirements import RequirementsSpec

    yield CondaEnvSpec(
        name="requirements",
        handler_class=RequirementsSpec,
        extensions=RequirementsSpec.extensions,
    )
