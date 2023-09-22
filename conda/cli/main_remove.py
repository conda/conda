# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI implementation for `conda remove`.

Removes the specified packages from an existing environment.
"""
import logging
from os.path import isfile, join

from ..base.context import context
from ..core.envs_manager import unregister_env
from ..core.link import PrefixSetup, UnlinkLinkTransaction
from ..core.prefix_data import PrefixData
from ..exceptions import (
    CondaEnvironmentError,
    CondaValueError,
    DirectoryNotACondaEnvironmentError,
    PackagesNotFoundError,
)
from ..gateways.disk.delete import path_is_clean, rm_rf
from ..models.match_spec import MatchSpec
from .common import check_non_admin, specs_from_args
from .install import handle_txn

log = logging.getLogger(__name__)


def execute(args, parser):
    if not (args.all or args.package_names):
        raise CondaValueError(
            "no package names supplied,\n"
            '       try "conda remove -h" for more details'
        )

    prefix = context.target_prefix
    check_non_admin()

    if args.all and prefix == context.default_prefix:
        msg = "cannot remove current environment. deactivate and run conda remove again"
        raise CondaEnvironmentError(msg)

    if args.all and path_is_clean(prefix):
        # full environment removal was requested, but environment doesn't exist anyway

        # .. but you know what? If you call `conda remove --all` you'd expect the dir
        # not to exist afterwards, would you not? If not (fine, I can see the argument
        # about deleting people's work in envs being a very bad thing indeed), but if
        # being careful is the goal it would still be nice if after `conda remove --all`
        # to be able to do `conda create` on the same environment name.
        #
        # try:
        #     rm_rf(prefix, clean_empty_parents=True)
        # except:
        #     log.warning("Failed rm_rf() of partially existent env {}".format(prefix))

        return 0

    if args.all:
        if prefix == context.root_prefix:
            raise CondaEnvironmentError(
                "cannot remove root environment, add -n NAME or -p PREFIX option"
            )
        if not isfile(join(prefix, "conda-meta", "history")):
            raise DirectoryNotACondaEnvironmentError(prefix)
        if not args.json:
            print(f"\nRemove all packages in environment {prefix}:\n")

        if "package_names" in args:
            stp = PrefixSetup(
                target_prefix=prefix,
                unlink_precs=tuple(PrefixData(prefix).iter_records()),
                link_precs=(),
                remove_specs=(),
                update_specs=(),
                neutered_specs={},
            )
            txn = UnlinkLinkTransaction(stp)
            try:
                handle_txn(txn, prefix, args, False, True)
            except PackagesNotFoundError:
                if not args.json:
                    print(
                        f"No packages found in {prefix}. Continuing environment removal"
                    )
        if not context.dry_run:
            rm_rf(prefix, clean_empty_parents=True)
            unregister_env(prefix)

        return

    else:
        if args.features:
            specs = tuple(MatchSpec(track_features=f) for f in set(args.package_names))
        else:
            specs = specs_from_args(args.package_names)
        channel_urls = ()
        subdirs = ()
        solver_backend = context.plugin_manager.get_cached_solver_backend()
        solver = solver_backend(prefix, channel_urls, subdirs, specs_to_remove=specs)
        txn = solver.solve_for_transaction()
        handle_txn(txn, prefix, args, False, True)
