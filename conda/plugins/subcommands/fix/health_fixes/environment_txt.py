# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Fix task: Register environment in environments.txt."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .....base.context import context
from .....cli.helpers import add_output_and_prompt_options, add_parser_prefix
from .....core.envs_manager import get_user_environments_txt_file, register_env
from .....core.prefix_data import PrefixData
from .....reporters import confirm_yn
from .... import hookimpl
from ....types import CondaHealthFix
from ...doctor.health_checks import check_envs_txt_file

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace

SUMMARY = "Register environment in environments.txt"


def configure_parser(parser: ArgumentParser) -> None:
    """Configure parser for environment-txt fix task."""
    parser.description = (
        "Register environment in environments.txt.\n\n"
        "This fix task adds the current environment to the user's "
        "environments.txt file if it's not already listed."
    )
    add_parser_prefix(parser)
    add_output_and_prompt_options(parser)


def execute(args: Namespace) -> int:
    """Execute the environment-txt fix task."""
    prefix_data = PrefixData.from_context()
    prefix_data.assert_environment()
    prefix = str(prefix_data.prefix_path)

    if check_envs_txt_file(prefix):
        print(f"Environment is already registered in environments.txt: {prefix}")
        return 0

    envs_txt = get_user_environments_txt_file()
    print(f"Environment not found in {envs_txt}")
    print(f"  Environment: {prefix}")

    print()
    confirm_yn(
        "Register this environment?",
        default="yes",
        dry_run=context.dry_run,
    )

    register_env(prefix)
    print(f"Environment registered: {prefix}")
    return 0


@hookimpl
def conda_health_fixes():
    """Register the environment-txt fix."""
    yield CondaHealthFix(
        name="environment-txt",
        summary=SUMMARY,
        configure_parser=configure_parser,
        execute=execute,
    )
