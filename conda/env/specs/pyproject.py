# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Define pyproject.toml spec."""

import os
from pathlib import Path
import sys
from typing import Union

if sys.version_info >= (3, 11):
    from tomllib import TOMLDecodeError
    from tomllib import load as toml_load

from .. import env
from ...common.serialize import yaml_safe_dump


class PyProjectSpec:
    """Reads dependencies from a ``pyproject.toml`` file
    and returns an :class:`Environment` object from it.
    
    Initially only specification of dependencies in a
    ``[tool.conda.environment]`` table is supported until
    PEP-735 (https://peps.python.org/pep-0735/) or a
    suitable replacement is approved to indicate how
    arbitrary lists of dependencies may be included in a
    ``pyproject.toml`` file.

    The structure of a ``[tool.conda.environment]`` table
    and the syntax of the dependency specifications should
    be identical to that used for a standard ``environment.yml``
    file, with YAML syntax simply translated to TOML.
    For maximum compatibility, the parsed TOML table is simply
    converted to YAML and passed to the normal YAML parser.
    """

    extensions = {".toml"}

    def __init__(self, filename: os.PathLike, name: Union[str, None] = None, **kwargs):
        self.filename: Path = Path(filename)
        self.name: str = name
        self._environment = None
        self.msg = None

    def _valid_file(self):
        if self.filename.exists():
            return True
        else:
            self.msg = f"File {self.filename} does not exist."
            return False

    def can_handle(self):
        if not self._valid_file():
            print("Invalid file")
            return False
        try:
            with open(self.filename, "rb") as f:
                toml = toml_load(f)
        except NameError:
            self.msg = "Reading from TOML files is only supported from Python >=3.11"
            print(self.msg)
            return False
        except TOMLDecodeError as e:
            self.msg = f"{self.filename} is not a valid TOML file: {e}"
            print(self.msg)
            return False
        environment_table = (
            toml
            .get("tool", {})
            .get("conda", {})
            .get("environment", None)
        )
        if environment_table is None:
            self.msg = f"{self.filename} does not contain a [tool.conda.environment] table."
            print(self.msg)
            return False
        # Check the [project] table for a name if one wasn't passed as an argument
        # A name given in the environment table will still be used preferentially though
        if self.name and "project" in toml:
            try:
                # Supporting this is kind of abuse of what the [project] table is for,
                # but if we don't have any other name to go with then using one from
                # here is better than throwing an error
                # A [project] table is not actually mandatory for a pyproject.toml that
                # is not designed to be built and distributed, but if it is present, it
                # must have entries for a name and a version to be valid
                self.name = toml["project"]["name"]
            except KeyError:
                self.msg = (
                    f"{self.filename} is not a valid pyproject.toml file, as a [project] table is invalid without name and version fields."
                )
                print(self.msg)
                return False
        try:
            environment_yaml = yaml_safe_dump(environment_table)
        except Exception as e:
            self.msg = (
                f"The [tool.conda.environment] table could not be converted to valid YAML: {e}"
            )
            print(self.msg)
            return False
        try:
            self._environment = env.from_yaml(environment_yaml)
            return True
        except Exception as e:
            self.msg = (
                f"The [tool.conda.environment] table could not be processed as an environment.yml file: {e}"
            )
            print(self.msg)
            return False

    @property
    def environment(self):
        if not self._environment:
            if not self.can_handle():
                print("Can't handle")
                return None
        # Make sure there's a name if at all possible
        if self._environment.name is None:
            self._environment.name = self.name
        return self._environment
