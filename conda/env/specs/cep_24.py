# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Define cep-0024 compliant YAML spec."""

from __future__ import annotations

from logging import getLogger
from typing import TYPE_CHECKING

from ...common.io import dashlist
from ...common.serialize import yaml
from ...exceptions import CondaValueError, PluginError
from ...plugins.types import EnvironmentSpecBase
from .. import env

if TYPE_CHECKING:
    from ...models.environment import Environment


log = getLogger(__name__)


class Cep24YamlFileSpec(EnvironmentSpecBase):
    _environment = None

    def __init__(self, filename: str | None = None, **kwargs):
        self.filename = filename

    def can_handle(self):
        """
        Validates loader can process environment definition.
        This can handle if:
            * the provided file exists
            * the provided file is compliant with the CEP-0024

        :return: True if the file can be handled
        :raises: if the file can not be handled
        """
        if self.filename is None:
            raise CondaValueError("No filename provided")

        yamlstr = env.load_file(self.filename)
        data = yaml.loads(yamlstr)
        errors = env.get_schema_errors(data)
        if errors:
            raise PluginError(
                f"Provided environment file is invalid:{dashlist(errors, indent=8)}"
            )
        return True

    @property
    def env(self) -> Environment:
        if not self._environment:
            self._environment = env.from_file(self.filename)
        return self._environment.to_environment_model()
