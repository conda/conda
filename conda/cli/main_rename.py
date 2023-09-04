# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI implementation for `conda rename`.

Renames an existing environment by cloning it and then removing the original environment.
"""
from __future__ import annotations

import os
from functools import partial
from pathlib import Path

from ..base.constants import DRY_RUN_PREFIX
from ..base.context import context, validate_prefix_name
from ..cli import install
from ..common.path import expand
from ..deprecations import deprecated
from ..exceptions import CondaEnvException
from ..gateways.disk.delete import rm_rf
from ..gateways.disk.update import rename_context


@deprecated.argument("24.3", "24.9", "name")
@deprecated.argument("24.3", "24.9", "prefix")
def validate_src() -> str:
    """
    Validate that we are receiving at least one value for --name or --prefix
    and ensure that the "base" environment is not being renamed
    """
    if Path(context.target_prefix).samefile(context.root_prefix):
        raise CondaEnvException("The 'base' environment cannot be renamed")

    if Path(context.target_prefix).samefile(context.active_prefix):
        raise CondaEnvException("Cannot rename the active environment")

    return context.target_prefix


def validate_destination(dest: str, force: bool = False) -> str:
    """Ensure that our destination does not exist"""
    if os.sep in dest:
        dest = expand(dest)
    else:
        dest = validate_prefix_name(dest, ctx=context, allow_base=False)

    if not force and os.path.exists(dest):
        env_name = os.path.basename(os.path.normpath(dest))
        raise CondaEnvException(
            f"The environment '{env_name}' already exists. Override with --force."
        )
    return dest


def execute(args, _):
    """Executes the command for renaming an existing environment."""
    source = validate_src()
    destination = validate_destination(args.destination, force=args.force)

    def clone_and_remove():
        actions: tuple[partial, ...] = (
            partial(
                install.clone,
                source,
                destination,
                quiet=context.quiet,
                json=context.json,
            ),
            partial(rm_rf, source),
        )

        # We now either run collected actions or print dry run statement
        for func in actions:
            if args.dry_run:
                print(f"{DRY_RUN_PREFIX} {func.func.__name__} {','.join(func.args)}")
            else:
                func()

    if args.force:
        with rename_context(destination, dry_run=args.dry_run):
            clone_and_remove()
    else:
        clone_and_remove()
