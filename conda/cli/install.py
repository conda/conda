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
from os.path import abspath, basename, exists, isdir
from pathlib import Path

from boltons.setutils import IndexedSet

from .. import CondaError
from ..base.constants import (
    REPODATA_FN,
    ROOT_ENV_NAME,
    UpdateModifier,
)
from ..base.context import context
from ..common.constants import NULL
from ..common.path import is_package_file
from ..core.index import (
    Index,
    calculate_channel_urls,
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
    DryRunExit,
    NoBaseEnvironmentError,
    PackageNotInstalledError,
    PackagesNotFoundError,
    ResolvePackageNotFound,
    SpecsConfigurationConflictError,
    UnsatisfiableError,
)
from ..gateways.disk.delete import delete_trash, path_is_clean
from ..history import History
from ..misc import _get_best_prec_match, clone_env, explicit
from ..models.match_spec import MatchSpec
from ..models.prefix_graph import PrefixGraph
from ..reporters import confirm_yn, get_spinner
from . import common
from .common import check_non_admin
from .main_config import set_keys

log = getLogger(__name__)
stderrlog = getLogger("conda.stderr")


@deprecated("25.9", "26.3", addendum="Use PrefixData.exists()")
def validate_prefix_exists(prefix: str | Path) -> None:
    """
    Validate that we are receiving at least one valid value for --name or --prefix.
    """
    prefix = Path(prefix)
    if not prefix.exists():
        raise CondaEnvException("The environment you have specified does not exist.")


@deprecated(
    "25.9", "26.3", addendum="Use PrefixData.exists() + PrefixData.validate_path()"
)
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


@deprecated(
    "25.9",
    "26.3",
    addendum="Use PrefixData.exists(), PrefixData.validate_path(), PrefixData.validate_name()",
)
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
    # Validate source
    if os.sep in src_arg:
        source_prefix_data = PrefixData(abspath(src_arg))
    else:
        source_prefix_data = PrefixData.from_name(src_arg)
    source_prefix_data.assert_environment()
    src_prefix = str(source_prefix_data.prefix_path)

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


@deprecated("25.9", "26.3", addendum="Use conda.cli.common.print_activate()")
def print_activate(env_name_or_prefix):  # pragma: no cover
    from .common import print_activate as _print_activate

    _print_activate(env_name_or_prefix)


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


class TryRepodata:
    def __init__(
        self, notify_success, repodata, last_repodata, index_args, allowed_errors
    ):
        self.notify_success = notify_success
        self.repodata = repodata
        self.last_repodata = last_repodata
        self.index_args = index_args
        self.allowed_errors = allowed_errors

    def __enter__(self):
        return self.repodata

    def __exit__(self, exc_type, exc_value, traceback):
        if not exc_value:
            self.notify_success()

        # Swallow the error to allow for the next repodata to be tried if:
        # 1. the error is in the 'allowed_errors' type
        # 2. there are more repodatas to try AND
        # 3. the error says it's okay to retry
        #
        # TODO: Regarding (3) This is a temporary workaround to allow downstream libraries
        # to inject this attribute set to False and skip the retry logic
        # Other solvers might implement their own internal retry logic without
        # depending --freeze-install implicitly like conda classic does. Example
        # retry loop in conda-libmamba-solver:
        # https://github.com/conda-incubator/conda-libmamba-solver/blob/da5b1ba/conda_libmamba_solver/solver.py#L254-L299
        # If we end up raising UnsatisfiableError, we annotate it with `allow_retry`
        # so we don't have go through all the repodatas and freeze-installed logic
        # unnecessarily (see https://github.com/conda/conda/issues/11294). see also:
        # https://github.com/conda-incubator/conda-libmamba-solver/blob/7c698209/conda_libmamba_solver/solver.py#L617
        if (
            isinstance(exc_value, self.allowed_errors)
            and (self.repodata != self.last_repodata)
            and getattr(exc_value, "allow_retry", True)
        ):
            return True
        elif isinstance(exc_value, ResolvePackageNotFound):
            # transform a ResolvePackageNotFound into PackagesNotFoundError
            channels_urls = tuple(
                calculate_channel_urls(
                    channel_urls=self.index_args["channel_urls"],
                    prepend=self.index_args["prepend"],
                    platform=None,
                    use_local=self.index_args["use_local"],
                )
            )
            # convert the ResolvePackageNotFound into PackagesNotFoundError
            raise PackagesNotFoundError(exc_value._formatted_chains, channels_urls)


class Repodatas:
    def __init__(self, repodata_fns, index_args, allows_errors=()):
        self.repodata_fns = repodata_fns
        self.index_args = index_args
        self.success = False
        self.allowed_errors = (
            ResolvePackageNotFound,
            PackagesNotFoundError,
            *allows_errors,
        )

    def __iter__(self):
        for repodata in self.repodata_fns:
            yield TryRepodata(
                self.succeed,
                repodata,
                self.repodata_fns[-1],
                self.index_args,
                self.allowed_errors,
            )
            if self.success:
                break

    def succeed(self):
        self.success = True


def validate_install_command(prefix: str, command: str = "install"):
    """Executes a set of validations that are required before any installation
    command is executed. This includes:
      * ensure the configuration is valid
      * ensuring the user in not an admin
      * ensure the user is not forcing 32bit installs in the root prefix

    :param prefix: The prefix where the environment will be created
    :param command: Type of operation being performed
    :raises: error if the configuration for the install is bad
    """
    context.validate_configuration()
    check_non_admin()

    prefix_data = PrefixData(prefix)

    if context.force_32bit and prefix_data.is_base():
        raise CondaValueError("cannot use CONDA_FORCE_32BIT=1 in base env")

    if command in ("install", "update", "remove"):
        try:
            prefix_data.assert_writable()
        except DirectoryNotACondaEnvironmentError as exc:
            if prefix_data == PrefixData(context.conda_prefix):
                raise NoBaseEnvironmentError() from exc
            delete_trash(prefix)
            if not path_is_clean(prefix):
                raise
        if context.protect_frozen_envs:
            prefix_data.assert_not_frozen()


def ensure_update_specs_exist(prefix: str, specs: list[str]):
    """Checks that each spec that is requested as an update exists in the prefix

    :param prefix: The target install prefix
    :param specs: List of specs to be updated
    :raises CondaError: if there is an invalid spec provided
    :raises PackageNotInstalledError: if the requested specs to install don't exist in the prefix
    """
    prefix_data = PrefixData(prefix)
    for spec in specs:
        spec = MatchSpec(spec)
        if not spec.is_name_only_spec:
            raise CondaError(
                f"Invalid spec for 'conda update': {spec}\nUse 'conda install' instead."
            )
        if not prefix_data.get(spec.name, None):
            raise PackageNotInstalledError(prefix, spec.name)


def install_clone(args, parser):
    """Executes an install of a new conda environment by cloning."""
    prefix = context.target_prefix
    index_args = get_index_args(args)

    # common validations for all types of installs
    validate_install_command(prefix=prefix, command="create")

    clone(
        args.clone,
        prefix,
        json=context.json,
        quiet=context.quiet,
        index_args=index_args,
    )


def install(args, parser, command="install"):
    """Logic for `conda install`, `conda update`, `conda remove`, and `conda create`."""
    prefix = context.target_prefix

    # common validations for all types of installs
    validate_install_command(prefix=prefix, command=command)

    if context.use_only_tar_bz2:
        args.repodata_fns = ("repodata.json",)

    newenv = command == "create"
    isupdate = command == "update"
    isinstall = command == "install"
    isremove = command == "remove"

    # collect packages provided from the command line
    args_packages = [s.strip("\"'") for s in args.packages]
    if newenv and not args.no_default_packages:
        # Override defaults if they are specified at the command line
        names = [MatchSpec(pkg).name for pkg in args_packages]
        for default_package in context.create_default_packages:
            if MatchSpec(default_package).name not in names:
                args_packages.append(default_package)

    index_args = get_index_args(args=args)
    context_channels = context.channels

    num_cp = sum(is_package_file(s) for s in args_packages)
    if num_cp:
        if num_cp == len(args_packages):
            # short circuit to installing explicit if all specs are direct files
            explicit(args_packages, prefix, verbose=not context.quiet)
            return
        else:
            raise CondaValueError(
                "cannot mix specifications with conda package filenames"
            )

    # collect specs provided by --file arguments
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
            # short circuit to installing explicit if explicit specs are provided
            explicit(specs, prefix, verbose=not context.quiet)
            return
    specs.extend(common.specs_from_args(args_packages))

    # for 'conda update', make sure the requested specs actually exist in the prefix
    # and that they are name-only specs
    if isupdate and context.update_modifier != UpdateModifier.UPDATE_ALL:
        ensure_update_specs_exist(prefix=prefix, specs=specs)
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

    args_set_update_modifier = getattr(args, "update_modifier", NULL) != NULL
    # This helps us differentiate between an update, the --freeze-installed option, and the retry
    # behavior in our initial fast frozen solve
    _should_retry_unfrozen = (
        not args_set_update_modifier
        or args.update_modifier
        not in (UpdateModifier.FREEZE_INSTALLED, UpdateModifier.UPDATE_SPECS)
    ) and not newenv

    update_modifier = context.update_modifier
    if (isinstall or isremove) and args.update_modifier == NULL:
        update_modifier = UpdateModifier.FREEZE_INSTALLED
    deps_modifier = context.deps_modifier

    for repodata_fn in Repodatas(
        repodata_fns,
        index_args,
        (UnsatisfiableError, SpecsConfigurationConflictError, SystemExit),
    ):
        with repodata_fn as repodata:
            solver_backend = context.plugin_manager.get_cached_solver_backend()
            solver = solver_backend(
                prefix,
                context_channels,
                context.subdirs,
                specs_to_add=specs,
                repodata_fn=repodata,
                command=args.cmd,
            )
            try:
                unlink_link_transaction = solver.solve_for_transaction(
                    deps_modifier=deps_modifier,
                    update_modifier=update_modifier,
                    force_reinstall=context.force_reinstall or context.force,
                    should_retry_solve=(
                        _should_retry_unfrozen or repodata != repodata_fns[-1]
                    ),
                )
            except (UnsatisfiableError, SpecsConfigurationConflictError) as e:
                if not getattr(e, "allow_retry", True):
                    raise e
                if _should_retry_unfrozen:
                    unlink_link_transaction = solver.solve_for_transaction(
                        deps_modifier=deps_modifier,
                        update_modifier=UpdateModifier.UPDATE_SPECS,
                        force_reinstall=context.force_reinstall or context.force,
                        should_retry_solve=(repodata != repodata_fns[-1]),
                    )
                else:
                    raise e
            except SystemExit as e:
                if not getattr(e, "allow_retry", True):
                    raise e
                if e.args and "could not import" in e.args[0]:
                    raise CondaImportError(str(e))
                raise e

    handle_txn(unlink_link_transaction, prefix, args, newenv)


def install_revision(args, parser):
    """Install a previous version of a conda environment"""
    prefix = context.target_prefix
    index_args = get_index_args(args)

    # common validations for all types of installs
    validate_install_command(prefix=prefix, command="install")

    # this is sort of a hack.  current_repodata.json may not have any .tar.bz2 files,
    #    because it deduplicates records that exist as both formats.  Forcing this to
    #    repodata.json ensures that .tar.bz2 files are available
    if context.use_only_tar_bz2:
        args.repodata_fns = ("repodata.json",)

    # ensure trash is cleared from existing prefix
    delete_trash(prefix)

    repodata_fns = args.repodata_fns
    if not repodata_fns:
        repodata_fns = list(context.repodata_fns)
    if REPODATA_FN not in repodata_fns:
        repodata_fns.append(REPODATA_FN)

    for repodata_fn in Repodatas(repodata_fns, index_args):
        with repodata_fn as repodata:
            with get_spinner(f"Collecting package metadata ({repodata})"):
                index = Index(
                    channels=index_args["channel_urls"],
                    prepend=index_args["prepend"],  # --override-channels
                    platform=None,
                    # these options were commented out in the version of this
                    # code bit that used the now-deprecated `get_index` function
                    # we have left them here so that this information is not lost
                    # use_cache=index_args["use_cache"],  # --use-index-cache
                    # unknown=index_args["unknown"],  # --unknown
                    use_local=index_args["use_local"],
                    prefix=prefix,
                    repodata_fn=repodata,
                )
            revision_idx = get_revision(args.revision)
            with get_spinner(f"Reverting to revision {revision_idx}"):
                unlink_link_transaction = revert_actions(prefix, revision_idx, index)

    handle_txn(unlink_link_transaction, prefix, args, newenv=False)


def revert_actions(prefix, revision=-1, index: Index | None = None):
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

    if index is not None:
        index.reload(prefix=True)

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
        if context.subdir != context._native_subdir():
            set_keys(
                ("subdir", context.subdir),
                path=Path(prefix, ".condarc"),
            )

    if context.json:
        actions = unlink_link_transaction._make_legacy_action_groups()[0]
        common.stdout_json_success(prefix=prefix, actions=actions)
