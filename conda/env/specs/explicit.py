# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Define explicit file spec for conda environment files."""

from __future__ import annotations

import os
from functools import lru_cache
from os.path import expanduser, expandvars
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import ClassVar

from ...common.url import path_to_url
from ...misc import _match_specs_from_explicit
from ..env import Environment
from .base import TextSpecFileBase


class ExplicitFileSpec(TextSpecFileBase):
    """
    Specification for explicit conda environment files.

    This class handles environment files marked with '@EXPLICIT' that contain
    package URLs or file paths. It follows the specifications in CEP-23:
    - Files must contain the '@EXPLICIT' marker
    - Each line contains one URL or file path
    - URLs may include checksums in anchors
    - File paths are expanded (tildes, environment variables)

    The class leverages existing conda functionality to parse and validate
    package URLs, and creates an Environment object with the parsed specifications.

    :ivar extensions: Supported file extensions
    :ivar filename: Path to the environment file
    :ivar msg: Error message if validation fails
    """

    extensions: ClassVar[set[str]] = {".txt"}

    @lru_cache(maxsize=1)
    def _parse_explicit_file(self) -> list[str] | None:
        """
        Parse the explicit file and return a list of package specifications.

        :return: List of package specifications if the file is a valid explicit file
        :return: None if the file is invalid or cannot be parsed
        :raises ValueError: If the file contents are invalid
        """
        if not self.filename:
            raise ValueError("No filename provided")

        try:
            # Read all non-comment lines from the file
            with open(self.filename, encoding="utf-8") as f:
                lines = [
                    line.strip()
                    for line in f
                    if line.strip() and not line.strip().startswith("#")
                ]

            # Verify this is an explicit file
            if "@EXPLICIT" not in lines:
                self.msg = f"File {self.filename} does not contain @EXPLICIT marker"
                return None

            # Process lines according to CEP-23
            processed_lines = []
            for line in lines:
                if line == "@EXPLICIT":
                    continue

                # Handle file paths by expanding variables and converting to URLs
                if not line.startswith(("http://", "https://", "file://")):
                    line = expanduser(expandvars(line))
                    if os.path.isabs(line) and not line.startswith("file://"):
                        line = path_to_url(line)

                processed_lines.append(line)

            # Parse and validate URLs using conda's existing functionality
            try:
                return [str(url) for url in _match_specs_from_explicit(processed_lines)]
            except Exception as e:
                self.msg = f"Error parsing explicit file: {e}"
                return None

        except Exception as e:
            self.msg = f"Error processing {self.filename}: {str(e)}"
            raise ValueError(self.msg) from e

    def _is_valid_content(self) -> bool:
        """
        Check if the file contains the @EXPLICIT marker.

        :return: True if the file is a valid explicit file, False otherwise
        """
        try:
            packages = self._parse_explicit_file()
            return packages is not None
        except Exception:
            return False

    @property
    def environment(self) -> Environment:
        """
        Build an environment from the explicit file.

        :return: An Environment object containing the package specifications
        :raises ValueError: If the file is not a valid explicit file
        """
        try:
            packages = self._parse_explicit_file()
            if packages is None:
                raise ValueError(f"Unable to handle file {self.filename}: {self.msg}")
            return Environment(dependencies=packages)
        except Exception as e:
            self.msg = f"Error creating environment from {self.filename}: {str(e)}"
            raise ValueError(self.msg) from e
