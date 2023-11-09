# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI implementation for `conda-env remove`.

Removes the specified conda environment.
"""
from argparse import Namespace, RawDescriptionHelpFormatter

from conda.cli.conda_argparse import (
    add_output_and_prompt_options,
    add_parser_prefix,
    add_parser_solver,
)


def configure_parser(sub_parsers):
    from ..auxlib.ish import dals

    summary = "Remove an environment."
    description = dals(
        f"""
        {summary}

        Removes a provided environment.  You must deactivate the existing
        environment before you can remove it.

        """
    )
    epilog = dals(
        """
        Examples::

            conda env remove --name FOO
            conda env remove -n FOO

        """
    )

    p = sub_parsers.add_parser(
        "remove",
        formatter_class=RawDescriptionHelpFormatter,
        help=summary,
        description=description,
        epilog=epilog,
    )

    add_parser_prefix(p)
    add_parser_solver(p)
    add_output_and_prompt_options(p)

    p.set_defaults(func=".main_remove.execute")


def execute(args, parser):
    import conda.cli.main_remove

    args = vars(args)
    args.update(
        {
            "all": True,
            "channel": None,
            "features": None,
            "override_channels": None,
            "use_local": None,
            "use_cache": None,
            "offline": None,
            "force": True,
            "pinned": None,
        }
    )
    args = Namespace(**args)
    from conda.base.context import context

    context.__init__(argparse_args=args)

    conda.cli.main_remove.execute(args, parser)
