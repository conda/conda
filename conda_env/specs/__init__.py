# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
from typing import Union

from conda.exceptions import (
    EnvironmentFileExtensionNotValid,
    EnvironmentFileNotFound,
    SpecNotFound,
)
from conda.gateways.connection.session import CONDA_SESSION_SCHEMES

from .binstar import BinstarSpec
from .notebook import NotebookSpec
from .requirements import RequirementsSpec
from .yaml_file import YamlFileSpec


def get_spec_class_from_file(filename: str) -> list | None:
    """
    Determine spec class to use from the provided ``filename``

    :raises EnvironmentFileExtensionNotValid | EnvironmentFileNotFound:
    """
    specs = None

    if filename:
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
                specs = [YamlFileSpec]
            elif ext in RequirementsSpec.extensions:
                specs = [RequirementsSpec]
        else:
            raise EnvironmentFileNotFound(filename=filename)

    return specs


SpecClasses = Union[NotebookSpec, BinstarSpec, YamlFileSpec, RequirementsSpec]


def detect(name: str = None, filename: str = None, directory: str = None) -> SpecClasses:
    """
    Return the appropriate spec class to use. Possible return values:

    :raises SpecNotFound: Raised if no suitable spec class could be found given the input
    """
    specs = [NotebookSpec, BinstarSpec]

    if filename is not None:
        specs = get_spec_class_from_file(filename)

    # Check specifications
    spec_instances = []
    for spec_class in specs:
        spec = spec_class(name=name, filename=filename, directory=directory)
        spec_instances.append(spec)
        if spec.can_handle():
            return spec

    raise SpecNotFound(build_message(spec_instances))


def build_message(spec_instances):
    binstar_spec = next((s for s in spec_instances if isinstance(s, BinstarSpec)), None)
    if binstar_spec:
        return binstar_spec.msg
    else:
        return "\n".join([s.msg for s in spec_instances if s.msg is not None])
