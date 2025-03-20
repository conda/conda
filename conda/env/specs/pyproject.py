# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Define pyproject.toml spec."""

from __future__ import annotations

import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    from tomllib import TOMLDecodeError
    from tomllib import load as toml_load

from ...common.serialize import yaml_safe_dump
from .. import env


class PyProjectSpec:
    """Reads dependencies from a ``pyproject.toml`` file
    and returns an :class:`Environment` object from it.

    Initially only specification of dependencies in a
    ``[tool.conda.environment]`` table is supported until
    PEP-735 (https://peps.python.org/pep-0735/) or a
    suitable replacement is approved to indicate how
    arbitrary lists of dependencies may be included in a
    ``pyproject.toml`` file.

    The environment specification is read from ``[tool.conda.environment]``.
    The structure of the ``[tool.conda.environment]`` table
    and the syntax of the dependency specifications should
    be identical to that used for a standard ``environment.yml``
    file, with YAML syntax simply translated to TOML.
    For maximum compatibility, the parsed TOML table is simply
    converted to YAML and passed to the normal YAML parser.

    Additionally, if ``[[dependency-groups]]`` contains a dependency group
    (https://peps.python.org/pep-0735/) called ``conda-pip``, it will also be
    installed as if it were in the normal environment table under the pip
    dependencies, with the addition that `pip` will also be automatically
    added to the dependencies list if not already listed.
    """

    extensions = {".toml"}

    def __init__(self, filename: str, name: str | None = None, **kwargs):
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
            toml.get("tool", {}).get("conda", {}).get("environment", None)
        )
        if environment_table is None:
            self.msg = (
                f"{self.filename} does not contain a [tool.conda.environment] table."
            )
            print(self.msg)
            return False
        # Look for pip dependencies that conda should read
        pip_deps = toml.get("dependency-groups", {}).get("conda-pip", None)
        if pip_deps:
            if "dependencies" not in environment_table:
                environment_table["dependencies"] = []
            if "pip" not in [dep[:3] for dep in environment_table["dependencies"]]:
                environment_table["dependencies"].append("pip")
            environment_table["dependencies"].append({"pip": pip_deps})
        # Check the [project] table for a name if one wasn't passed as an argument
        # A name given in the environment table will still be used preferentially though
        if self.name is None and "project" in toml:
            try:
                # Supporting this is kind of abuse of what the [project] table is for,
                # but if we don't have any other name to go with then using one from
                # here is better than throwing an error
                # A [project] table is not actually mandatory for a pyproject.toml that
                # is not designed to be built and distributed, but if it is present, it
                # must have entries for a name and a version to be valid
                self.name = toml["project"]["name"]
            except KeyError:
                self.msg = f"{self.filename} is not a valid pyproject.toml file, as a [project] table is invalid without name and version fields."
                print(self.msg)
                return False
        try:
            environment_yaml = yaml_safe_dump(environment_table)
        except Exception as e:
            self.msg = f"The [tool.conda.environment] table could not be converted to valid YAML: {e}"
            print(self.msg)
            return False
        try:
            self._environment = env.from_yaml(environment_yaml)
            return True
        except Exception as e:
            self.msg = f"The [tool.conda.environment] table could not be processed as an environment.yml file: {e}"
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
