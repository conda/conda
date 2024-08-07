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
    from ..models.environment import Environment
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
    cli_env = Environment(
        name=args.name,
        prefix=args.prefix,
        requirements=specs,
        validate=False,
    )

    file_envs = []
    if args.file:
        for path in args.file:
            input_file = detect_input_file(name=cli_env.name or "_", filename=path)
            file_envs.append(_conda_env_to_environment(input_file))

    env = Environment.merge(cli_env, *file_envs)
    if env.exists():
        existing_env = Environment.from_prefix(env.prefix)
        env = Environment.merge(existing_env, env)

    if context.dry_run:
        print(json.dumps(env.to_dict(), indent=2, default=str))
        return 0

    if env.solver_options.explicit:
        # invoke explicit solve and obtain transaction
        transaction = ...
    else:
        if env.prefix.exists():
            existing_env = Environment.from_prefix(env.prefix)
            env = Environment.merge(env, existing_env)
        # invoke the solver loop and obtain transaction
        transaction = ...

    # Handle transaction; maybe add here the environment directory creation and stuff
    handle_txn(transaction, env.prefix, args, not env.prefix.exists())


def _conda_env_to_environment(parsed) -> Environment:
    from ..models.environment import Environment

    return Environment(
        name=parsed.name if parsed.name != "_" else None,
        channels=parsed.environment.channels,
        requirements=parsed.environment.dependencies.get("conda", []),
        variables=parsed.environment.variables or {},
        validate=False,
    )
