# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import Callable, NamedTuple

from requests import Session

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
    """

    name: str
    version: str | None


class CondaSolver(NamedTuple):
    """
    A conda solver.

    :param name: Solver name (e.g., ``custom-solver``).
    :param backend: Type that will be instantiated as the solver backend.
    """

    name: str
    backend: type[Solver]


class CondaSessionClass(NamedTuple):
    """
    A conda session.

    :param name: Session name (e.g., ``basic-auth-session``). This name should be unique
                 and only one may be registered at a time.
    :param session: Type that will be instantiated as the conda session.
    """

    name: str
    session_class: type[Session]


class CondaBeforeAction(NamedTuple):
    """
    A before action.

    :param name: BeforeAction name (e.g., ``basic-auth-before-action``). This name should be unique
                 and only one may be registered at a time.
    :param action: Callable that will be executed during application start-up.
    :param run_for: The commands that this action should be run on; defaults to running on all
                    commands.
    """

    name: str
    action: Callable
    run_for: set[str, ...] | None = None
