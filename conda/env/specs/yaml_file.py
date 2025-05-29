# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Define YAML spec."""

from ruamel.yaml.error import YAMLError

from ...exceptions import EnvironmentFileEmpty, EnvironmentFileNotFound
from ...plugins.types import EnvironmentSpecBase
from .. import env


class YamlFileSpec(EnvironmentSpecBase):
    _environment = None
    extensions = {".yaml", ".yml", ".json"}  # Add JSON support since JSON ⊆ YAML

    def __init__(self, filename=None, **kwargs):
        self.filename = filename
        self.msg = None

    def can_handle(self):
        """
        Validates loader can process environment definition.
        This can handle if:
            * the env file can be interpreted and transformed into
              a `conda.env.env.Environment`

        :return: True or False
        """
        try:
            self._environment = env.from_file(self.filename)
            return True
        except EnvironmentFileNotFound as e:
            self.msg = str(e)
            return False
        except EnvironmentFileEmpty as e:
            self.msg = e.message
            return False
        except (TypeError, YAMLError):
            self.msg = f"{self.filename} is not a valid yaml or json file."
            return False

    def environment(self) -> env.Environment:
        if not self._environment:
            if not self.can_handle():
                raise ValueError(f"Cannot handle environment file: {self.msg}")
        if self._environment is None:
            raise ValueError("Environment could not be loaded")
        return self._environment
