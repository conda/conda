# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Define requirements.txt spec."""

import os

from ...deprecations import deprecated
from ..env import Environment
from .base import TextSpecFileBase


class RequirementsSpec(TextSpecFileBase):
    """
    Reads dependencies from a requirements.txt file
    and returns an Environment object from it.
    """

    msg = None
    extensions = {".txt"}

    @deprecated.argument("24.7", "26.3", "name")
    def __init__(self, filename=None, name=None, **kwargs):
        super().__init__(filename, **kwargs)
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

    def _is_valid_content(self) -> bool:
        """
        Requirements files don't need additional content validation beyond
        file extension and existence checks, which are done in the base class.

        :return: True always, since there's no specific format to check
        """
        return True

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
