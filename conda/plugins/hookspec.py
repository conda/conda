# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

from collections.abc import Iterable

import pluggy

from .types import CondaSolver, CondaSubcommand, CondaVirtualPackage, CondaSession

spec_name = "conda"
_hookspec = pluggy.HookspecMarker(spec_name)
hookimpl = pluggy.HookimplMarker(spec_name)


class CondaSpecs:
    """
    The conda plugin hookspecs, to be used by developers.
    """

    @_hookspec
    def conda_solvers(self) -> Iterable[CondaSolver]:
        """
        Register solvers in conda.

        :return: An iterable of solvers entries.

        Example:

        .. code-block:: python

            from conda import plugins
            from conda.core import solve


            class VerboseSolver(solve.Solver):
                def solve_final_state(self, *args, **kwargs):
                    log.info("My verbose solver!")
                    return super().solve_final_state(*args, **kwargs)


            @plugins.hookimpl
            def conda_solvers():
                yield plugins.CondaSolver(
                    name="verbose-classic",
                    backend=VerboseSolver,
                )

        """

    @_hookspec
    def conda_subcommands(self) -> Iterable[CondaSubcommand]:
        """
        Register external subcommands in conda.

        :return: An iterable of subcommand entries.

        Example:

        .. code-block:: python

            from conda import plugins


            def example_command(args):
                print("This is an example command!")


            @plugins.hookimpl
            def conda_subcommands():
                yield plugins.CondaSubcommand(
                    name="example",
                    summary="example command",
                    action=example_command,
                )

        """

    @_hookspec
    def conda_virtual_packages(self) -> Iterable[CondaVirtualPackage]:
        """
        Register virtual packages in Conda.

        :return: An iterable of virtual package entries.

        Example:

        .. code-block:: python

            from conda import plugins


            @plugins.hookimpl
            def conda_virtual_packages():
                yield plugins.CondaVirtualPackage(
                    name="my_custom_os",
                    version="1.2.3",
                )

        """

    @_hookspec
    def conda_session_classes(self) -> Iterable[CondaSession]:
        """
        Register session classes in conda. This session be a sub-class
        of ``requests.Session`` to maintain compatibility. This could also
        just directly subclass ``conda.gateways.connection.session.CondaSession``.

        :return: An iterable of conda session classes

        Example:

        .. code-block:: python

            from conda import plugins
            from requests import Session


            class MyCustomSession(Session):
                def __init__(self, *args, **kwargs):
                    self.custom_param = "custom-name"


            @plugins.hookimpl
            def conda_session_classes():
                yield plugins.CondaSession(
                    name="my-custom-session",
                    session=MyCustomSession,
                )
        """
