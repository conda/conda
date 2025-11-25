# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
In this module, you will find everything relevant to conda's plugin system.
It contains all of the code that plugin authors will use to write plugins,
as well as conda's internal implementations of plugins.

**Modules relevant for plugin authors**

- :mod:`conda.plugins.hookspec`: all available hook specifications are listed here, including
  examples of how to use them
- :mod:`conda.plugins.types`: important types to use when defining plugin hooks

**Modules relevant for internal development**

- :mod:`conda.plugins.manager`: includes our custom subclass of pluggy's
  `PluginManager <https://pluggy.readthedocs.io/en/stable/api_reference.html#pluggy.PluginManager>`_ class

**Modules with internal plugin implementations**

- :mod:`conda.plugins.solvers`: implementation of the "classic" solver
- :mod:`conda.plugins.subcommands.doctor`: ``conda doctor`` subcommand
- :mod:`conda.plugins.virtual_packages`: registers virtual packages in conda

"""

from ..deprecations import deprecated
from . import types
from .hookspec import hookimpl

__all__ = ["hookimpl", "types"]

deprecated.constant(
    "26.3",
    "26.9",
    "CondaAuthHandler",
    types.CondaAuthHandler,
    addendum="Use `conda.plugins.types.CondaAuthHandler` instead.",
)
deprecated.constant(
    "26.3",
    "26.9",
    "CondaEnvironmentSpecifier",
    types.CondaEnvironmentSpecifier,
    addendum="Use `conda.plugins.types.CondaEnvironmentSpecifier` instead.",
)
deprecated.constant(
    "26.3",
    "26.9",
    "CondaHealthCheck",
    types.CondaHealthCheck,
    addendum="Use `conda.plugins.types.CondaHealthCheck` instead.",
)
deprecated.constant(
    "26.3",
    "26.9",
    "CondaPostCommand",
    types.CondaPostCommand,
    addendum="Use `conda.plugins.types.CondaPostCommand` instead.",
)
deprecated.constant(
    "26.3",
    "26.9",
    "CondaPostSolve",
    types.CondaPostSolve,
    addendum="Use `conda.plugins.types.CondaPostSolve` instead.",
)
deprecated.constant(
    "26.3",
    "26.9",
    "CondaPostTransactionAction",
    types.CondaPostTransactionAction,
    addendum="Use `conda.plugins.types.CondaPostTransactionAction` instead.",
)
deprecated.constant(
    "26.3",
    "26.9",
    "CondaPreCommand",
    types.CondaPreCommand,
    addendum="Use `conda.plugins.types.CondaPreCommand` instead.",
)
deprecated.constant(
    "26.3",
    "26.9",
    "CondaPrefixDataLoader",
    types.CondaPrefixDataLoader,
    addendum="Use `conda.plugins.types.CondaPrefixDataLoader` instead.",
)
deprecated.constant(
    "26.3",
    "26.9",
    "CondaPreSolve",
    types.CondaPreSolve,
    addendum="Use `conda.plugins.types.CondaPreSolve` instead.",
)
deprecated.constant(
    "26.3",
    "26.9",
    "CondaPreTransactionAction",
    types.CondaPreTransactionAction,
    addendum="Use `conda.plugins.types.CondaPreTransactionAction` instead.",
)
deprecated.constant(
    "26.3",
    "26.9",
    "CondaReporterBackend",
    types.CondaReporterBackend,
    addendum="Use `conda.plugins.types.CondaReporterBackend` instead.",
)
deprecated.constant(
    "26.3",
    "26.9",
    "CondaRequestHeader",
    types.CondaRequestHeader,
    addendum="Use `conda.plugins.types.CondaRequestHeader` instead.",
)
deprecated.constant(
    "26.3",
    "26.9",
    "CondaSetting",
    types.CondaSetting,
    addendum="Use `conda.plugins.types.CondaSetting` instead.",
)
deprecated.constant(
    "26.3",
    "26.9",
    "CondaSolver",
    types.CondaSolver,
    addendum="Use `conda.plugins.types.CondaSolver` instead.",
)
deprecated.constant(
    "26.3",
    "26.9",
    "CondaSubcommand",
    types.CondaSubcommand,
    addendum="Use `conda.plugins.types.CondaSubcommand` instead.",
)
deprecated.constant(
    "26.3",
    "26.9",
    "CondaVirtualPackage",
    types.CondaVirtualPackage,
    addendum="Use `conda.plugins.types.CondaVirtualPackage` instead.",
)
