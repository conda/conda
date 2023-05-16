# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from collections.abc import Iterable

import pluggy

from .types import (
    CondaOnException,
    CondaPostCommand,
    CondaPreCommand,
    CondaSolver,
    CondaSubcommand,
    CondaVirtualPackage,
)

spec_name = "conda"
_hookspec = pluggy.HookspecMarker(spec_name)
hookimpl = pluggy.HookimplMarker(spec_name)


class CondaSpecs:
    """The conda plugin hookspecs, to be used by developers."""

    @_hookspec
    def conda_solvers(self) -> Iterable[CondaSolver]:
        """
        Register solvers in conda.

        Example:
        .. code-block:: python

            import logging

            from conda import plugins
            from conda.core import solve


            log = logging.getLogger(__name__)


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

        :return: An iterable of solvers entries.
        """

    @_hookspec
    def conda_subcommands(self) -> Iterable[CondaSubcommand]:
        """
        Register external subcommands in conda.

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

        :return: An iterable of subcommand entries.
        """

    @_hookspec
    def conda_virtual_packages(self) -> Iterable[CondaVirtualPackage]:
        """
        Register virtual packages in Conda.

        Example:
        .. code-block:: python

            from conda import plugins


            @plugins.hookimpl
            def conda_virtual_packages():
                yield plugins.CondaVirtualPackage(
                    name="my_custom_os",
                    version="1.2.3",
                    build="x86_64",
                )

        :return: An iterable of virtual package entries.
        """

    @_hookspec
    def conda_pre_commands(self) -> Iterable[CondaPreCommand]:
        """
        Register pre-run commands in conda.

        :return: An iterable of pre-run commands.

        Example:
        .. code-block:: python

            from conda import plugins


            PLUGIN_NAME = "custom_plugin"


            def custom_plugin_pre_commands_action():
                print("pre-command action")


            @plugins.hookimpl
            def conda_pre_commands():
                yield CondaPreRun(
                    name=f"{PLUGIN_NAME}_pre_commands",
                    action=custom_plugin_pre_commands_action,
                    run_for={"install", "create"},
                )
        """

    @_hookspec
    def conda_post_commands(self) -> Iterable[CondaPostCommand]:
        """
        Register post-run commands in conda.

        :return: An iterable of post-run commands.

        Example:
        .. code-block:: python

            from conda import plugins


            PLUGIN_NAME = "custom_plugin"


            def custom_plugin_post_commands_action():
                print("post-command action")


            @plugins.hookimpl
            def conda_post_commands():
                yield CondaPostCommands(
                    name=f"{PLUGIN_NAME}_post_commands",
                    action=custom_plugin_post_commands_action,
                    run_for={"install", "create"},
                )
        """

    @_hookspec
    def conda_on_exception(self) -> Iterable[CondaOnException]:
        """
        Register commands in conda that run on exception.

        :return: An iterable of on-exception commands.

        Example:
        .. code-block:: python

            from conda import plugins


            PLUGIN_NAME = "custom_plugin"


            def custom_plugin_on_exception_action():
                print("on_exception action")


            @hookimpl
            def conda_on_exception():
                yield CondaOnException(
                    name=f"{PLUGIN_NAME}_on_exception", action=custom_plugin_on_exception_action
                )
        """
