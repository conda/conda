# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Define YAML spec."""

from __future__ import annotations

import os
from logging import getLogger
from typing import TYPE_CHECKING

from ...common.serialize import yaml_safe_load
from ...deprecations import deprecated
from ...exceptions import CondaValueError
from ...plugins.types import EnvironmentSpecBase
from .. import env

if TYPE_CHECKING:
    from ...models.environment import Environment
    from ..env import EnvironmentYaml


log = getLogger(__name__)


class YamlFileSpec(EnvironmentSpecBase):
    # Do not use this plugin for in the environment spec detection process.
    # Users must specify using `environment.yaml` with the `--environment-specifier`
    # option.
    detection_supported = False

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
            * the yaml file can be loaded and is not empty

        :return: True or False
        """
        if not self.filename:
            return False

        # Extract the file extension (e.g., '.txt' or '' if no extension)
        _, file_ext = os.path.splitext(self.filename)

        # Check if the file has a supported extension and exists
        if not any(spec_ext == file_ext for spec_ext in YamlFileSpec.extensions):
            return False

        try:
            yamlstr = env.load_file(self.filename)
            data = yaml_safe_load(yamlstr)
            if data is None:
                return False
        except Exception:
            log.debug("Failed to load %s as a YAML.", self.filename, exc_info=True)
            return False

        return True

    @property
    @deprecated("26.3", "26.9", addendum="This method is not used anymore, use 'env'")
    def environment(self) -> EnvironmentYaml:
        if not self._environment:
            if not self.can_handle():
                raise CondaValueError(f"Cannot handle environment file: {self.msg}")
            self._environment = env.from_file(self.filename)

        if self._environment is None:
            raise CondaValueError("Environment could not be loaded")
        return self._environment

    @property
    def env(self) -> Environment:
        if not self._environment:
            self._environment = env.from_file(self.filename)
        return self._environment.to_environment_model()
