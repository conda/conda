# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Define requirements.txt spec."""

import os

from ...deprecations import deprecated
from ..env import Environment
from . import BaseEnvSpec


class RequirementsSpec(BaseEnvSpec):
    """
    Reads dependencies from a requirements.txt file
    and returns an Environment object from it.
    """

    msg = None
    extensions = {".txt"}

    @deprecated.argument("24.7", "25.1", "name")
    def __init__(self, filename=None, name=None, **kwargs):
        self.filename = filename
        self._name = name  # UNUSED
        self.msg = None

    @property
    @deprecated("24.7", "25.1", addendum="This attribute is not used anymore.")
    def name(self):
        return self._name

    @name.setter
    @deprecated("24.7", "25.1", addendum="This attribute is not used anymore.")
    def name(self, value):
        self._name = value

    @deprecated("24.7", "25.1", addendum="This method is not used anymore.")
    def _valid_file(self):
        if os.path.exists(self.filename):
            return True
        else:
            self.msg = "There is no requirements.txt"
            return False

    @deprecated("24.7", "25.1", addendum="This method is not used anymore.")
    def _valid_name(self):
        if self.name is None:
            return False
        else:
            return True

    def can_handle(self):
        return os.path.exists(self.filename)

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
