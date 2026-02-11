# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
**EXPERIMENTAL**
Register the conda env spec for requirements.txt files.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from .. import hookimpl
from ..types import CondaEnvironmentSpecifier
from ...models.match_spec import MatchSpec
from ...base.context import context
from ...models.environment import Environment


if TYPE_CHECKING:
    from ...common.path import PathType

VALID_EXTENSIONS = {".txt"}


def validate(filename: PathType, data: str) -> bool:
    """
    Validates that this spec can process the environment definition.
    This checks if:
        * a filename was provided
        * the file has a supported extension
        * the file exists
        * the file content is valid for this specifier type

    :return: True if the file can be handled, False otherwise
    """
    # Return early if no filename was provided
    if filename is None:
        return False

    # Extract the file extension (e.g., '.txt' or '' if no extension)
    _, file_ext = os.path.splitext(filename)

    # Check if the file has a supported extension
    if not any(spec_ext == file_ext for spec_ext in VALID_EXTENSIONS):
        return False

    # Ensure this is not an explicit file. Requirements.txt and explicit files
    # may sometimes share file extension.
    dependencies_list = [
        dep for dep in data.split("\n") if (dep and not dep.startswith("#"))
    ]
    if "@EXPLICIT" in dependencies_list:
        return False
    return True


def environment(data: str) -> Environment:
    # Convert generator to list since Dependencies needs to access it multiple times
    dependencies_list = [
        dep for dep in data.split("\n") if (dep and not dep.startswith("#"))
    ]
    requested_packages = [MatchSpec(dep) for dep in dependencies_list]

    return Environment(
        platform=context.subdir,
        requested_packages=requested_packages,
    )


@hookimpl
def conda_environment_specifiers():
    yield CondaEnvironmentSpecifier(
        name="requirements.txt",
        validate=validate,
        env=environment,
        detection_supported=True,
    )
