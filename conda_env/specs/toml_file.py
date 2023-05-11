# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os

from ..env import Environment


class TomlSpec:
    """Reads dependencies from a ``pyproject.toml`` file
    and returns an :class:`Environment` object from it.

    Note that this doesn't install the project described by the
    ``pyproject.toml`` file itself, but only its dependencies.

    Because the dependencies are expected to be conform to PEP 508,
    rather than conda's syntax, they are all added as ``pip``
    dependencies.

    """

    msg = None
    extensions = {".toml"}

    def __init__(self, filename=None, name=None, **kwargs):
        self.filename = filename
        self.name = name
        self.msg = None

    def _valid_file(self):
        if os.path.exists(self.filename):
            return True

        self.msg = f"File {self.filename} does not exist"
        return False

    def _valid_name(self):
        if self.name is None:
            self.msg = "Environment with pyproject.toml file needs a name"
            return False

        return True

    def can_handle(self):
        return self._valid_file() and self._valid_name()

    @property
    def environment(self):
        import tomli

        with open(self.filename, "rb") as f:
            dependencies = tomli.load(f)["project"]["dependencies"]
        return Environment(name=self.name, dependencies=["pip", {"pip": dependencies}])
