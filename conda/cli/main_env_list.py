# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI implementation for `conda-env list`, now aliased to `conda info --envs`.

Lists available conda environments.
"""

from argparse import ArgumentParser, _SubParsersAction


def configure_parser(sub_parsers: _SubParsersAction, **kwargs) -> ArgumentParser:
    from ..auxlib.ish import dals
    from .helpers import add_parser_json

    summary = "An alias for `conda info --envs`. Lists all conda environments."
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

    p.set_defaults(
        func="conda.cli.main_info.execute",
        # The following are the necessary default args for the `conda info` command
        envs=True,
        base=False,
        unsafe_channels=False,
        system=False,
        all=False,
    )

    return p
