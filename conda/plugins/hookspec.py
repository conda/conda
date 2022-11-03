# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

from collections.abc import Iterable

import pluggy

from ..models.plugins import CondaSubcommand, CondaVirtualPackage

spec_name = "conda"
_hookspec = pluggy.HookspecMarker(spec_name)
hookimpl = pluggy.HookimplMarker(spec_name)


class CondaSpecs:

    @_hookspec
    def conda_subcommands() -> Iterable[CondaSubcommand]:
        """
        Register external subcommands in conda.

        :return: An iterable of subcommand entries.

        Example:

        .. code-block:: python

            from conda import plugins
            from conda.models.plugins import CondaSubcommand


            def example_command(args):
                print("This is an example command!")


            @plugins.hookimpl
            def conda_subcommands(self):
                yield CondaSubcommand(
                    name="example",
                    summary="example command",
                    action=example_command,
                )
        """

    @_hookspec
    def conda_virtual_packages() -> Iterable[CondaVirtualPackage]:
        """
        Register virtual packages in Conda.

        :return: An iterable of virtual package entries.

        Example:

        .. code-block:: python

            from conda import plugins
            from conda.models.plugins import CondaVirtualPackage


            @plugins.hookimpl
            def conda_virtual_packages(self):
                yield CondaVirtualPackage(
                    name="my_custom_os",
                    version="1.2.3",
                )

        """
