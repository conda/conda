# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import Callable, NamedTuple

from ..core.solve import Solver


class CondaSubcommand(NamedTuple):
    """
    A conda subcommand.

    :param name: Subcommand name (e.g., ``conda my-subcommand-name``).
    :param summary: Subcommand summary, will be shown in ``conda --help``.
    :param action: Callable that will be run when the subcommand is invoked.
    """

    name: str
    summary: str
    action: Callable[
        [list[str]],  # arguments
        int | None,  # return code
    ]


class CondaVirtualPackage(NamedTuple):
    """
    A conda virtual package.

    :param name: Virtual package name (e.g., ``my_custom_os``).
    :param version: Virtual package version (e.g., ``1.2.3``).
    :param version: Virtual package build string (e.g., ``x86_64``).
    """

    name: str
    version: str | None
    build: str | None


class CondaSolver(NamedTuple):
    """
    A conda solver.

    :param name: Solver name (e.g., ``custom-solver``).
    :param backend: Type that will be instantiated as the solver backend.
    """

    name: str
    backend: type[Solver]


class CondaPreRun(NamedTuple):
    """
    Allows a plugin hook to execute before an invoked conda command is run.

    :param name: Pre-run command name (e.g., ``custom_plugin_pre_run``).
    :param action: Callable which contains the code to be run.
    :param run_for: Represents the command(s) this will be run on (e.g. install or create).
    """

    name: str
    action: Callable
    run_for: str


class CondaPostRun(NamedTuple):
    """
    Allows a plugin hook to execute after an invoked conda command is run.

    :param name: Post-run command name (e.g., ``custom_plugin_post_run``).
    :param action: Callable which contains the code to be run.
    :param run_for: Represents the command(s) this will be run on (e.g. install or create).
    """

    name: str
    action: Callable
    run_for: str


class CondaOnException(NamedTuple):
    """
    Runs when an exception is raised while a conda command is invoked.

    :param name: On-exception command name (e.g., ``custom_plugin_on_exception``).
    :param action: Callable which contains the code to be run.
    """

    name: str
    action: Callable
