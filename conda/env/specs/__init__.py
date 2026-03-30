# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

from ...base.context import context
from ...exceptions import (
    EnvironmentSpecPluginNotDetected,
    SpecNotFound,
)

if TYPE_CHECKING:
    from .requirements import RequirementsSpec
    from .yaml_file import YamlFileSpec

    FileSpecTypes = type[YamlFileSpec] | type[RequirementsSpec]
    SpecTypes = YamlFileSpec | RequirementsSpec


def detect(filename: str | None = None) -> SpecTypes:
    """
    Return the appropriate spec type to use.

    :raises SpecNotFound: Raised if no suitable spec class could be found given the input
    """
    try:
        spec_hook = context.plugin_manager.detect_environment_specifier(
            source=filename,
        )
    except EnvironmentSpecPluginNotDetected as e:
        raise SpecNotFound(e.message)

    return spec_hook.environment_spec(filename)
