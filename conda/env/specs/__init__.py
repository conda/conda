# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from ...base.context import context
from ...deprecations import deprecated
from ...exceptions import (
    EnvironmentFileExtensionNotValid,
    EnvironmentFileNotFound,
    EnvironmentSpecPluginNotDetected,
    SpecNotFound,
)
from ...gateways.connection.session import CONDA_SESSION_SCHEMES

if TYPE_CHECKING:
    from .requirements import RequirementsSpec
    from .yaml_file import YamlFileSpec

    FileSpecTypes = type[YamlFileSpec] | type[RequirementsSpec]
    SpecTypes = YamlFileSpec | RequirementsSpec


@deprecated(
    "25.9",
    "26.3",
    addendum="Use conda.base.context.plugin_manager.detect_environment_specifier.",
)
def get_spec_class_from_file(filename: str) -> FileSpecTypes:
    """
    Determine spec class to use from the provided ``filename``

    :raises EnvironmentFileExtensionNotValid | EnvironmentFileNotFound:
    """
    from .requirements import RequirementsSpec
    from .yaml_file import YamlFileSpec

    if filename.startswith("file://"):
        filename = filename[len("file://") :]

    # Check extensions
    all_valid_exts = {*YamlFileSpec.extensions, *RequirementsSpec.extensions}
    _, ext = os.path.splitext(filename)

    # First check if file exists and test the known valid extension for specs
    file_exists = (
        os.path.isfile(filename) or filename.split("://", 1)[0] in CONDA_SESSION_SCHEMES
    )
    if file_exists:
        if ext == "" or ext not in all_valid_exts:
            raise EnvironmentFileExtensionNotValid(filename)
        elif ext in YamlFileSpec.extensions:
            return YamlFileSpec
        elif ext in RequirementsSpec.extensions:
            return RequirementsSpec
    raise EnvironmentFileNotFound(filename=filename)


@deprecated.argument("25.9", "26.3", "name")
@deprecated.argument(
    "25.9", "26.3", "directory", addendum="Specify the full path in filename"
)
def detect(
    filename: str | None = None,
) -> SpecTypes:
    """
    Return the appropriate spec type to use.

    :raises SpecNotFound: Raised if no suitable spec class could be found given the input
    """
    try:
        spec_hook = context.plugin_manager.detect_environment_specifier(
            source=filename,
        )
    except EnvironmentSpecPluginNotDetected as e:
        raise SpecNotFound(e.message)

    return spec_hook.environment_spec(filename)
