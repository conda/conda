# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Base class for conda env spec plugins
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..env import Environment


class BaseEnvSpec:
    """
    Base class for all env spec plugins.

    :param extensions: Filename extensions the class is able to handle, if any.
                       Only required for resources represented by a file.
    """
    msg: str | None = None
    extensions: list[str] = ()

    def __init__(self, filename=None):
        """Create a EnvSpec.

        :param filename: file that describes the environment.
        """
        pass

    def can_handle(self) -> bool:
        """Determines if the EnvSpec plugin can read and operate on the
        environment described by the `filename`.

        :returns bool: returns True, if the plugin can interpret the file.
        """
        raise NotImplementedError

    @property
    def environment(self) -> Environment:
        """Express the provided environment file as a conda environment object.

        :returns Environment: the conda environment represented by the file.
        """
        raise NotImplementedError
