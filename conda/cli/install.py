# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Conda package installation logic.

Core logic for `conda [create|install|update|remove]` commands.

See conda.cli.main_create, conda.cli.main_install, conda.cli.main_update, and
conda.cli.main_remove for the entry points into this module.
"""

from __future__ import annotations

import os
from logging import getLogger
from os.path import abspath, basename, exists, isdir, isfile, join
from pathlib import Path

from boltons.setutils import IndexedSet

from .. import CondaError
from ..auxlib.ish import dals
from ..base.constants import (
    PREFIX_MAGIC_FILE,
    REPODATA_FN,
    ROOT_ENV_NAME,
    DepsModifier,
    UpdateModifier,
)
from ..base.context import context, locate_prefix_by_name
from ..common.constants import NULL
from ..common.path import is_package_file, paths_equal
from ..core.index import (
    _supplement_index_with_prefix,
    calculate_channel_urls,
    get_index,
)
from ..core.link import PrefixSetup, UnlinkLinkTransaction
from ..core.prefix_data import PrefixData
from ..core.solve import diff_for_unlink_link_precs
from ..deprecations import deprecated
from ..exceptions import (
    CondaEnvException,
    CondaExitZero,
    CondaImportError,
    CondaIndexError,
    CondaSystemExit,
    CondaValueError,
    DirectoryNotACondaEnvironmentError,
    DirectoryNotFoundError,
    DryRunExit,
    EnvironmentLocationNotFound,
    NoBaseEnvironmentError,
    PackageNotInstalledError,
    PackagesNotFoundError,
    ResolvePackageNotFound,
    SpecsConfigurationConflictError,
    UnsatisfiableError,
)
from ..gateways.disk.delete import delete_trash, path_is_clean
from ..history import History
from ..misc import _get_best_prec_match, clone_env, explicit, touch_nonadmin
from ..models.match_spec import MatchSpec
from ..models.prefix_graph import PrefixGraph
from ..reporters import confirm_yn, get_spinner
from . import common
from .common import check_non_admin, validate_prefix_is_writable
from .main_config import set_keys

log = getLogger(__name__)
stderrlog = getLogger("conda.stderr")


def validate_prefix_exists(prefix: str | Path) -> None:
    """
    Validate that we are receiving at least one valid value for --name or --prefix.
    """
    prefix = Path(prefix)
    if not prefix.exists():
        raise CondaEnvException("The environment you have specified does not exist.")


def validate_new_prefix(dest: str, force: bool = False) -> str:
    """Ensure that the new prefix does not exist."""
    from ..base.context import context, validate_prefix_name
    from ..common.path import expand

    if os.sep in dest:
        dest = expand(dest)
    else:
        dest = validate_prefix_name(dest, ctx=context, allow_base=False)

    if not force and os.path.exists(dest):
        env_name = os.path.basename(os.path.normpath(dest))
        raise CondaEnvException(
            f"The environment '{env_name}' already exists. Override with --yes."
        )

    return dest


def check_prefix(prefix: str, json=False):
    if os.pathsep in prefix:
        raise CondaValueError(
            f"Cannot create a conda environment with '{os.pathsep}' in the prefix. Aborting."
        )
    name = basename(prefix)
    error = None
    if name == ROOT_ENV_NAME:
        error = f"'{name}' is a reserved environment name"
    if exists(prefix):
        if isdir(prefix) and "conda-meta" not in tuple(
            entry.name for entry in os.scandir(prefix)
        ):
            return None
        error = f"prefix already exists: {prefix}"

    if error:
        raise CondaValueError(error, json)

    if " " in prefix:
        stderrlog.warning(
            "WARNING: A space was detected in your requested environment path:\n"
            f"'{prefix}'\n"
            "Spaces in paths can sometimes be problematic. To minimize issues,\n"
            "make sure you activate your environment before running any executables!\n"
        )


def clone(src_arg, dst_prefix, json=False, quiet=False, index_args=None):
    if os.sep in src_arg:
        src_prefix = abspath(src_arg)
        if not isdir(src_prefix):
            raise DirectoryNotFoundError(src_arg)
    else:
        src_prefix = locate_prefix_by_name(src_arg)

    if not json:
        print(f"Source:      {src_prefix}")
        print(f"Destination: {dst_prefix}")

    actions, untracked_files = clone_env(
        src_prefix, dst_prefix, verbose=not json, quiet=quiet, index_args=index_args
    )

    if json:
        common.stdout_json_success(
            actions=actions,
            untracked_files=list(untracked_files),
            src_prefix=src_prefix,
            dst_prefix=dst_prefix,
        )


def print_activate(env_name_or_prefix):  # pragma: no cover
    if not context.quiet and not context.json:
        if " " in env_name_or_prefix:
            env_name_or_prefix = f'"{env_name_or_prefix}"'
        message = dals(
            f"""
        #
        # To activate this environment, use
        #
        #     $ conda activate {env_name_or_prefix}
        #
        # To deactivate an active environment, use
        #
        #     $ conda deactivate
        """
        )
        print(message)  # TODO: use logger


def get_revision(arg, json=False):
    try:
        return int(arg)
    except ValueError:
        raise CondaValueError(f"expected revision number, not: '{arg}'", json)


def get_index_args(args) -> dict[str, any]:
    """Returns a dict of args required for fetching an index
    :param args: The args provided by the cli
    :returns: dict of index args
    """
    return {
        # TODO: deprecate --use-index-cache
        # "use_cache": args.use_index_cache,  # --use-index-cache
        "channel_urls": context.channels,
        # TODO: deprecate --unknown
        # "unknown": args.unknown,  # --unknown
        "prepend": not args.override_channels,  # --override-channels
        "use_local": args.use_local,  # --use-local
    }


def validate_install_command(prefix: str):
    """Executes a set of validations that are required before any installation
    command is executed. This includes:
      * ensure the configuration is valid
      * ensuring the user in not an admin
      * ensure the user is not forcing 32bit installs in the root prefix

    :param prefix: The prefix where the environment will be created
    :raises: error if the configuration for the install is bad
    """
    context.validate_configuration()
    check_non_admin()
    if context.force_32bit and paths_equal(prefix, context.root_prefix):
        raise CondaValueError("cannot use CONDA_FORCE_32BIT=1 in base env")


def install_clone(args, parser):
    """Executes an install of a new conda environment by cloning. Assumes
    that the caller has already checked that the prefix does not exist (or
    is ok to overwrite)
    """
    prefix = context.target_prefix

    # common validations for all types of installs
    validate_install_command(prefix=prefix)

    index_args = get_index_args(args)

    # this is sort of a hack.  current_repodata.json may not have any .tar.bz2 files,
    #    because it deduplicates records that exist as both formats.  Forcing this to
    #    repodata.json ensures that .tar.bz2 files are available
    if context.use_only_tar_bz2:
        args.repodata_fns = ("repodata.json",)

    clone(
        args.clone,
        prefix,
        json=context.json,
        quiet=context.quiet,
        index_args=index_args,
    )
    touch_nonadmin(prefix)
    print_activate(args.name or prefix)
    return


def install(args, parser, command="install"):
    """Logic for `conda install`, `conda update`, and `conda create`."""
    prefix = context.target_prefix

    # common validations for all types of installs
    validate_install_command(prefix=prefix)

    if context.use_only_tar_bz2:
        args.repodata_fns = ("repodata.json",)

    newenv = bool(command == "create")
    isupdate = bool(command == "update")
    isinstall = bool(command == "install")
    isremove = bool(command == "remove")

    if isupdate or isinstall or isremove:
        if isdir(prefix):
            delete_trash(prefix)
            if not isfile(join(prefix, PREFIX_MAGIC_FILE)):
                if paths_equal(prefix, context.conda_prefix):
                    raise NoBaseEnvironmentError()
                else:
                    if not path_is_clean(prefix):
                        raise DirectoryNotACondaEnvironmentError(prefix)
            else:
                validate_prefix_is_writable(prefix)
        else:
            raise EnvironmentLocationNotFound(prefix)

    args_packages = [s.strip("\"'") for s in args.packages]
    if newenv and not args.no_default_packages:
        # Override defaults if they are specified at the command line
        names = [MatchSpec(pkg).name for pkg in args_packages]
        for default_package in context.create_default_packages:
            if MatchSpec(default_package).name not in names:
                args_packages.append(default_package)

    context_channels = context.channels
    index_args = get_index_args(args)
    num_cp = sum(is_package_file(s) for s in args_packages)
    if num_cp:
        if num_cp == len(args_packages):
            explicit(args_packages, prefix, verbose=not context.quiet)
            if newenv:
                touch_nonadmin(prefix)
                print_activate(args.name or prefix)
            return
        else:
            raise CondaValueError(
                "cannot mix specifications with conda package filenames"
            )

    specs = []
    if args.file:
        for fpath in args.file:
            try:
                specs.extend(common.specs_from_url(fpath, json=context.json))
            except UnicodeError:
                raise CondaError(
                    "Error reading file, file should be a text file containing"
                    " packages \nconda create --help for details"
                )
        if "@EXPLICIT" in specs:
            explicit(specs, prefix, verbose=not context.quiet)
            if newenv:
                touch_nonadmin(prefix)
                print_activate(args.name or prefix)
            return
    specs.extend(common.specs_from_args(args_packages, json=context.json))

    # for 'conda update', make sure the requested specs actually exist in the prefix
    # and that they are name-only specs
    if isupdate and context.update_modifier != UpdateModifier.UPDATE_ALL:
        prefix_data = PrefixData(prefix)
        for spec in specs:
            spec = MatchSpec(spec)
            if not spec.is_name_only_spec:
                raise CondaError(
                    f"Invalid spec for 'conda update': {spec}\n"
                    "Use 'conda install' instead."
                )
            if not prefix_data.get(spec.name, None):
                raise PackageNotInstalledError(prefix, spec.name)

    if newenv and args.clone:
        deprecated.topic(
            "25.9",
            "26.3",
            topic="This function will not handle clones anymore.",
            addendum="Use `conda.cli.install.install_clone()` instead",
        )
        return install_clone(args, parser)

    repodata_fns = args.repodata_fns
    if not repodata_fns:
        repodata_fns = list(context.repodata_fns)
    if REPODATA_FN not in repodata_fns:
        repodata_fns.append(REPODATA_FN)

    args_set_update_modifier = (
        hasattr(args, "update_modifier") and args.update_modifier != NULL
    )
    # This helps us differentiate between an update, the --freeze-installed option, and the retry
    # behavior in our initial fast frozen solve
    _should_retry_unfrozen = (
        not args_set_update_modifier
        or args.update_modifier
        not in (UpdateModifier.FREEZE_INSTALLED, UpdateModifier.UPDATE_SPECS)
    ) and not newenv

    for repodata_fn in repodata_fns:
        try:
            if isinstall and args.revision:
                with get_spinner(f"Collecting package metadata ({repodata_fn})"):
                    index = get_index(
                        channel_urls=index_args["channel_urls"],
                        prepend=index_args["prepend"],  # --override-channels
                        platform=None,
                        use_local=index_args["use_local"],  # --use-local
                        # use_cache=index_args["use_cache"],  # --use-index-cache
                        # unknown=index_args["unknown"],  # --unknown
                        prefix=prefix,
                        repodata_fn=repodata_fn,
                    )
                revision_idx = get_revision(args.revision)
                with get_spinner(f"Reverting to revision {revision_idx}"):
                    unlink_link_transaction = revert_actions(
                        prefix, revision_idx, index
                    )
            else:
                solver_backend = context.plugin_manager.get_cached_solver_backend()
                solver = solver_backend(
                    prefix,
                    context_channels,
                    context.subdirs,
                    specs_to_add=specs,
                    repodata_fn=repodata_fn,
                    command=args.cmd,
                )
                update_modifier = context.update_modifier
                if (isinstall or isremove) and args.update_modifier == NULL:
                    update_modifier = UpdateModifier.FREEZE_INSTALLED
                deps_modifier = context.deps_modifier
                if isupdate:
                    deps_modifier = context.deps_modifier or DepsModifier.UPDATE_SPECS

                unlink_link_transaction = solver.solve_for_transaction(
                    deps_modifier=deps_modifier,
                    update_modifier=update_modifier,
                    force_reinstall=context.force_reinstall or context.force,
                    should_retry_solve=(
                        _should_retry_unfrozen or repodata_fn != repodata_fns[-1]
                    ),
                )
            # we only need one of these to work.  If we haven't raised an exception,
            #   we're good.
            break

        except (ResolvePackageNotFound, PackagesNotFoundError) as e:
            if not getattr(e, "allow_retry", True):
                raise e  # see note in next except block
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
            # Quick solve with frozen env or trimmed repodata failed.  Try again without that.
            if not hasattr(args, "update_modifier"):
                if repodata_fn == repodata_fns[-1]:
                    raise e
            elif _should_retry_unfrozen:
                try:
                    unlink_link_transaction = solver.solve_for_transaction(
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
    handle_txn(unlink_link_transaction, prefix, args, newenv)


def revert_actions(prefix, revision=-1, index=None):
    # TODO: If revision raise a revision error, should always go back to a safe revision
    h = History(prefix)
    # TODO: need a History method to get user-requested specs for revision number
    #       Doing a revert right now messes up user-requested spec history.
    #       Either need to wipe out history after ``revision``, or add the correct
    #       history information to the new entry about to be created.
    # TODO: This is wrong!!!!!!!!!!
    user_requested_specs = h.get_requested_specs_map().values()
    try:
        target_state = {
            MatchSpec.from_dist_str(dist_str) for dist_str in h.get_state(revision)
        }
    except IndexError:
        raise CondaIndexError("no such revision: %d" % revision)

    _supplement_index_with_prefix(index, prefix)

    not_found_in_index_specs = set()
    link_precs = set()
    for spec in target_state:
        precs = tuple(prec for prec in index.values() if spec.match(prec))
        if not precs:
            not_found_in_index_specs.add(spec)
        elif len(precs) > 1:
            link_precs.add(_get_best_prec_match(precs))
        else:
            link_precs.add(precs[0])

    if not_found_in_index_specs:
        raise PackagesNotFoundError(not_found_in_index_specs)

    final_precs = IndexedSet(PrefixGraph(link_precs).graph)  # toposort
    unlink_precs, link_precs = diff_for_unlink_link_precs(prefix, final_precs)
    setup = PrefixSetup(prefix, unlink_precs, link_precs, (), user_requested_specs, ())
    return UnlinkLinkTransaction(setup)


def handle_txn(unlink_link_transaction, prefix, args, newenv, remove_op=False):
    if unlink_link_transaction.nothing_to_do:
        if remove_op:
            # No packages found to remove from environment
            raise PackagesNotFoundError(args.package_names)
        elif not newenv:
            if context.json:
                common.stdout_json_success(
                    message="All requested packages already installed."
                )
            else:
                print("\n# All requested packages already installed.\n")
            return

    if not context.json:
        unlink_link_transaction.print_transaction_summary()
        confirm_yn()

    elif context.dry_run:
        actions = unlink_link_transaction._make_legacy_action_groups()[0]
        common.stdout_json_success(prefix=prefix, actions=actions, dry_run=True)
        raise DryRunExit()

    try:
        unlink_link_transaction.download_and_extract()
        if context.download_only:
            raise CondaExitZero(
                "Package caches prepared. UnlinkLinkTransaction cancelled with "
                "--download-only option."
            )
        unlink_link_transaction.execute()

    except SystemExit as e:
        raise CondaSystemExit("Exiting", e)

    if newenv:
        touch_nonadmin(prefix)
        if context.subdir != context._native_subdir():
            set_keys(
                ("subdir", context.subdir),
                path=Path(prefix, ".condarc"),
            )
        print_activate(args.name or prefix)

    if context.json:
        actions = unlink_link_transaction._make_legacy_action_groups()[0]
        common.stdout_json_success(prefix=prefix, actions=actions)
