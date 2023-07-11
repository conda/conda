# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from collections.abc import Iterable

import pluggy

from .types import (
    CondaPreCommand,
    CondaShellPlugins,
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

        **Example:**

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

        **Example:**

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

        **Example:**

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
        Register pre-commands functions in conda.

        **Example:**

        .. code-block:: python

           from conda import plugins


           def example_pre_command(command, args):
               print("pre-command action")


           @plugins.hookimpl
           def conda_pre_commands():
               yield CondaPreCommand(
                   name="example-pre-command",
                   action=example_pre_command,
                   run_for={"install", "create"},
               )
        """

    @_hookspec
    def conda_shell_plugins(self) -> Iterable[CondaShellPlugins]:
        r"""
        Register external shell plugins in conda.


        **Example:**

        .. code-block:: python

            import os
            from conda import plugins


            @plugins.hookimpl
            def conda_shell_plugins():
                yield plugins.CondaShellPlugins(
                    name="plugin_name",
                    summary="Conda shell plugin for example shell",
                    script_path=os.path.abspath("./posix_script.sh"),
                    pathsep_join=":".join,
                    sep="/",
                    path_conversion=some_function,
                    script_extension=".sh",
                    tempfile_extension=None,
                    command_join="\n",
                    run_script_tmpl='. "%s"',
                    unset_var_tmpl="unset %s",
                    export_var_tmpl="export %s='%s'",
                    set_var_tmpl="%s='%s'",
                )
        """
