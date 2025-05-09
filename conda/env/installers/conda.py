# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Conda-flavored installer."""

import logging
import os
import tempfile
from os.path import basename

from boltons.setutils import IndexedSet

from ...base.constants import UpdateModifier
from ...base.context import context
from ...env.env import Environment
from ...env.explicit import ExplicitEnvironment
from ...exceptions import UnsatisfiableError
from ...models.channel import Channel, prioritize_channels


def _solve(prefix, specs, args, env, *_, **kwargs):
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
    solver = solver_backend(prefix, channels, subdirs, specs_to_add=specs)
    return solver


def dry_run(specs, args, env, *_, **kwargs):
    """Do a dry run of the environment solve.

    :param specs: Package specifications to install
    :param args: Command-line arguments
    :param env: Environment object
    :return: Solved environment object
    :rtype: Environment
    """
    solver = _solve(tempfile.mkdtemp(), specs, args, env, *_, **kwargs)
    pkgs = solver.solve_final_state()
    solved_env = Environment(
        name=env.name, dependencies=[str(p) for p in pkgs], channels=env.channels
    )
    return solved_env


def install(prefix: str, specs: list, args, env, *_, **kwargs) -> dict:
    """Install packages into a conda environment.

    This function handles two main paths:
    1. For ExplicitEnvironment instances (from @EXPLICIT files): Bypasses the solver
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
    if isinstance(env, ExplicitEnvironment):
        return _install_explicit_environment(prefix, specs, env)

    # For regular environments, proceed with the normal solve-based installation
    solver = _solve(prefix, specs, args, env, *_, **kwargs)

    try:
        unlink_link_transaction = solver.solve_for_transaction(
            prune=getattr(args, "prune", False),
            update_modifier=UpdateModifier.FREEZE_INSTALLED,
        )
    except (UnsatisfiableError, SystemExit) as exc:
        # Handle solver errors (original code continues here)
        raise exc

    return _execute_transaction(unlink_link_transaction)


def _install_explicit_environment(
    prefix: str, specs: list, env: ExplicitEnvironment
) -> dict:
    """
    Install packages from an explicit environment without using the solver.

    Implements CEP-23 requirement to bypass the solver for explicit environments.

    :param prefix: Installation target directory
    :type prefix: str
    :param specs: Package specifications to install
    :type specs: list
    :param env: Environment with explicit package URLs
    :type env: ExplicitEnvironment
    :return: Installation result from explicit()
    :rtype: dict
    """
    from ...misc import explicit

    log = logging.getLogger(__name__)

    # Use verbose output if not in quiet mode
    verbose = not getattr(context, "quiet", False)

    # Determine which package specs to use (priority order):
    explicit_specs = None
    filename = env.explicit_filename

    # 1. Try to read from original file if available (most reliable source)
    if filename and os.path.exists(filename):
        try:
            with open(filename) as f:
                explicit_specs = [
                    line.strip()
                    for line in f
                    if line.strip() and not line.strip().startswith("#")
                ]
            log.debug(f"Using package specs from explicit file: {filename}")
        except OSError as e:
            log.warning(f"Could not read explicit file {filename}: {e}")

    # 2-3. Fall back to provided specs or parsed specs from environment
    if not explicit_specs:
        explicit_specs = specs if specs else env.explicit_specs
        log_msg = (
            "Using specs provided to installer"
            if specs
            else "Using specs from environment"
        )
        log.debug(log_msg)

    # Install using explicit() - bypassing the solver completely
    return explicit(explicit_specs, prefix, verbose=verbose)


def _execute_transaction(transaction):
    """Execute a conda transaction after it has been solved.

    :param transaction: Transaction object to execute
    :return: Success status dictionary
    :rtype: dict
    """
    if transaction.nothing_to_do:
        return {"success": True}

    # Execute the transaction and return success
    transaction._make_legacy_action_groups()  # This processes the action groups
    transaction.download_and_extract()
    transaction.execute()
    return {"success": True}
