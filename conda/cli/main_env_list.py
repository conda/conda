# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI implementation for `conda-env list`.

Lists available conda environments.
"""

from argparse import ArgumentParser, Namespace, _SubParsersAction


def configure_parser(sub_parsers: _SubParsersAction, **kwargs) -> ArgumentParser:
    from ..auxlib.ish import dals
    from .helpers import add_parser_json

    summary = "List the Conda environments."
    description = summary
    epilog = dals(
        """
        Examples::

            conda env list
            conda env list --json

        """
    )
    p = sub_parsers.add_parser(
        "list",
        help=summary,
        description=description,
        epilog=epilog,
        **kwargs,
    )

    add_parser_json(p)

    p.set_defaults(func="conda.cli.main_env_list.execute")

    return p


def execute(args: Namespace, parser: ArgumentParser):
    from ..base.context import context
    from ..common.io import get_reporter_manager
    from ..core.envs_manager import list_all_known_prefixes

    reporter_manager = get_reporter_manager()
    reporter_manager.render(
        list_all_known_prefixes(), component="envs_list", context=context
    )

    return 0
