# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Define YAML spec."""

from __future__ import annotations

from logging import getLogger
from typing import TYPE_CHECKING

from ...common.serialize import yaml
from ...exceptions import CondaValueError, PluginError
from ...plugins.types import EnvironmentSpecBase
from .. import env

if TYPE_CHECKING:
    from ...models.environment import Environment

log = getLogger(__name__)


class YamlFileSpec(EnvironmentSpecBase):
    # Do not use this plugin for in the environment spec detection process.
    # Users must specify using `environment.yaml` with the `--environment-specifier`
    # option.
    detection_supported = False

    _environment = None

    def __init__(self, filename=None, **kwargs):
        self.filename = filename
        self.msg = None

    def can_handle(self):
        """
        Validates loader can process environment definition.
        This can handle if:
            * the provided file exists
            * the yaml file can be loaded and is not empty

        Returns:
            True or False
        """
        if self.filename is None:
            raise CondaValueError("No filename provided")

        yamlstr = env.load_file(self.filename)
        data = yaml.loads(yamlstr)
        # We check for dict in order to avoid loading flat files as YAML.
        # The standard really wants a nested dict structure.
        if data is None or not isinstance(data, dict):
            raise PluginError(f"{self.filename} is an empty yaml file.")

        return True

    @property
    def env(self) -> Environment:
        if not self._environment:
            self._environment = env.from_file(self.filename)
        return self._environment.to_environment_model()
