# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Define cep-0024 compliant YAML spec."""

from __future__ import annotations

import os
from logging import getLogger
from typing import TYPE_CHECKING

from ...common.serialize import yaml_safe_load
from ...exceptions import CondaError
from ...plugins.types import EnvironmentSpecBase
from .. import env

if TYPE_CHECKING:
    from ...models.environment import Environment


log = getLogger(__name__)


class Cep24YamlFileSpec(EnvironmentSpecBase):
    _environment = None
    extensions = {".yaml", ".yml"}

    def __init__(self, filename: str | None = None, **kwargs):
        self.filename = filename

    def can_handle(self):
        """
        Validates loader can process environment definition.
        This can handle if:
            * the provided file exists
            * the provided file ends in the supported file extensions (.yaml or .yml)
            * the provided file is compliant with the CEP-0024

        :return: True or False
        """
        if not self.filename:
            return False

        # Extract the file extension (e.g., '.txt' or '' if no extension)
        _, file_ext = os.path.splitext(self.filename)

        # Check if the file has a supported extension and exists
        if file_ext.lower() not in self.extensions:
            return False

        try:
            yamlstr = env.load_file(self.filename)
            data = yaml_safe_load(yamlstr)
            errors = env.get_schema_errors(data)
            if errors:
                return False
            return True
        except CondaError:
            log.debug("Failed to load %s as a YAML.", self.filename, exc_info=True)
            return False

    @property
    def env(self) -> Environment:
        if not self._environment:
            self._environment = env.from_file(self.filename)
        return self._environment.to_environment_model()
