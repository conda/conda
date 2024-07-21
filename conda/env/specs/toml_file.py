# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Define .toml spec."""

import os
import sys

if sys.version_info >= (3, 11):
    from tomllib import TOMLDecodeError
    from tomllib import load as toml_load
else:
    from tomli import TOMLDecodeError
    from tomli import load as toml_load

from ..env import Environment


class TomlSpec:
    """Reads dependencies from a ``.toml`` file
    and returns an :class:`Environment` object from it.
    Note that this doesn't install the project described by the
    ``.toml`` file itself, but only its dependencies.
    Because the dependencies are expected to be conform to PEP 508,
    rather than conda's syntax.

    All dependencies all added as ``pip`` dependencies.
    One can only use this feature via explicitly writing
    `channel=[]` in [tool.conda] for compatibility reasons.
    See https://github.com/conda/conda/pull/12666#issuecomment-1628391662 for more information.
    """

    extensions = {".toml"}

    def __init__(self, filename=None, name=None, **kwargs):
        self.filename: str = filename
        self.name: str = name
        self._environment = None
        self.msg = None

    def _valid_file(self):
        # find the filename directly
        if os.path.exists(self.filename):
            return True

        self.msg = f"File {self.filename} does not exist"
        return False

    def can_handle(self):
        if not self._valid_file():
            return False

        try:
            with open(self.filename, "rb") as f:
                toml_file = toml_load(f)
                proj = toml_file.get("project", {})
                channels = (
                    toml_file.get("tool", {}).get("conda", {}).get("channels", None)
                )
                assert channels == []
        except AssertionError:
            self.msg = "So far, explicitly writing `channels=[]` in [tool.conda] is required to avoid compatibility hell."
            return False
        except TOMLDecodeError as e:
            self.msg = f"{self.filename} is not a valid toml file: {e}"
            return False
        except Exception as e:
            self.msg = f"An unknown error occured while reading {self.filename}: {e}"
            return False

        project_name = proj.get("name", None)
        dependencies = proj.get("dependencies", [])

        # if no name is provided, use the project name
        if self.name is None:
            self.name = project_name

        # still no name? then we can't proceed
        if self.name is None:
            self.msg = "Environment with pyproject.toml file needs a name"
            return False

        return Environment(name=self.name, dependencies=["pip", {"pip": dependencies}])

    @property
    def environment(self):
        if not self._environment:
            self._environment = self.can_handle()
        return self._environment
