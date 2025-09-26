# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Define explicit spec."""

from __future__ import annotations

from ...base.constants import EXPLICIT_MARKER
from ...base.context import context
from ...exceptions import CondaValueError
from ...gateways.disk.read import yield_lines
from ...misc import get_package_records_from_explicit
from ...models.environment import Environment
from ...plugins.types import EnvironmentSpecBase


class ExplicitSpec(EnvironmentSpecBase):
    """
    The ExplicitSpec class handles explicit environment files. These are ones
    which are marked with the @EXPLICIT marker.
    """

    def __init__(self, filename: str | None = None, **kwargs) -> None:
        """Initialize the explicit specification.

        :param filename: Path to the requirements file
        :param kwargs: Additional arguments
        """
        self.filename = filename

    def can_handle(self) -> bool:
        """
        Validates that this spec can process the environment definition.
        This checks if:
            * a filename was provided
            * the file has the "@EXPLICIT" marker

        :return: True if the file can be handled, False otherwise
        """
        # Return early if no filename was provided
        if self.filename is None:
            return False

        # Ensure the file has the "@EXPLICIT" marker
        dependencies_list = list(yield_lines(self.filename))
        if EXPLICIT_MARKER in dependencies_list:
            return True
        else:
            return False

    @property
    def env(self) -> Environment:
        """
        Build an environment from the explicit file.

        :return: An Environment object containing the package specifications
        :raises ValueError: If the file cannot be read
        """
        if not self.filename:
            raise CondaValueError("No filename provided")

        # Convert generator to list since Dependencies needs to access it multiple times
        dependencies_list = list(yield_lines(self.filename))
        explicit_packages = get_package_records_from_explicit(dependencies_list)

        return Environment(
            prefix=context.target_prefix,
            platform=context.subdir,
            explicit_packages=explicit_packages,
        )
