# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Define YAML spec."""

import os
from logging import getLogger

from ...models.environment import Environment
from ...plugins.types import EnvironmentSpecBase
from .. import env

log = getLogger(__name__)


class YamlFileSpec(EnvironmentSpecBase):
    _environment = None
    extensions = {".yaml", ".yml"}

    def __init__(self, filename=None, **kwargs):
        self.filename = filename
        self.msg = None

    def can_handle(self):
        """
        Validates loader can process environment definition.
        This can handle if:
            * the provided file exists
            * the provided file ends in the supported file extensions (.yaml or .yml)
            * the env file can be interpreted and transformed into
              a `conda.env.env.Environment`

        :return: True or False
        """
        # Extract the file extension (e.g., '.txt' or '' if no extension)
        _, file_ext = os.path.splitext(self.filename)

        # Check if the file has a supported extension and exists
        if not any(spec_ext == file_ext for spec_ext in YamlFileSpec.extensions):
            return False

        try:
            self._environment = env.from_file(self.filename)
            return True
        except Exception:
            log.debug(
                "Failed to load %s as `environment.yaml`.", self.filename, exc_info=True
            )
            return False

    @property
    def environment(self) -> Environment:
        if not self._environment:
            self.can_handle()
        return self._environment.to_environment_model()
