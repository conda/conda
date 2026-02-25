# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
**EXPERIMENTAL**
Register the conda env spec for environment.yml files.
"""

from __future__ import annotations

import os
from functools import partial
from logging import getLogger
from typing import TYPE_CHECKING

from ...common.serialize import yaml
from ...env import env
from ...exceptions import CondaError
from .. import hookimpl
from ..types import CondaEnvironmentSpecifier

if TYPE_CHECKING:
    from ...common.path import PathType
    from ...models.environment import Environment


log = getLogger(__name__)


VALID_EXTENSIONS = {".yaml", ".yml"}


def validate(filename: PathType, data: str, schema_errors: bool) -> bool:
    """
    Validates loader can process environment definition.
    This can handle if:
        * the provided file exists
        * the provided file ends in the supported file extensions (.yaml or .yml)
        * the provided file is compliant with the CEP-0024

    If schema_errors is True, then this function will fail if it detects any schema errors
    that make the file non-compliant with CEP-0024. If schema_errors is False, then this
    function will return True as long as the file is a valid YAML file, even if it has
    schema errors that make it non-compliant with CEP-0024.

    :return: True or False
    """
    if not filename:
        return False

    # Extract the file extension (e.g., '.txt' or '' if no extension)
    _, file_ext = os.path.splitext(filename)

    # Check if the file has a supported extension and exists
    if file_ext.lower() not in VALID_EXTENSIONS:
        return False

    try:
        yaml_data = yaml.loads(data)
        if schema_errors:
            if yaml_data is None:
                return False
            errors = env.get_schema_errors(yaml_data)
            if errors:
                return False
        return True
    except CondaError:
        log.debug("Failed to load %s as a YAML.", filename, exc_info=True)
        return False


def environment(data: str) -> Environment:
    environment_yaml = env.from_yaml(data)
    return environment_yaml.to_environment_model()


@hookimpl()
def conda_environment_specifiers():
    yield CondaEnvironmentSpecifier(
        name="cep-24",
        validate=partial(validate, schema_errors=True),
        env=environment,
        detection_supported=True,
    )

    yield CondaEnvironmentSpecifier(
        name="environment.yml",
        validate=partial(validate, schema_errors=False),
        env=environment,
        detection_supported=False,
    )
