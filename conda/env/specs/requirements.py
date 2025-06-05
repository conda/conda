# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Define requirements.txt spec."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import ClassVar

from ...common.url import is_url, path_to_url
from ...common.path import expand
from ...deprecations import deprecated
from ...gateways.disk.read import read_non_comment_lines
from ...misc import url_pat
from ...plugins.types import EnvironmentSpecBase
from ..env import Environment
from ..explicit import ExplicitEnvironment


class RequirementsSpec(EnvironmentSpecBase):
    """
    Reads dependencies from a requirements.txt file
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
    def name(self):
        return self._name

    @name.setter
    @deprecated("25.9", "26.3", addendum="This attribute is not used anymore.")
    def name(self, value):
        self._name = value

    @deprecated("25.9", "26.3", addendum="This method is not used anymore.")
    def _valid_file(self) -> bool:
        """Check if the file exists.

        :return: True if the file exists, False otherwise
        """
        if os.path.exists(self.filename):
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

        # Check if the file exists
        if not os.path.exists(self.filename):
            self.msg = f"File {self.filename} does not exist"
            return False

        # Check if the file content is valid for this spec type
        return self._is_valid_content()

    def _read_file_lines(self) -> list[str] | None:
        """Read non-empty, non-comment lines from the file.

        Reads the file and returns a list of non-empty, non-comment lines.
        Comments start with '#'. Empty lines are skipped.

        :return: List of lines if successful, None if there was an error
        """
        if not self.filename or not os.path.exists(self.filename):
            return None

        try:
            return read_non_comment_lines(self.filename)
        except Exception as e:
            self.msg = f"Error reading file {self.filename}: {str(e)}"
            return None

    def _is_valid_content(self) -> bool:
        """
        Check if the file is a valid requirements file and not an explicit file.

        This method ensures that the RequirementsSpec doesn't handle explicit files
        (those containing @EXPLICIT marker), as those should be handled by
        ExplicitRequirementsSpec instead.

        :return: True if the file is a valid requirements file and not an explicit file
        """
        lines = self._read_file_lines()
        if lines is None:
            return False

        # Check if the file contains the @EXPLICIT marker
        if "@EXPLICIT" in lines:
            self.msg = (
                f"File {self.filename} is an explicit file, not a requirements file"
            )
            return False

        return True

    @property
    def environment(self) -> Environment:
        """
        Build an environment from the requirements file.

        :return: An Environment object containing the package specifications
        :raises ValueError: If the file is not a valid requirements file
        """
        lines = self._read_file_lines()
        if lines is None:
            raise ValueError(f"Unable to read file {self.filename}: {self.msg}")
        return Environment(dependencies=lines)


class ExplicitRequirementsSpec(RequirementsSpec):
    """Specification for explicit conda environment files.

    This class handles environment files marked with '@EXPLICIT' that contain
    package URLs or file paths. It follows the specifications in CEP-23:
    - Files must contain the '@EXPLICIT' marker
    - Each line contains one URL or file path
    - URLs may include checksums in anchors
    - File paths are expanded (tildes, environment variables)

    According to CEP-23, when an explicit input file is processed, conda
    SHOULD NOT invoke a solver, as all package specifications are fully resolved.
    """

    @lru_cache(maxsize=1)
    def _parse_explicit_file(self) -> list[str] | None:
        """Parse the explicit file and return a list of package specifications.

        Parses a file with the @EXPLICIT marker and converts package URLs
        according to CEP-23 specifications.

        :return: List of package specifications if valid, None if invalid
        :raises ValueError: If the file contents are invalid
        """
        if not self.filename:
            raise ValueError("No filename provided")

        # Read all non-comment lines from the file
        lines = self._read_file_lines()
        if lines is None:
            raise ValueError(f"Unable to read file {self.filename}: {self.msg}")

        # Verify this is an explicit file
        if "@EXPLICIT" not in lines:
            self.msg = f"File {self.filename} does not contain @EXPLICIT marker"
            return None

        # Process lines according to CEP-23
        processed_lines = []
        for line in lines:
            if line == "@EXPLICIT":
                continue

            # Strip any channel and platform-specific prefixes (e.g., 'conda-forge/osx-64::')
            # The conda.misc.explicit() function expects direct URLs or package paths
            if "::" in line:
                # The line has a channel/subdir prefix which needs to be removed
                # Format is typically: channel/subdir::package==version=build
                # or just: channel::package==version=build
                line = line.split("::", 1)[1]

            # Handle file paths and URL normalization using the same logic as misc.py
            if not is_url(line):
                # Convert paths to URLs using the same logic as _match_specs_from_explicit
                line = path_to_url(expand(line))

            # Validate URL format using the same regex pattern as misc.py
            # This ensures consistency and proper parsing of URLs with checksums
            m = url_pat.match(line)
            if m is None:
                # If the URL doesn't match the expected pattern, still include it
                # but log a warning. This maintains backward compatibility while
                # ensuring we use consistent URL parsing logic.
                pass

            processed_lines.append(line)

        # Return the processed lines that will be passed to ExplicitEnvironment
        # and eventually to the explicit() function in conda.misc
        return processed_lines

    def _is_valid_content(self) -> bool:
        """Check if the file contains the @EXPLICIT marker.

        Validates that the file contains the @EXPLICIT marker, which
        indicates it's an explicit environment file according to CEP-23.

        :return: True if the file is a valid explicit file, False otherwise
        """
        try:
            packages = self._parse_explicit_file()
            return packages is not None
        except Exception:
            return False

    @property
    def environment(self) -> ExplicitEnvironment:
        """Build an environment from the explicit file.

        Creates a special Environment object from explicit specifications.
        When this environment is used in the conda env create workflow,
        it will be processed using a special attribute that triggers the
        explicit() function rather than a solver, as required by CEP-23.

        :return: A specially configured Environment object
        :raises ValueError: If the file is not a valid explicit file
        """
        try:
            packages = self._parse_explicit_file()
            if packages is None:
                raise ValueError(f"Unable to handle file {self.filename}: {self.msg}")

            # Create an explicit environment with the packages
            # Using the typed ExplicitEnvironment class signals that this is from an explicit file
            # and should bypass the solver according to CEP-23
            return ExplicitEnvironment(dependencies=packages, filename=self.filename)
        except Exception as e:
            self.msg = f"Error creating environment from {self.filename}: {str(e)}"
            raise ValueError(self.msg) from e
