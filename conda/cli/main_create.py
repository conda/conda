# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI implementation for `conda create`.

Creates new conda environments with the specified packages.
"""

from __future__ import annotations

from logging import getLogger
from typing import TYPE_CHECKING

from ..notices import notices

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace, _SubParsersAction

log = getLogger(__name__)


def configure_parser(sub_parsers: _SubParsersAction, **kwargs) -> ArgumentParser:
    from ..auxlib.ish import dals
    from ..common.constants import NULL
    from .actions import NullCountAction
    from .helpers import (
        add_parser_create_install_update,
        add_parser_default_packages,
        add_parser_platform,
        add_parser_solver,
    )

    summary = "Create a new conda environment from a list of specified packages. "
    description = dals(
        f"""
        {summary}

        To use the newly-created environment, use 'conda activate envname'.
        This command requires either the -n NAME or -p PREFIX option.
        """
    )
    epilog = dals(
        """
        Examples:

        Create an environment containing the package 'sqlite'::

            conda create -n myenv sqlite

        Create an environment (env2) as a clone of an existing environment (env1)::

            conda create -n env2 --clone path/to/file/env1

        """
    )
    p = sub_parsers.add_parser(
        "create",
        help=summary,
        description=description,
        epilog=epilog,
        **kwargs,
    )
    p.add_argument(
        "--clone",
        action="store",
        help="Create a new environment as a copy of an existing local environment.",
        metavar="ENV",
    )
    solver_mode_options, _, channel_options = add_parser_create_install_update(p)
    add_parser_default_packages(solver_mode_options)
    add_parser_platform(channel_options)
    add_parser_solver(solver_mode_options)
    p.add_argument(
        "--dev",
        action=NullCountAction,
        help="Use `sys.executable -m conda` in wrapper scripts instead of CONDA_EXE. "
        "This is mainly for use during tests where we test new conda sources "
        "against old Python versions.",
        dest="dev",
        default=NULL,
    )
    p.set_defaults(func="conda.cli.main_create.execute")

    return p


@notices
def execute(args: Namespace, parser: ArgumentParser) -> int:
    import os
    from tempfile import mktemp

    from ..base.constants import UNUSED_ENV_NAME
    from ..base.context import context
    from ..core.prefix_data import PrefixData
    from ..exceptions import ArgumentError, CondaValueError, TooManyArgumentsError
    from ..gateways.disk.delete import rm_rf
    from ..reporters import confirm_yn
    from .common import (
        print_activate,
        validate_environment_files_consistency,
        validate_subdir_config,
    )
    from .install import install, install_clone

    # Ensure provided combination of command line argments are valid
    # At least one of the arguments -n/--name -p/--prefix is required
    if not args.name and not args.prefix:
        if context.dry_run:
            args.prefix = os.path.join(mktemp(), UNUSED_ENV_NAME)
            context.__init__(argparse_args=args)
        else:
            raise ArgumentError(
                "one of the arguments -n/--name -p/--prefix is required"
            )

    # Only one of the arguments --clone and packages is allowed
    if args.clone and args.packages:
        raise TooManyArgumentsError(
            0,
            len(args.packages),
            list(args.packages),
            "did not expect any arguments for --clone",
        )
    prefix_data = PrefixData.from_context(validate=True)

    if prefix_data.is_environment():
        if context.dry_run:
            # Taking the "easy" way out, rather than trying to fake removing
            # the existing environment before creating a new one.
            raise CondaValueError(
                "Cannot `create --dry-run` with an existing conda environment"
            )
        confirm_yn(
            f"WARNING: A conda environment already exists at '{context.target_prefix}'\n\n"
            "Remove existing environment?\nThis will remove ALL directories contained within "
            "this specified prefix directory, including any other conda environments.\n\n",
            default="no",
            dry_run=False,
        )
        log.info("Removing existing environment %s", context.target_prefix)
        rm_rf(context.target_prefix)
    elif prefix_data.exists():
        confirm_yn(
            f"WARNING: A directory already exists at the target location '{context.target_prefix}'\n"
            "but it is not a conda environment.\n"
            "Continue creating environment",
            default="no",
            dry_run=False,
        )

    # Ensure the subdir config is valid
    validate_subdir_config()

    # Validate that input files are of the same format type
    validate_environment_files_consistency(args.file)

    # Run appropriate install
    if args.clone:
        install_clone(args, parser)
    else:
        install(args, parser, "create")
    # Run post-install steps applicable to all new environments
    prefix_data.set_nonadmin()
    print_activate(args.name or context.target_prefix)

    return 0
