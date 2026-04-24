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
    from ..base.context import context
    from ..common.constants import NULL
    from ..plugins.types import EnvironmentFormat
    from .actions import NullCountAction
    from .helpers import (
        add_parser_create_install_update,
        add_parser_default_packages,
        add_parser_platform,
        add_parser_solver,
    )

    plugin_manager = context.plugin_manager
    specifiers = list(plugin_manager.get_hook_results("environment_specifiers"))
    spec_example = plugin_manager.example_filename_for(
        EnvironmentFormat.environment, specifiers
    )
    lock_example = plugin_manager.example_filename_for(
        EnvironmentFormat.lockfile, specifiers
    )

    summary = "Create a new conda environment from a list of specified packages."
    description = dals(
        f"""
        {summary}

        Environments can be created from package specs on the command line,
        from an input file whose format is detected from its name or
        contents, or as a clone of an existing environment. See the epilog
        for the input formats available in your installation.

        To use the newly-created environment, use 'conda activate envname'.
        This command requires either the -n NAME or -p PREFIX option unless
        --dry-run or --download-only is specified.
        """
    )

    # Static description blocks use ``dals`` per the house style. The
    # conditional example sub-blocks below use plain strings with explicit
    # leading whitespace: ``dals`` would strip any indent smaller than the
    # longest common prefix, so the "2-space label, 4-space command" shape
    # we want here (matching the issue #15960 examples) has to be written
    # literally.
    example_blocks = [
        "Examples:\n\n"
        "  Create from package specs:\n"
        "    conda create -n myenv python=3.12 numpy",
    ]
    if spec_example:
        example_blocks.append(
            "  Create from an environment spec (solved at install time):\n"
            f"    conda create -n myenv --file {spec_example}"
        )
    if lock_example:
        example_blocks.append(
            "  Create from a lockfile (no solve, exact reproduction):\n"
            f"    conda create -n myenv --file {lock_example}"
        )
    example_blocks.append(
        "  Clone an existing environment:\n    conda create -n env2 --clone env1"
    )
    epilog = "\n\n".join(example_blocks) + plugin_manager.describe_formats(
        specifiers, heading="Available input formats"
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
        get_name_prefix_from_env_file,
        print_activate,
        validate_environment_files_consistency,
        validate_file_exists,
        validate_subdir_config,
    )
    from .install import install, install_clone

    # When `--clone` is present, `--file` and `packages` are not allowed
    if args.clone:
        if args.file:
            raise TooManyArgumentsError(
                0,
                len(args.file),
                list(args.file),
                "`--file` and `--clone` arguments are mutually exclusive.",
            )
        if args.packages:
            raise TooManyArgumentsError(
                0,
                len(args.packages),
                list(args.packages),
                "Did not expect any new packages or arguments for `--clone`.",
            )

    for fpath in args.file:
        validate_file_exists(fpath)
    validate_environment_files_consistency(args.file)

    if not args.name and not args.prefix:
        if args.file and len(args.file) > 1:
            raise ArgumentError(
                "Multiple environment files were specified but no name or prefix was provided. "
                "Please provide -n/--name or -p/--prefix when using multiple --file arguments."
            )

        if args.file:
            # We know there's only a single file being passed in at this point
            name, prefix = get_name_prefix_from_env_file(args.file[0])
            if name is not None:
                args.name = name
            if prefix is not None and args.name is None:
                args.prefix = prefix

        if args.name is not None or args.prefix is not None:
            context.__init__(argparse_args=args)
        elif args.file:
            raise ArgumentError(
                "The environment file(s) do not specify a name or prefix. "
                "Please provide one via -n/--name or -p/--prefix."
            )
        elif context.dry_run or context.download_only:
            args.prefix = os.path.join(mktemp(), UNUSED_ENV_NAME)
            context.__init__(argparse_args=args)
        else:
            raise ArgumentError(
                "one of the arguments -n/--name -p/--prefix is required"
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

    # Run appropriate install
    if args.clone:
        install_clone(args, parser)
    else:
        install(args, parser, "create")
    # Run post-install steps applicable to all new environments
    prefix_data.set_nonadmin()
    print_activate(args.name or context.target_prefix)

    return 0
