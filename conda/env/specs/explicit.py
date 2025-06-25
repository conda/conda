# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Define explicit spec."""

from __future__ import annotations

from ...gateways.disk.read import yield_lines
from ...plugins.types import EnvironmentSpecBase
from ..env import Environment


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
        if "@EXPLICIT" in dependencies_list:
            return True
        else:
            return False

    @property
    def environment(self) -> Environment:
        """
        Build an environment from the explicit file.

        This method reads the file as a generator and passes it directly to Environment,
        which will automatically detect if it's an explicit file and set the appropriate flags.

        :return: An Environment object containing the package specifications
        :raises ValueError: If the file cannot be read
        """
        if not self.filename:
            raise ValueError("No filename provided")

        # Convert generator to list since Dependencies needs to access it multiple times
        dependencies_list = list(yield_lines(self.filename))
        return Environment(
            dependencies=dependencies_list,
            filename=self.filename,
        )
