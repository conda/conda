# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Define requirements.txt spec."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import ClassVar

from ...base.context import context
from ...deprecations import deprecated
from ...exceptions import CondaValueError
from ...gateways.disk.read import yield_lines
from ...models.environment import Environment
from ...models.match_spec import MatchSpec
from ...plugins.types import EnvironmentSpecBase
from ..env import EnvironmentYaml


class RequirementsSpec(EnvironmentSpecBase):
    """
    Reads dependencies from requirements files (including explicit files)
    and returns an Environment object from it.
    """

    msg: str | None = None
    extensions: ClassVar[set[str]] = {".txt"}

    @deprecated.argument("24.7", "26.3", "name")
    def __init__(
        self, filename: str | None = None, name: str | None = None, **kwargs
    ) -> None:
        """Initialize the requirements specification.

        :param filename: Path to the requirements file
        :param name: (Deprecated) Name of the environment
        :param kwargs: Additional arguments
        """
        self.filename = filename
        self._name = name

    @property
    @deprecated("25.9", "26.3", addendum="This attribute is not used anymore.")
    def name(self):  # type: ignore[misc]
        return self._name

    @name.setter  # type: ignore[misc]
    @deprecated("25.9", "26.3", addendum="This attribute is not used anymore.")
    def name(self, value):  # type: ignore[misc]
        self._name = value

    @deprecated("25.9", "26.3", addendum="This method is not used anymore.")
    def _valid_file(self) -> bool:
        """Check if the file exists.

        :return: True if the file exists, False otherwise
        """
        if self.filename and os.path.exists(self.filename):
            return True
        else:
            self.msg = "There is no requirements.txt"
            return False

    @deprecated("25.9", "26.3", addendum="This method is not used anymore.")
    def _valid_name(self) -> bool:
        """Check if the name is valid.

        :return: True if the name is valid, False otherwise
        """
        if self.name is None:
            self.msg = "The environment does not have a name"
            return False
        else:
            return True

    def can_handle(self) -> bool:
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
        if self.filename is None:
            return False

        # Extract the file extension (e.g., '.txt' or '' if no extension)
        _, file_ext = os.path.splitext(self.filename)

        # Check if the file has a supported extension
        if not any(spec_ext == file_ext for spec_ext in self.extensions):
            self.msg = f"File {self.filename} does not have a supported extension: {', '.join(self.extensions)}"
            return False

        # Ensure this is not an explicit file. Requirements.txt and explicit files
        # may sometimes share file extension.
        dependencies_list = list(yield_lines(self.filename))
        if "@EXPLICIT" in dependencies_list:
            return False
        return True

    @property
    @deprecated("26.3", "26.9", addendum="This method is not used anymore, use 'env'")
    def environment(self) -> EnvironmentYaml:
        """
        Build an environment from the requirements file.

        This method reads the file as a generator and passes it directly to EnvironmentYaml.

        :return: An Environment object containing the package specifications
        :raises ValueError: If the file cannot be read
        """
        if not self.filename:
            raise CondaValueError("No filename provided")

        # Convert generator to list since Dependencies needs to access it multiple times
        dependencies_list = list(yield_lines(self.filename))
        return EnvironmentYaml(
            dependencies=dependencies_list,
            filename=self.filename,
        )

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
            prefix=context.target_prefix,
            platform=context.subdir,
            requested_packages=requested_packages,
        )
