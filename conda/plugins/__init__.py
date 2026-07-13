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

- :mod:`conda.plugins.previews`: aggregator for opt-in preview features
- :mod:`conda.plugins.solvers`: implementation of the "classic" solver
- :mod:`conda.plugins.subcommands.doctor`: ``conda doctor`` and ``conda check`` subcommands (with ``--fix`` support)
- :mod:`conda.plugins.virtual_packages`: registers virtual packages in conda

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..deprecations import deprecated
from .hookspec import hookimpl

if TYPE_CHECKING:
    from types import ModuleType

__all__ = ["hookimpl"]


def _load_types() -> ModuleType:
    return __import__("conda.plugins.types", fromlist=["types"])


# ``deprecated.constant`` installs its own registry as module ``__getattr__``,
# so the 16 deprecated re-exports still warn on access.
for name in (
    "CondaAuthHandler",
    "CondaEnvironmentSpecifier",
    "CondaHealthCheck",
    "CondaPostCommand",
    "CondaPostSolve",
    "CondaPostTransactionAction",
    "CondaPreCommand",
    "CondaPrefixDataLoader",
    "CondaPreSolve",
    "CondaPreTransactionAction",
    "CondaReporterBackend",
    "CondaRequestHeader",
    "CondaSetting",
    "CondaSolver",
    "CondaSubcommand",
    "CondaVirtualPackage",
):
    deprecated.constant(
        "26.3",
        "26.9",
        name,
        factory=lambda n=name: getattr(_load_types(), n),
        addendum=f"Use `conda.plugins.types.{name}` instead.",
    )
del name
