# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Entry point for all conda-env subcommands."""
from argparse import ArgumentParser, Namespace, _SubParsersAction

import conda.exports  # noqa


def configure_parser(sub_parsers: _SubParsersAction, **kwargs) -> ArgumentParser:
    from ..cli import (
        main_env_config,
        main_env_create,
        main_env_export,
        main_env_list,
        main_env_remove,
        main_env_update,
    )

    if sub_parsers is None:
        p = ArgumentParser()

    else:
        p = sub_parsers.add_parser(
            "env",
            **kwargs,
        )

    env_parsers = p.add_subparsers(
        metavar="command",
        dest="cmd",
    )
    main_env_config.configure_parser(env_parsers)
    main_env_create.configure_parser(env_parsers)
    main_env_export.configure_parser(env_parsers)
    main_env_list.configure_parser(env_parsers)
    main_env_remove.configure_parser(env_parsers)
    main_env_update.configure_parser(env_parsers)

    p.set_defaults(func="conda.cli.main_env.execute")
    return p


def execute(args: Namespace, parser: ArgumentParser) -> int:
    parser.parse_args(["env", "--help"])

    return 0
