# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Register the conda env spec for environment.yml files."""

from .. import CondaEnvSpec, hookimpl


@hookimpl
def conda_env_specs():
    from ...env.specs.yaml_file import YamlFileSpec

    yield CondaEnvSpec(
        name="yaml_file",
        handler_class=YamlFileSpec,
        extensions=YamlFileSpec.extensions,
    )
