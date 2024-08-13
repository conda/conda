# Copyright (C) 2024 conda contributors
# SPDX-License-Identifier: BSD-3-Clause
"""Conda package installation logic, revisited.

Core logic for `conda [create|install|update|remove]` commands.

See conda.cli.main_create, conda.cli.main_install, conda.cli.main_update, and
conda.cli.main_remove for the entry points into this module.
"""

from __future__ import annotations

from logging import getLogger
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import Namespace
    from typing import Iterable

    from ..core.link import UnlinkLinkTransaction
    from ..models.environment import Environment

log = getLogger(__name__)


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
    from tempfile import mkdtemp

    from ..base.constants import REPODATA_FN, UpdateModifier
    from ..base.context import context
    from ..common.constants import NULL
    from ..common.path import paths_equal
    from ..env.specs import detect as detect_input_file
    from ..exceptions import (
        ArgumentError,
        CondaOSError,
        CondaValueError,
        DirectoryNotACondaEnvironmentError,
        EnvironmentLocationNotFound,
        InvalidSpec,
        NeedsNameOrPrefix,
        NoBaseEnvironmentError,
        PackageNotInstalledError,
    )
    from ..gateways.disk.create import mkdir_p
    from ..gateways.disk.delete import delete_trash, path_is_clean
    from ..misc import touch_nonadmin
    from ..models.environment import Environment
    from ..models.match_spec import MatchSpec
    from .common import check_non_admin
    from .install import check_prefix, clone, handle_txn, print_activate

    context.validate_configuration()
    check_non_admin()
    # this is sort of a hack.  current_repodata.json may not have any .tar.bz2 files,
    #    because it deduplicates records that exist as both formats.  Forcing this to
    #    repodata.json ensures that .tar.bz2 files are available
    if context.use_only_tar_bz2:
        log.info("use_only_tar_bz2 is true; overriding repodata_fns")
        args.repodata_fns = ("repodata.json",)

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

    repodata_fns = args.repodata_fns or list(context.repodata_fns)
    if REPODATA_FN not in repodata_fns:
        repodata_fns.append(REPODATA_FN)
    index_args = {
        "use_cache": args.use_index_cache,
        "channel_urls": context.channels,
        "unknown": args.unknown,
        "prepend": not args.override_channels,
        "use_local": args.use_local,
        "repodata_fn": repodata_fns[-1],  # default to latest (usually repodata.json)
    }

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
        if context.dry_run:
            cli_env.prefix = mkdtemp(prefix="unused-conda-env")
            env = Environment.merge(cli_env, *file_envs)
        else:
            raise ArgumentError(
                "one of the arguments -n/--name -p/--prefix is required"
            )

    if context.force_32bit and paths_equal(env.prefix, context.root_prefix):
        # TODO: Deprecate this setting?
        raise CondaValueError("cannot use CONDA_FORCE_32BIT=1 in base env")

    if command == "create":
        check_prefix(str(env.prefix), json=context.json)
        _check_subdir_override()
        if args.clone:
            _check_clone(args)
    elif env.exists():
        delete_trash(prefix)
        # TODO: If we changed the Solver logic, this merged environment could
        # hold all the information required to simply invoke the solution.
        # For now, we need to pass this _without_ the history or pins.
        existing_env = Environment.from_prefix(
            env.prefix, load_history=False, load_pins=False
        )
        if command == "update":
            installed_pkgs = list(existing_env.installed())
            if env.requirements:
                for requirement in env.requirements:
                    if not requirement.is_name_only_spec:
                        raise InvalidSpec(
                            f"Invalid spec for 'conda update': {requirement}.\n"
                            "'conda update' only accepts name-only specs. "
                            "Use 'conda install' to specify a constraint."
                        )
                    if not any(requirement.match(pkg) for pkg in installed_pkgs):
                        raise PackageNotInstalledError(env.prefix, requirement)
            elif context.update_modifier != UpdateModifier.UPDATE_ALL:
                raise CondaValueError(
                    "no package names supplied\n"
                    "# Example: conda update -n myenv scipy"
                )

        env = Environment.merge(existing_env, env)
    elif not (env.prefix / "conda-meta" / "history").is_file():
        if paths_equal(prefix, context.conda_prefix):
            raise NoBaseEnvironmentError()
        else:
            if not path_is_clean(prefix):
                raise DirectoryNotACondaEnvironmentError(prefix)
    elif getattr(args, "mkdir", False):
        # --mkdir is deprecated and marked for removal in conda 25.3
        try:
            mkdir_p(env.prefix)
        except OSError as e:
            raise CondaOSError(f"Could not create directory: {env.prefix}", caused_by=e)
    else:
        raise EnvironmentLocationNotFound(env.prefix)

    if getattr(args, "clone", False):
        # TODO: Make it return a transaction too, like explicit does
        clone(
            src_arg=args.clone,
            dst_prefix=env.prefix,
            json=context.json,
            quiet=context.quiet,
            index_args=index_args,
        )
        touch_nonadmin(env.prefix)
        print_activate(args.name or str(env.prefix))
        return 0
    elif getattr(args, "revision", None) not in (None, NULL):
        transaction = revision_transaction(env.prefix, args.revision, index_args)
    elif env.is_explicit():
        # invoke explicit solve and obtain transaction
        transaction = explicit_transaction(env, args, command)
    else:
        transaction = solver_transaction(env, args, command, index_args, repodata_fns)

    # Handle transaction; maybe add here the environment directory creation and stuff
    handle_txn(
        transaction,
        str(env.prefix),
        args,
        command == "create",
        variables=env.variables,
    )


def _conda_env_to_environment(parsed) -> Environment:
    from ..models.environment import Environment

    env = parsed.environment
    return Environment(
        name=env.name if env.name != "_" else None,
        channels=env.channels,
        requirements=[
            dep
            for dep in env.dependencies.get("conda", ())
            if str(dep).upper() != "@EXPLICIT"
        ],
        variables=env.variables or {},
        validate=False,
    )


def explicit_transaction(environment: Environment, args: Namespace, command: str):
    from ..base.context import context
    from ..core.link import PrefixSetup, UnlinkLinkTransaction
    from ..core.package_cache_data import PackageCacheData, ProgressiveFetchExtract
    from ..exceptions import CondaExitZero, DryRunExit, SpecNotFound

    if not environment.requirements:
        return UnlinkLinkTransaction(PrefixSetup(str(environment.prefix), (), (), (), (), ()))

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
    else:
        specs_to_link = environment.requirements

    pfe = ProgressiveFetchExtract(specs_to_link)

    if context.dry_run:
        raise DryRunExit()

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
            specs_to_update.append(spec)
        else:
            specs_with_missing_record.append(spec)

    if specs_with_missing_record:
        raise SpecNotFound(
            f"Missing package cache records for: {', '.join(map(str, specs_with_missing_record))}"
        )

    stp = PrefixSetup(
        str(environment.prefix),
        records_to_unlink,
        records_to_link,
        (),
        specs_to_update,
        (),
    )

    return UnlinkLinkTransaction(stp)


def solver_transaction(
    environment: Environment,
    args: Namespace,
    command: str,
    index_args: dict,
    repodata_fns: Iterable[str],
) -> UnlinkLinkTransaction:
    from ..base.context import context

    if context.solver == "classic":
        return _classic_solver_transaction(
            environment, args, command, index_args, repodata_fns
        )
    return _simple_solver_transaction(environment, args, command, repodata_fns)


def _classic_solver_transaction(
    environment: Environment,
    args: Namespace,
    command: str,
    index_args: dict,
    repodata_fns: Iterable[str],
) -> UnlinkLinkTransaction:
    """Loops through the repodata filenames and frozen/unfrozen modes til it succeeds."""
    from ..base.constants import DepsModifier, UpdateModifier
    from ..base.context import context
    from ..common.constants import NULL
    from ..core.index import calculate_channel_urls
    from ..exceptions import (
        CondaImportError,
        PackagesNotFoundError,
        ResolvePackageNotFound,
        SpecsConfigurationConflictError,
        UnsatisfiableError,
    )

    # This helps us differentiate between an update, the --freeze-installed option, and the retry
    # behavior in our initial fast frozen solve
    _should_retry_unfrozen = (
        hasattr(args, "update_modifier")
        and args.update_modifier
        not in (UpdateModifier.FREEZE_INSTALLED, UpdateModifier.UPDATE_SPECS, NULL)
    ) and environment.exists()

    for repodata_fn in repodata_fns:
        try:
            solver_backend = context.plugin_manager.get_cached_solver_backend()
            solver = solver_backend(
                environment.prefix,
                environment.channels,
                context.subdirs,
                specs_to_add=environment.requirements,
                repodata_fn=repodata_fn,
                command=command,
            )
            update_modifier = context.update_modifier
            if command == "install" and args.update_modifier == NULL:
                update_modifier = UpdateModifier.FREEZE_INSTALLED
            deps_modifier = context.deps_modifier
            if command == "update":
                deps_modifier = context.deps_modifier or DepsModifier.UPDATE_SPECS

            return solver.solve_for_transaction(
                deps_modifier=deps_modifier,
                update_modifier=update_modifier,
                force_reinstall=context.force_reinstall or context.force,
                should_retry_solve=(
                    _should_retry_unfrozen or repodata_fn != repodata_fns[-1]
                ),
            )

        except (ResolvePackageNotFound, PackagesNotFoundError) as e:
            # end of the line.  Raise the exception
            if repodata_fn == repodata_fns[-1]:
                # PackagesNotFoundError is the only exception type we want to raise.
                #    Over time, we should try to get rid of ResolvePackageNotFound
                if isinstance(e, PackagesNotFoundError):
                    raise e
                else:
                    channels_urls = tuple(
                        calculate_channel_urls(
                            channel_urls=index_args["channel_urls"],
                            prepend=index_args["prepend"],
                            platform=None,
                            use_local=index_args["use_local"],
                        )
                    )
                    # convert the ResolvePackageNotFound into PackagesNotFoundError
                    raise PackagesNotFoundError(e._formatted_chains, channels_urls)

        except (UnsatisfiableError, SystemExit, SpecsConfigurationConflictError) as e:
            # Quick solve with frozen env or trimmed repodata failed.  Try again without that.
            if not hasattr(args, "update_modifier"):
                if repodata_fn == repodata_fns[-1]:
                    raise e
            elif _should_retry_unfrozen:
                try:
                    return solver.solve_for_transaction(
                        deps_modifier=deps_modifier,
                        update_modifier=UpdateModifier.UPDATE_SPECS,
                        force_reinstall=context.force_reinstall or context.force,
                        should_retry_solve=(repodata_fn != repodata_fns[-1]),
                    )
                except (
                    UnsatisfiableError,
                    SystemExit,
                    SpecsConfigurationConflictError,
                ) as e:
                    # Unsatisfiable package specifications/no such revision/import error
                    if e.args and "could not import" in e.args[0]:
                        raise CondaImportError(str(e))
                    # we want to fall through without raising if we're not at the end of the list
                    #    of fns.  That way, we fall to the next fn.
                    if repodata_fn == repodata_fns[-1]:
                        raise e
            elif repodata_fn != repodata_fns[-1]:
                continue  # if we hit this, we should retry with next repodata source
            else:
                # end of the line.  Raise the exception
                # Unsatisfiable package specifications/no such revision/import error
                if e.args and "could not import" in e.args[0]:
                    raise CondaImportError(str(e))
                raise e


def _simple_solver_transaction(
    environment: Environment,
    args: Namespace,
    command: str,
    repodata_fns: Iterable[str],
) -> UnlinkLinkTransaction:
    """Loops through the repodata filenames, and only raises on the last one."""
    from ..base.constants import DepsModifier, UpdateModifier
    from ..base.context import context
    from ..common.constants import NULL
    from ..exceptions import (
        PackagesNotFoundError,
        ResolvePackageNotFound,
        SpecsConfigurationConflictError,
        UnsatisfiableError,
    )

    for repodata_fn in repodata_fns:
        try:
            solver_backend = context.plugin_manager.get_cached_solver_backend()
            solver = solver_backend(
                str(environment.prefix),
                environment.channels,
                context.subdirs,
                specs_to_add=environment.requirements,
                repodata_fn=repodata_fn,
                command=command,
            )
            update_modifier = context.update_modifier
            if command == "install" and args.update_modifier == NULL:
                update_modifier = UpdateModifier.FREEZE_INSTALLED
            deps_modifier = context.deps_modifier
            if command == "update":
                deps_modifier = context.deps_modifier or DepsModifier.UPDATE_SPECS

            return solver.solve_for_transaction(
                deps_modifier=deps_modifier,
                update_modifier=update_modifier,
                force_reinstall=context.force_reinstall or context.force,
            )
        except (
            ResolvePackageNotFound,
            PackagesNotFoundError,
            UnsatisfiableError,
            SystemExit,
            SpecsConfigurationConflictError,
        ) as e:
            if not getattr(e, "allow_retry", True):
                # TODO: This is a temporary workaround to allow downstream libraries
                # to inject this attribute set to False and skip the retry logic
                # Other solvers might implement their own internal retry logic without
                # depending --freeze-install implicitly like conda classic does. Example
                # retry loop in conda-libmamba-solver:
                # https://github.com/conda-incubator/conda-libmamba-solver/blob/da5b1ba/conda_libmamba_solver/solver.py#L254-L299
                # If we end up raising UnsatisfiableError, we annotate it with `allow_retry`
                # so we don't have go through all the repodatas and freeze-installed logic
                # unnecessarily (see https://github.com/conda/conda/issues/11294). see also:
                # https://github.com/conda-incubator/conda-libmamba-solver/blob/7c698209/conda_libmamba_solver/solver.py#L617
                raise e
            if repodata_fn == repodata_fns[-1]:  # last attempt, we raise
                raise e


def revision_transaction(prefix: str, revision: int, index_args: dict):
    from ..base.context import context
    from ..common.io import Spinner
    from ..core.index import get_index
    from .install import get_revision, revert_actions

    repodata_fn = index_args.get("repodata_fn", context.repodata_fns[-1])
    with Spinner(
        f"Collecting package metadata ({repodata_fn})",
        not context.verbose and not context.quiet,
        context.json,
    ):
        index = get_index(
            channel_urls=index_args["channel_urls"],
            prepend=index_args["prepend"],
            platform=None,
            use_local=index_args["use_local"],
            use_cache=index_args["use_cache"],
            unknown=index_args["unknown"],
            prefix=prefix,
            repodata_fn=repodata_fn,
        )
    revision_idx = get_revision(revision)
    with Spinner(
        f"Reverting to revision {revision_idx}",
        not context.verbose and not context.quiet,
        context.json,
    ):
        return revert_actions(str(prefix), revision_idx, index)


def _check_subdir_override():
    from ..auxlib.ish import dals
    from ..base.context import context
    from ..common.path import paths_equal
    from ..exceptions import OperationNotAllowed

    if context.subdir != context._native_subdir():
        # We will only allow a different subdir if it's specified by global
        # configuration, environment variable or command line argument. IOW,
        # prevent a non-base env configured for a non-native subdir from leaking
        # its subdir to a newer env.
        context_sources = context.collect_all()
        if context_sources.get("cmd_line", {}).get("subdir") == context.subdir:
            pass  # this is ok
        elif context_sources.get("envvars", {}).get("subdir") == context.subdir:
            pass  # this is ok too
        # config does not come from envvars or cmd_line, it must be a file
        # that's ok as long as it's a base env or a global file
        elif not paths_equal(context.active_prefix, context.root_prefix):
            # this is only ok as long as it's base environment
            active_env_config = next(
                (
                    config
                    for path, config in context_sources.items()
                    if paths_equal(context.active_prefix, path.parent)
                ),
                None,
            )
            if active_env_config.get("subdir") == context.subdir:
                # In practice this never happens; the subdir info is not even
                # loaded from the active env for conda create :shrug:
                msg = dals(
                    f"""
                    Active environment configuration ({context.active_prefix}) is
                    implicitly requesting a non-native platform ({context.subdir}).
                    Please deactivate first or explicitly request the platform via
                    the --platform=[value] command line flag.
                    """
                )
                raise OperationNotAllowed(msg)


def _check_clone(args: Namespace):
    from ..exceptions import TooManyArgumentsError

    if args.packages or args.file:
        raise TooManyArgumentsError(
            expected=0,
            received=len(args.packages) + len(args.file),
            offending_arguments=[*args.packages, *args.file],
            optional_message="did not expect any arguments for --clone",
        )
