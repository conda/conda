# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Conda-flavored installer."""

import tempfile
from typing import Iterable
from os.path import basename

from boltons.setutils import IndexedSet

from ...base.constants import UpdateModifier
from ...base.context import context
from ...common.constants import NULL
from ...exceptions import UnsatisfiableError
from ...models.channel import Channel, prioritize_channels
from ...plugins.types import InstallerBase


class NativeInstaller(InstallerBase):
    def __init__(self, **kwargs):
        pass

    def _solve(self, prefix, specs):
        """Solve the environment"""
        channel_urls = context.channels
        _channel_priority_map = prioritize_channels(channel_urls)

        channels = IndexedSet(Channel(url) for url in _channel_priority_map)
        subdirs = IndexedSet(basename(url) for url in _channel_priority_map)

        solver_backend = context.plugin_manager.get_cached_solver_backend()
        solver = solver_backend(prefix, channels, subdirs, specs_to_add=specs)
        return solver

    def install(self, prefix, specs, *args, **kwargs) -> Iterable[str]:
        """Install packages into an environment"""
        solver = self._solve(prefix, specs)

        try:
            unlink_link_transaction = solver.solve_for_transaction(
                update_modifier=UpdateModifier.FREEZE_INSTALLED,
            )
        except (UnsatisfiableError, SystemExit):
            unlink_link_transaction = solver.solve_for_transaction(
                update_modifier=NULL
            )

        if unlink_link_transaction.nothing_to_do:
            return None
        unlink_link_transaction.download_and_extract()
        unlink_link_transaction.execute()
        return unlink_link_transaction._make_legacy_action_groups()[0]

    def dry_run(self, prefix, specs, *args, **kwargs) -> Iterable[str]:
        """Do a dry run of the environment solve"""
        solver = self._solve(tempfile.mkdtemp(), specs)
        pkgs = solver.solve_final_state()
        return [str(p) for p in pkgs]
