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
    """
    This helper function will collect all the different inputs from conda create/install/update
    and provide one of the following outcomes:

    1. Raise an error because the CLI was insufficient or invalid
    2. Clone an existing environment to a new one: 'conda create --clone'
    3. Process 'explicit' transactions (lockfiles, or if all specs are URLs or paths)
    4. Massage all the inputs for the solver, invoke the solver, and process the final transaction
    """
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
        NeedsNameOrPrefix,
        PackageNotInstalledError,
        TooManyArgumentsError,
    )
    from ..misc import touch_nonadmin
    from ..models.environment import Environment
    from ..models.match_spec import MatchSpec
    from .install import clone, handle_txn, print_activate

    index_args = {
        "use_cache": args.use_index_cache,
        "channel_urls": context.channels,
        "unknown": args.unknown,
        "prepend": not args.override_channels,
        "use_local": args.use_local,
    }

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

    # Environment cloning is an early exit task; we already have the necessary information
    if command == "create" and args.clone:
        if args.packages or args.file:
            raise TooManyArgumentsError(
                expected=0,
                received=len(args.packages) + len(args.file),
                offending_arguments=[*args.packages, *args.file],
                optional_message="did not expect any arguments for --clone",
            )
        clone(
            src_arg=args.clone,
            dst_prefix=cli_env.prefix,
            json=context.json,
            quiet=context.quiet,
            index_args=index_args,
        )
        touch_nonadmin(cli_env.prefix)
        print_activate(args.name or cli_env.prefix)
        return 0

    # Now let's process potential files passed via --file
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
        # For now, we need to pass this _without_ the history or pins.
        existing_env = Environment.from_prefix(
            env.prefix, load_history=False, load_pins=False
        )
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
            raise CondaError(
                f"'conda {command}' can only be used with existing environments."
            )
        # TODO: Create prefix (should this be part of the transaction system)

    if env.explicit:
        # invoke explicit solve and obtain transaction
        transaction = explicit_transaction(env, args, command)
    else:
        # invoke the solver loop and obtain transaction
        transaction = solver_transaction(env, args, command)

    # TODO: temporary, just to see how the env looks like
    if True:  # context.dry_run:
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
    from ..base.context import context
    from ..core.link import PrefixSetup, UnlinkLinkTransaction
    from ..core.package_cache_data import PackageCacheData, ProgressiveFetchExtract
    from ..exceptions import CondaExitZero, DryRunExit, SpecNotFound

    records_to_unlink = []
    specs_to_link = []
    if environment.exists():
        installed = {record.name: record for record in environment.installed()}
        for spec in environment.requirements:
            url = spec.get("url")
            if not url:
                raise ValueError(
                    "Explicit transactions require specs that define 'url'."
                )
            filename = url.split("/")[-1]
            if filename.lower().endswith(".conda"):
                basename = filename[:-6]
            elif filename.lower().endswith(".tar.bz2"):
                basename = filename[:-8]
            else:
                raise ValueError(f"Unsupported file extension: {filename}")
            name, version, build = basename.rsplit("-", 2)
            installed_record = installed.get(name)
            if installed_record:
                if installed_record.fn != filename:
                    records_to_unlink.append(installed_record)
                    specs_to_link.append(spec)
            else:
                specs_to_link.append(spec)

    if context.dry_run:
        raise DryRunExit()

    pfe = ProgressiveFetchExtract(specs_to_link)
    pfe.execute()

    if context.download_only:
        raise CondaExitZero(
            "Package caches prepared. "
            "UnlinkLinkTransaction cancelled with --download-only option."
        )

    # now make an UnlinkLinkTransaction with the PackageCacheRecords as inputs
    # need to add package name to fetch_specs so that history parsing keeps track of them correctly
    records_to_link = []
    specs_to_update = []
    specs_with_missing_record = []
    for spec in specs_to_link:
        record = next(PackageCacheData.query_all(spec), None)
        if record:
            records_to_link.append(record)
            specs_to_update(spec)
        else:
            specs_with_missing_record.append(spec)

    if specs_with_missing_record:
        raise SpecNotFound(
            f"Missing package cache records for: {', '.join(map(str, specs_with_missing_record))}"
        )

    stp = PrefixSetup(
        environment.prefix,
        records_to_unlink,
        records_to_link,
        (),
        specs_to_update,
        (),
    )

    return UnlinkLinkTransaction(stp)


def solver_transaction(environment: Environment, args: Namespace, command: str):
    ...