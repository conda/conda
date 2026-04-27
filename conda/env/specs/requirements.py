# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Define requirements.txt spec."""

from __future__ import annotations

import os

from ...base.context import context
from ...common.url import is_url
from ...exceptions import CondaValueError, InvalidMatchSpec, PluginError
from ...gateways.disk.read import yield_lines
from ...models.environment import Environment
from ...models.match_spec import MatchSpec
from ...plugins.types import EnvironmentSpecBase


class RequirementsSpec(EnvironmentSpecBase):
    """
    Reads dependencies from requirements files (including explicit files)
    and returns an Environment object from it.
    """

    msg: str | None = None

    def __init__(self, filename: str | None = None, **kwargs) -> None:
        """Initialize the requirements specification.

        :param filename: Path to the requirements file
        :param kwargs: Additional arguments
        """
        self.filename = filename

    def can_handle(self) -> bool:
        """
        Validates that this spec can process the environment definition.
        This checks if:
            * a filename was provided
            * the file exists
            * the file content is valid for this specifier type

        :return: True if the file can be handled, False otherwise
        """
        # Return early if no filename was provided
        if self.filename is None:
            raise CondaValueError("No filename provided")

        if is_url(self.filename):
            raise CondaValueError(f"{self.filename} may not be a url")

        if not os.path.exists(self.filename):
            raise CondaValueError(f"{self.filename} does not exist")

        # Ensure this is not an explicit file. Requirements.txt and explicit files
        # may sometimes share file extension.
        dependencies_list = list(yield_lines(self.filename))
        for dep in dependencies_list:
            # Ensure the file is not an explicit file
            if dep == "@EXPLICIT":
                raise PluginError(f"{self.filename} is an explicit file.")
            # Ensure that every item is a valid matchspec
            try:
                MatchSpec(dep)
            except InvalidMatchSpec:
                raise PluginError(
                    f"{self.filename} contains an invalid matchspec '{dep}'"
                )

        return True

    @property
    def env(self) -> Environment:
        """
        Build an environment from the requirements file.

        :return: An Environment object containing the package specifications
        :raises ValueError: If the file cannot be read
        """
        if not self.filename:
            raise ValueError("No filename provided")

        # Convert generator to list since Dependencies needs to access it multiple times
        dependencies_list = list(yield_lines(self.filename))
        requested_packages = [MatchSpec(dep) for dep in dependencies_list]

        return Environment(
            platform=context.subdir,
            requested_packages=requested_packages,
        )
