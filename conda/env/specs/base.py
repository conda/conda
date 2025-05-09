# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Define base spec class for environment specifiers."""

from __future__ import annotations

import os

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import ClassVar

from ...plugins.types import EnvironmentSpecBase


class TextSpecFileBase(EnvironmentSpecBase):
    """
    Base class for text-based environment specification files.

    This class implements the common functionality for handling text-based specification
    files as defined in `CEP-23 <https://conda.org/learn/ceps/cep-0023>`_.

    Key features include:
    - File existence checks
    - Extension validation
    - Content validation
    - Error messaging

    Subclasses must implement:
    - extensions: a set of supported file extensions (e.g., {".txt", ".yml"})
    - _is_valid_content: a method that checks if the file content is valid for this spec

    .. note::
        This class is designed to support both explicit and non-explicit specification
        files as defined in CEP-23.

    .. versionadded:: 25.5

    .. seealso::
        - :class:`ExplicitFileSpec`: For handling explicit specification files
        - :class:`RequirementsSpec`: For handling requirements.txt files

    """

    extensions: ClassVar[set[str]] = (
        set()
    )  # Subclasses must override with supported extensions

    def __init__(self, filename=None, **kwargs):
        self.filename = filename
        self.msg = None

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

    def _is_valid_content(self) -> bool:
        """
        Checks if the file content is valid for this environment specifier.

        :return: True if the content is valid, False otherwise
        """
        # Subclasses should override this method
        raise NotImplementedError("Subclasses must implement _is_valid_content()")
