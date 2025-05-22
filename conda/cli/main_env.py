# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Entry point for all conda-env subcommands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import main_export

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace, _SubParsersAction


def configure_parser(sub_parsers: _SubParsersAction, **kwargs) -> ArgumentParser:
    from . import (
        main_env_config,
        main_env_create,
        main_env_list,
        main_env_remove,
        main_env_update,
    )

    p = sub_parsers.add_parser(
        "env",
        help="Create and manage conda environments.",
        **kwargs,
    )

    env_parsers = p.add_subparsers(
        metavar="command",
        dest="cmd",
    )
    main_env_config.configure_parser(env_parsers)
    main_env_create.configure_parser(env_parsers)
    main_export.configure_parser(env_parsers)
    main_env_list.configure_parser(env_parsers)
    main_env_remove.configure_parser(env_parsers)
    main_env_update.configure_parser(env_parsers)

    p.set_defaults(func="conda.cli.main_env.execute")
    return p


def execute(args: Namespace, parser: ArgumentParser) -> int:
    parser.parse_args(["env", "--help"])

    return 0
