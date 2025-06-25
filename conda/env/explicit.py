# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Explicit environment implementation for conda."""

from __future__ import annotations

from .env import Environment


class ExplicitEnvironment(Environment):
    """
    A specialized Environment class for explicit environments.

    This class represents environments created from @EXPLICIT files that should
    bypass the solver according to CEP-23.
    """

    def __init__(
        self,
        name: str = None,
        dependencies: list[str] = None,
        channels: list[str] = None,
        prefix: str = None,
        filename: str = None,
        **kwargs,
    ):
        """
        Initialize an explicit environment.

        Parameters
        ----------
        name : str, optional
            The name of the environment
        dependencies : List[str], optional
            The list of package specifications (URLs in this case)
        channels : List[str], optional
            The list of channels
        prefix : str, optional
            The installation prefix
        filename : str, optional
            The path to the explicit file this environment was created from
        """
        super().__init__(
            name=name,
            dependencies=dependencies,
            channels=channels,
            prefix=prefix,
            filename=filename,
            **kwargs,
        )
        self.explicit_specs = dependencies or []
        self.explicit_filename = filename
