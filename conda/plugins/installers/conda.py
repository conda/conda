# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Register the native conda installer for conda env files."""

import tempfile
from typing import Iterable, Optional
from os.path import basename

from boltons.setutils import IndexedSet

from ...base.constants import (
    REPODATA_FN,
    UpdateModifier,
    DepsModifier,
)
from ...base.context import context
from ...core.index import calculate_channel_urls
from ...exceptions import (
    CondaImportError,
    CondaExitZero,
    CondaSystemExit,
    PackagesNotFoundError,
    ResolvePackageNotFound,
    SpecsConfigurationConflictError,
    UnsatisfiableError,
)
from ...models.channel import Channel, prioritize_channels
from ...plugins.types import InstallerBase
from .. import CondaInstaller, hookimpl


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

    def install(
            self, 
            prefix: str, 
            specs: Iterable[str], 
            update_modifier: Optional[UpdateModifier] = None, 
            deps_modifier: Optional[DepsModifier] = None,
            should_retry_unfrozen: bool = False,
            index_args: dict[str, any] = {},
            command: str = None,
            *args, **kwargs
        ) -> Iterable[str]:
        """Install packages into an environment"""
        if context.use_only_tar_bz2:
            repodata_fns = ("repodata.json",)
        else: 
            repodata_fns = list(context.repodata_fns)
        if REPODATA_FN not in repodata_fns:
            repodata_fns.append(REPODATA_FN)

        for repodata_fn in Repodatas(
            repodata_fns,
            index_args,
            (UnsatisfiableError, SpecsConfigurationConflictError, SystemExit),
        ):
            with repodata_fn as repodata:
                solver_backend = context.plugin_manager.get_cached_solver_backend()
                solver = solver_backend(
                    prefix,
                    context.channels,
                    context.subdirs,
                    specs_to_add=specs,
                    repodata_fn=repodata,
                    command=command,
                )
                try:
                    unlink_link_transaction = solver.solve_for_transaction(
                        deps_modifier=deps_modifier,
                        update_modifier=update_modifier,
                        force_reinstall=context.force_reinstall or context.force,
                        should_retry_solve=(
                            should_retry_unfrozen or repodata != repodata_fns[-1]
                        ),
                    )
                except (UnsatisfiableError, SpecsConfigurationConflictError) as e:
                    if not getattr(e, "allow_retry", True):
                        raise e
                    if should_retry_unfrozen:
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

        # TODO: do this better and not copy/paste from cli/install.py
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

        return unlink_link_transaction._make_legacy_action_groups()[0]

    def dry_run(self, prefix, specs, *args, **kwargs) -> Iterable[str]:
        """Do a dry run of the environment solve"""
        solver = self._solve(tempfile.mkdtemp(), specs)
        pkgs = solver.solve_final_state()
        return [str(p) for p in pkgs]


@hookimpl
def conda_installers():
    yield CondaInstaller(
        name="conda",
        types=("conda",),
        installer=NativeInstaller,
    )
