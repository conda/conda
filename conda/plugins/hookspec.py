# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Pluggy hook specifications ("hookspecs") to register conda plugins.

Each hookspec defined in :class:`~conda.plugins.hookspec.CondaSpecs` contains
an example of how to use it.

"""
from __future__ import annotations

from collections.abc import Iterable

import pluggy

from .types import (
    CondaAuthHandler,
    CondaPostCommand,
    CondaPreCommand,
    CondaSolver,
    CondaSubcommand,
    CondaVirtualPackage,
)

spec_name = "conda"
"""Name used for organizing conda hook specifications"""

_hookspec = pluggy.HookspecMarker(spec_name)
"""
The conda plugin hook specifications, to be used by developers
"""

hookimpl = pluggy.HookimplMarker(spec_name)
"""
Decorator used to mark plugin hook implementations
"""


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

        :return: An iterable of solver entries.
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
        Register pre-command functions in conda.

        **Example:**

        .. code-block:: python

           from conda import plugins


           def example_pre_command(command):
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
    def conda_post_commands(self) -> Iterable[CondaPostCommand]:
        """
        Register post-command functions in conda.

        **Example:**

        .. code-block:: python

           from conda import plugins


           def example_post_command(command):
               print("post-command action")


           @plugins.hookimpl
           def conda_post_commands():
               yield CondaPostCommand(
                   name="example-post-command",
                   action=example_post_command,
                   run_for={"install", "create"},
               )
        """

    @_hookspec
    def conda_auth_handlers(self) -> Iterable[CondaAuthHandler]:
        """
        Register a conda auth handler derived from the requests API.

        This plugin hook allows attaching requests auth handler subclasses,
        e.g. when authenticating requests against individual channels hosted
        at HTTP/HTTPS services.

        **Example:**

        .. code-block:: python

            import os
            from conda import plugins
            from requests.auth import AuthBase


            class EnvironmentHeaderAuth(AuthBase):
                def __init__(self, *args, **kwargs):
                    self.username = os.environ["EXAMPLE_CONDA_AUTH_USERNAME"]
                    self.password = os.environ["EXAMPLE_CONDA_AUTH_PASSWORD"]

                def __call__(self, request):
                    request.headers["X-Username"] = self.username
                    request.headers["X-Password"] = self.password
                    return request


            @plugins.hookimpl
            def conda_auth_handlers():
                yield plugins.CondaAuthHandler(
                    name="environment-header-auth",
                    auth_handler=EnvironmentHeaderAuth,
                )
        """
