# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import tempfile
from contextlib import contextmanager
from functools import partial
import os

from ..base.context import context, locate_prefix_by_name, validate_prefix_name
from ..base.constants import DRY_RUN_PREFIX
from ..cli import common, install
from ..common.path import expand, paths_equal
from ..exceptions import CondaEnvException
from ..gateways.disk.delete import rm_rf
from ..gateways.disk.update import rename


def validate_src(args) -> str:
    """
    Validate that we are receiving at least one value for --name or --prefix
    and ensure that the "base" environment is not being renamed
    """
    if paths_equal(context.target_prefix, context.root_prefix):
        raise CondaEnvException("The 'base' environment cannot be renamed")

    prefix = args.name if args.name else args.prefix

    if common.is_active_prefix(prefix):
        raise CondaEnvException("Cannot rename the active environment")

    return locate_prefix_by_name(prefix)


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


@contextmanager
def safe_rm_destination(directory: str):
    """
    Used for removing a directory when there are dependent actions (i.e. you need to ensure
    other actions succeed before removing it).

    Example:
        with safe_rm_destination(directory):
            # Do dependent actions here
    """
    tmpdir = tempfile.mkdtemp()

    try:
        rename(directory, tmpdir, force=True)
        yield
    except Exception as exc:
        # Error occurred, roll back change
        rename(tmpdir, directory, force=True)
        raise exc


def execute(args, _):
    """
    Executes the command for renaming an existing environment
    """
    source = validate_src(args)
    destination = validate_destination(args.destination, force=args.force)

    def clone_and_remove():
        actions: tuple[partial, ...] = (
            partial(install.clone, source, destination, quiet=context.quiet, json=context.json),
            partial(rm_rf, source),
        )

        # We now either run collected actions or print dry run statement
        for func in actions:
            if args.dry_run:
                print(f"{DRY_RUN_PREFIX} {func.func.__name__} {','.join(func.args)}")
            else:
                func()

    if args.force:
        with safe_rm_destination(destination):
            clone_and_remove()
    else:
        clone_and_remove()
