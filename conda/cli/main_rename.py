# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
from typing import Callable

from conda.base.context import context, locate_prefix_by_name, validate_prefix_name
from conda.base.constants import DRY_RUN_PREFIX
from conda.cli import common, install
from conda.common.path import expand
from conda.exceptions import CondaEnvException
from conda.gateways.disk.delete import rm_rf


def validate_src(args) -> str:
    """
    Validate that we are receiving at least one value for --name or --prefix
    and ensure that the "base" environment is not being renamed
    """
    common.ensure_name_or_prefix(args, "env rename")

    if context.target_prefix == context.root_prefix:
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
        raise CondaEnvException("Environment destination already exists. Override with --force.")

    return dest


Args = tuple
Kwargs = dict


def execute(args, _):
    """
    Executes the command for renaming an existing environment
    """
    src = validate_src(args)
    dest = validate_destination(args.destination, force=args.force)

    actions: list[tuple[Callable, Args, Kwargs]] = []

    if args.force:
        actions.append((rm_rf, (dest,), {}))

    actions.append(
        (
            install.clone,
            (src, dest),
            {"quiet": context.quiet, "json": context.json},
        )
    )
    actions.append((rm_rf, (src,), {}))

    # We now either run collected actions or print dry run statement
    for act_func, act_args, act_kwargs in actions:
        if args.dry_run:
            pos_args = ", ".join(act_args)
            print(f"{DRY_RUN_PREFIX} {act_func.__name__} {pos_args}")
        else:
            act_func(*act_args, **act_kwargs)
