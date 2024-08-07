# Copyright (C) 2024 conda contributors
# SPDX-License-Identifier: BSD-3-Clause
"""Conda package installation logic, revisited.

Core logic for `conda [create|install|update|remove]` commands.

See conda.cli.main_create, conda.cli.main_install, conda.cli.main_update, and
conda.cli.main_remove for the entry points into this module.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import Namespace

    from ..models.environment import Environment


def install(args: Namespace, _, command: str) -> int:
    # Parse all inputs to build an Environment instance
    # Retrieve the necessary information from the Environment
    # Set up environment workspace or import if existing
    # Build explicit transactions
    # OR Build solver transactions
    # Handle transaction

    from ..base.context import context
    from ..env.specs import detect as detect_input_file
    from ..exceptions import (
        ArgumentError,
        CondaError,
        InvalidSpec,
        PackageNotInstalledError,
    )
    from ..models.environment import Environment, NeedsNameOrPrefix
    from ..models.match_spec import MatchSpec
    from .install import handle_txn

    # First, let's create an 'Environment' for the information exposed in the CLI (no files)
    specs = [MatchSpec(pkg) for pkg in args.packages]
    if command == "create" and not args.no_default_packages:
        names = {spec.name for spec in specs}
        for pkg in context.create_default_packages:
            spec = MatchSpec(pkg)
            if spec.name not in names:
                specs.append(spec)

    if command != "create" and not args.name and not args.prefix:
        name = None
        prefix = context.active_prefix
    else:
        name = args.name
        prefix = args.prefix
    cli_env = Environment(
        name=name,
        prefix=prefix,
        requirements=specs,
        validate=False,
    )

    file_envs = []
    if args.file:
        for path in args.file:
            # TODO: reimplement this conda.env part with a plugin system
            # that knows about conda.models.environment natively
            input_file = detect_input_file(name=cli_env.name or "_", filename=path)
            file_envs.append(_conda_env_to_environment(input_file))

    try:
        env = Environment.merge(cli_env, *file_envs)
    except NeedsNameOrPrefix:
        raise ArgumentError("one of the arguments -n/--name -p/--prefix is required")

    if env.exists():
        # TODO: If we changed the Solver logic, this merged environment could
        # hold all the information required to simply invoke the solution.
        # We will probably need to pass this _without_ the history.
        existing_env = Environment.from_prefix(env.prefix, load_history=False, load_pins=False)
        if command == "update":
            installed_names = {spec.name for spec in existing_env.installed()}
            for requirement in env.requirements:
                if not requirement.is_name_only_spec:
                    raise InvalidSpec(
                        f"Invalid spec: {requirement}.\n"
                        "'conda update' only accepts name-only specs. "
                        "Use 'conda install' to specify a constraint."
                    )
                if requirement.name not in installed_names:
                    raise PackageNotInstalledError(env.prefix, requirement)
        env = Environment.merge(existing_env, env)
    else:
        if command != "create":
            raise CondaError(f"'conda {command}' can only be used with existing environments.")
        # TODO: Create prefix (should this be part of the transaction system)

    if env.solver_options.explicit:
        if command == "update":
            raise CondaError("'conda update' doesn't support explicit changes.")
        # invoke explicit solve and obtain transaction
        transaction = explicit_transaction(env, args, command)
    else:
        # invoke the solver loop and obtain transaction
        transaction = solver_transaction(env, args, command)

    # TODO: temporary, just to see how the env looks like
    if True: # context.dry_run:
        print(json.dumps(env.to_dict(), indent=2, default=str))
        return 0

    # Handle transaction; maybe add here the environment directory creation and stuff
    handle_txn(transaction, env.prefix, args, not env.prefix.exists())
    # TODO: we also need to dump the Environment state into conda-meta, maybe as part
    # of the transaction system.


def _conda_env_to_environment(parsed) -> Environment:
    from ..models.environment import Environment

    return Environment(
        name=parsed.name if parsed.name != "_" else None,
        channels=parsed.environment.channels,
        requirements=parsed.environment.dependencies.get("conda", []),
        variables=parsed.environment.variables or {},
        validate=False,
    )


def explicit_transaction(environment: Environment, args: Namespace, command: str):
    ...


def solver_transaction(environment: Environment, args: Namespace, command: str):
    ...
