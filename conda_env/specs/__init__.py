# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
from typing import Type, Union

from conda.exceptions import (
    EnvironmentFileExtensionNotValid,
    EnvironmentFileNotFound,
    SpecNotFound,
)
from conda.gateways.connection.session import CONDA_SESSION_SCHEMES

from .binstar import BinstarSpec
from .requirements import RequirementsSpec
from .yaml_file import YamlFileSpec

FileSpecTypes = Union[Type[YamlFileSpec], Type[RequirementsSpec]]


def get_spec_class_from_file(filename: str) -> FileSpecTypes:
    """
    Determine spec class to use from the provided ``filename``

    :raises EnvironmentFileExtensionNotValid | EnvironmentFileNotFound:
    """
    # Check extensions
    all_valid_exts = YamlFileSpec.extensions.union(RequirementsSpec.extensions)
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


SpecTypes = Union[BinstarSpec, YamlFileSpec, RequirementsSpec]


def detect(
    name: str = None,
    filename: str = None,
    directory: str = None,
    remote_definition: str = None,
) -> SpecTypes:
    """
    Return the appropriate spec type to use.

    :raises SpecNotFound: Raised if no suitable spec class could be found given the input
    :raises EnvironmentFileExtensionNotValid | EnvironmentFileNotFound:
    """
    if remote_definition is not None:
        spec = BinstarSpec(name=remote_definition)
        if spec.can_handle():
            return spec
        else:
            raise SpecNotFound(spec.msg)

    if filename is not None:
        spec_class = get_spec_class_from_file(filename)
        spec = spec_class(name=name, filename=filename, directory=directory)
        if spec.can_handle():
            return spec

    raise SpecNotFound(spec.msg)
