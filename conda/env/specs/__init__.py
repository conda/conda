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
    SpecNotFound,
)
from ...gateways.connection.session import CONDA_SESSION_SCHEMES

if TYPE_CHECKING:
    from typing import Type, Union

    from ..env import Environment
    from .binstar import BinstarSpec
    from .requirements import RequirementsSpec
    from .yaml_file import YamlFileSpec

    FileSpecTypes = Union[Type[YamlFileSpec], Type[RequirementsSpec]]
    SpecTypes = Union[BinstarSpec, YamlFileSpec, RequirementsSpec]


class BaseEnvSpec:
    msg: str | None = None

    def can_handle(self) -> bool:
        raise NotImplementedError

    @property
    def environment(self) -> Environment:
        raise NotImplementedError


@deprecated("24.7", "25.1", addendum="Not used anymore")
def get_spec_class_from_file(filename: str) -> FileSpecTypes:
    """
    Determine spec class to use from the provided ``filename``

    :raises EnvironmentFileExtensionNotValid | EnvironmentFileNotFound:
    """
    from .requirements import RequirementsSpec
    from .yaml_file import YamlFileSpec
    if filename.startswith("file://"):
        filename = filename[len("file://"):]

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
    else:
        raise EnvironmentFileNotFound(filename=filename)


@deprecated.argument("24.7", "25.1", "name")
@deprecated.argument("24.7", "25.1", "filename", rename="resource")
@deprecated.argument("24.7", "25.1", "directory")
@deprecated.argument("24.7", "25.1", "remote_definition", rename="resource")
def detect(
    resource: str = None,
    # everything else is not used anymore
    name: str = None,
    filename: str = None,
    directory: str = None,
    remote_definition: str = None,
) -> SpecTypes:
    """
    Return the appropriate spec type to use.

    :raises SpecNotFound: Raised if no suitable spec class could be found given the input
    """
    if not resource:
        if filename:
            resource = filename
        elif remote_definition:
            resource = remote_definition
    spec_hook = context.plugin_manager.get_env_spec_handler(resource)
    spec = spec_hook.handler_class(resource)
    if spec.can_handle():
        return spec
    raise SpecNotFound(spec.msg)
