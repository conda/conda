# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Fix task: Reinstall packages with altered files."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .....base.context import context
from .....cli.helpers import add_output_and_prompt_options, add_parser_prefix
from .....core.prefix_data import PrefixData
from .....reporters import confirm_yn
from .... import hookimpl
from ....types import CondaHealthFix
from ...doctor.health_checks import find_altered_packages

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace

SUMMARY = "Reinstall packages with altered files"


def configure_parser(parser: ArgumentParser) -> None:
    """Configure parser for altered-files fix task."""
    parser.description = (
        "Reinstall packages that have altered files.\n\n"
        "This fix task identifies packages with files that have been modified "
        "(checksum mismatch, as reported by `conda doctor`) and reinstalls them "
        "to restore the original files."
    )
    add_parser_prefix(parser)
    add_output_and_prompt_options(parser)


def execute(args: Namespace) -> int:
    """Execute the altered-files fix task."""
    from .....cli.install import install

    prefix_data = PrefixData.from_context()
    prefix_data.assert_environment()
    prefix = str(prefix_data.prefix_path)

    altered_packages = find_altered_packages(prefix)

    if not altered_packages:
        print("No packages with altered files found.")
        return 0

    print(f"Found {len(altered_packages)} package(s) with altered files:")
    for pkg_name, files in sorted(altered_packages.items()):
        print(f"  {pkg_name}: {len(files)} altered file(s)")

    print()
    confirm_yn(
        "Reinstall these packages to restore original files?",
        default="no",
        dry_run=context.dry_run,
    )

    # Get the package specs to reinstall
    specs = list(altered_packages.keys())

    # Use conda install --force-reinstall
    args.packages = specs
    args.force_reinstall = True
    args.channel = None
    args.override_channels = False
    args.satisfied_skip_solve = False
    args.update_deps = False
    args.only_deps = False
    args.no_deps = False
    args.prune = False
    args.freeze_installed = False
    args.solver_retries = 0

    return install(args)


@hookimpl
def conda_health_fixes():
    """Register the altered-files fix."""
    yield CondaHealthFix(
        name="altered-files",
        summary=SUMMARY,
        configure_parser=configure_parser,
        execute=execute,
    )
