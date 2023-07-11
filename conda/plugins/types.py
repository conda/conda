# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Definition of specific return types for use when defining a conda plugin hook.

Each type corresponds to the plugin hook for which it is used.

"""
from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import dataclass, field
from typing import Callable, NamedTuple

from ..core.solve import Solver


def _not_implemented_configure_parser(parser: ArgumentParser) -> None:
    raise NotImplementedError


@dataclass
class CondaSubcommand:
    """
    Return type to use when defining a conda subcommand plugin hook.

    For details on how this is used, see
    :meth:`~conda.plugins.hookspec.CondaSpecs.conda_subcommands`.

    :param name: Subcommand name (e.g., ``conda my-subcommand-name``).
    :param summary: Subcommand summary, will be shown in ``conda --help``.
    :param setup: Callable that will be run when the subcommand parser is set up.
    :param action: Callable that will be run when the subcommand is invoked.
    """

    name: str
    summary: str
    action: Callable[
        [list[str]],  # arguments
        int | None,  # return code
    ]
    configure_parser: Callable[[ArgumentParser], None] = field(
        default=_not_implemented_configure_parser
    )


class CondaVirtualPackage(NamedTuple):
    """
    Return type to use when defining a conda virtual package plugin hook.

    For details on how this is used, see
    :meth:`~conda.plugins.hookspec.CondaSpecs.conda_virtual_packages`.

    :param name: Virtual package name (e.g., ``my_custom_os``).
    :param version: Virtual package version (e.g., ``1.2.3``).
    :param version: Virtual package build string (e.g., ``x86_64``).
    """

    name: str
    version: str | None
    build: str | None


class CondaSolver(NamedTuple):
    """
    Return type to use when defining a conda solver plugin hook.

    For details on how this is used, see
    :meth:`~conda.plugins.hookspec.CondaSpecs.conda_solvers`.

    :param name: Solver name (e.g., ``custom-solver``).
    :param backend: Type that will be instantiated as the solver backend.
    """

    name: str
    backend: type[Solver]


class CondaPreCommand(NamedTuple):
    """
    Return type to use when defining a conda pre-command plugin hook.

    For details on how this is used, see
    :meth:`~conda.plugins.hookspec.CondaSpecs.conda_pre_commands`.

    :param name: Pre-command name (e.g., ``custom_plugin_pre_commands``).
    :param action: Callable which contains the code to be run.
    :param run_for: Represents the command(s) this will be run on (e.g. ``install`` or ``create``).
    """

    name: str
    action: Callable[[str], None]
    run_for: set[str]


class CondaPostCommand(NamedTuple):
    """
    Return type to use when defining a conda post-command plugin hook.

    For details on how this is used, see
    :meth:`~conda.plugins.hookspec.CondaSpecs.conda_post_commands`.

    :param name: Post-command name (e.g., ``custom_plugin_post_commands``).
    :param action: Callable which contains the code to be run.
    :param run_for: Represents the command(s) this will be run on (e.g. ``install`` or ``create``).
    """

    name: str
    action: Callable[[str], None]
    run_for: set[str]
