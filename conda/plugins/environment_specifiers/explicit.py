# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
**EXPERIMENTAL**
Register the conda env spec for explicit files.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .. import hookimpl
from ..types import CondaEnvironmentSpecifier
from ...base.constants import EXPLICIT_MARKER
from ...misc import get_package_records_from_explicit
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
        * the file has the "@EXPLICIT" marker

    :return: True if the file can be handled, False otherwise
    """
    # Return early if no filename was provided
    if filename is None:
        return False

    # Ensure the file has the "@EXPLICIT" marker
    dependencies_list = [
        dep for dep in data.split("\n") if (dep and not dep.startswith("#"))
    ]
    if EXPLICIT_MARKER in dependencies_list:
        return True
    else:
        return False


def environment(data: str) -> Environment:
    # Convert generator to list since Dependencies needs to access it multiple times
    dependencies_list = [
        dep for dep in data.split("\n") if (dep and not dep.startswith("#"))
    ]
    explicit_packages = get_package_records_from_explicit(dependencies_list)

    return Environment(
        platform=context.subdir,
        explicit_packages=explicit_packages,
    )


@hookimpl
def conda_environment_specifiers():
    yield CondaEnvironmentSpecifier(
        name="explicit",
        validate=validate,
        env=environment,
        detection_supported=True,
    )
