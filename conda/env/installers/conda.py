# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Conda-flavored installer."""

from __future__ import annotations

import logging
import tempfile
from os.path import basename
from typing import TYPE_CHECKING

from boltons.setutils import IndexedSet

from ...base.constants import UpdateModifier
from ...base.context import context
from ...common.constants import NULL
from ...env.env import Environment
from ...exceptions import CondaValueError, UnsatisfiableError
from ...gateways.disk.read import yield_lines
from ...models.channel import Channel, prioritize_channels

if TYPE_CHECKING:
    from argparse import Namespace

    from ...core.solve import Solver


def _solve(
    prefix: str, specs: list, args: Namespace, env: Environment, *_, **kwargs
) -> Solver:
    """Solve the environment.

    :param prefix: Installation target directory
    :param specs: Package specifications to install
    :param args: Command-line arguments
    :param env: Environment object
    :return: Solver object
    """
    # TODO: support all various ways this happens
    # Including 'nodefaults' in the channels list disables the defaults
    channel_urls = [chan for chan in env.channels if chan != "nodefaults"]

    if "nodefaults" not in env.channels:
        channel_urls.extend(context.channels)
    _channel_priority_map = prioritize_channels(channel_urls)

    channels = IndexedSet(Channel(url) for url in _channel_priority_map)
    subdirs = IndexedSet(basename(url) for url in _channel_priority_map)

    solver_backend = context.plugin_manager.get_cached_solver_backend()
    if solver_backend is None:
        raise CondaValueError("No solver backend found")
    solver = solver_backend(prefix, channels, subdirs, specs_to_add=specs)
    return solver


def dry_run(
    specs: list, args: Namespace, env: Environment, *_, **kwargs
) -> Environment:
    """Do a dry run of the environment solve.

    :param specs: Package specifications to install
    :param args: Command-line arguments
    :param env: Environment object
    :return: Solved environment object
    :rtype: Environment
    """
    solver = _solve(tempfile.mkdtemp(), specs, args, env, *_, **kwargs)
    pkgs = solver.solve_final_state()
    return Environment(
        name=env.name, dependencies=[str(p) for p in pkgs], channels=env.channels
    )


def install(
    prefix: str, specs: list, args: Namespace, env: Environment, *_, **kwargs
) -> dict | None:
    """Install packages into a conda environment.

    This function handles two main paths:
    1. For environments with explicit_specs (from @EXPLICIT files): Bypasses the solver
       and directly installs packages using conda.misc.explicit() as required by CEP-23.
    2. For regular Environment instances: Uses the solver to determine the optimal
       package set before installation.

    :param prefix: The target installation path for the environment
    :type prefix: str
    :param specs: Package specifications to install
    :type specs: list
    :param args: Command-line arguments from the conda command
    :type args: Namespace
    :param env: Environment object containing dependencies and channels
    :type env: Environment
    :return: Installation result information
    :rtype: dict

    .. note::
        This implementation follows CEP-23, which states: "When an explicit input file is
        processed, the conda client SHOULD NOT invoke a solver."
    """
    # Handle explicit environments separately per CEP-23 requirements
    if env.dependencies.explicit:
        from ...misc import explicit

        log = logging.getLogger(__name__)

        # Use verbose output if not in quiet mode
        verbose = not context.quiet

        # Determine which package specs to use (priority order):
        explicit_specs = None
        filename = env.filename

        # 1. Try to read from original file if available (most reliable source)
        if filename:
            explicit_specs = list(yield_lines(filename))
            if explicit_specs:
                log.debug(f"Using package specs from explicit file: {filename}")
            else:
                log.warning(f"Could not read explicit file {filename} or file is empty")

        # 2-3. Fall back to provided specs or dependencies from environment
        if not explicit_specs:
            explicit_specs = specs if specs else env.dependencies.raw
            log_msg = (
                "Using specs provided to installer"
                if specs
                else "Using dependencies from environment"
            )
            log.debug(log_msg)

        # Install using explicit() - bypassing the solver completely
        return explicit(explicit_specs, prefix, verbose=verbose)

    # For regular environments, proceed with the normal solve-based installation
    solver = _solve(prefix, specs, args, env, *_, **kwargs)

    try:
        unlink_link_transaction = solver.solve_for_transaction(
            prune=getattr(args, "prune", False),
            update_modifier=UpdateModifier.FREEZE_INSTALLED,
        )
    except (UnsatisfiableError, SystemExit) as exc:
        # See this comment for 'allow_retry' details
        # https://github.com/conda/conda/blob/b4592e9eb0/conda/cli/install.py#L417-L429
        if not getattr(exc, "allow_retry", True):
            raise
        unlink_link_transaction = solver.solve_for_transaction(
            prune=getattr(args, "prune", False), update_modifier=NULL
        )
    # Execute the transaction and return success
    if unlink_link_transaction.nothing_to_do:
        return None

    unlink_link_transaction.download_and_extract()
    unlink_link_transaction.execute()
    return unlink_link_transaction._make_legacy_action_groups()[0]
