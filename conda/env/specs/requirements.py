# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Define requirements.txt spec."""

import os

from ...deprecations import deprecated
from ...plugins.types import EnvironmentSpecifierBase
from ..env import Environment


class RequirementsSpec(EnvironmentSpecifierBase):
    """
    Reads dependencies from a requirements.txt file
    and returns an Environment object from it.
    """

    msg = None
    extensions = {".txt"}

    @deprecated.argument("24.7", "26.3", "name")
    def __init__(self, filename=None, **kwargs):
        self.filename = filename
        self._name = name  # UNUSED
        self.msg = None

    @property
    @deprecated("25.9", "26.3", addendum="This attribute is not used anymore.")
    def name(self):
        return self._name

    @name.setter
    @deprecated("25.9", "26.3", addendum="This attribute is not used anymore.")
    def name(self, value):
        self._name = value

    @deprecated("25.9", "26.3", addendum="This method is not used anymore.")
    def _valid_file(self):
        if os.path.exists(self.filename):
            return True
        else:
            self.msg = "There is no requirements.txt"
            return False

    @deprecated("25.9", "26.3", addendum="This method is not used anymore.")
    def _valid_name(self):
        if self.name is None:
            return False
        else:
            return True

    def can_handle(self) -> bool:
        """
        Validates loader can process environment definition.
        This can handle if:
            * the provided file ends in the supported file extensions (.txt)
            * the file exists

        :return: True if the file can be parsed and handled, False otherwise
        """
        for ext in RequirementsSpec.extensions:
            if self.filename.endswith(ext) and os.path.exists(self.filename):
                return True

        return False

    @property
    def environment(self):
        dependencies = []
        with open(self.filename) as reqfile:
            for line in reqfile:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                dependencies.append(line)
        return Environment(dependencies=dependencies)
