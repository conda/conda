# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

from argparse import RawDescriptionHelpFormatter
import argparse

from conda.cli import common


descr = "Launch an IPython Notebook as an app"
example = """
examples:
    conda launch MyNotebookApp.ipynb

"""

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'launch',
        formatter_class = RawDescriptionHelpFormatter,
        description = descr,
        help = descr,
        epilog = example,
    )
    common.add_parser_install(p)
    p.add_argument(
        "-v", "--view",
        action="store_true",
        default=False,
        help="view notebook app (do not execute or prompt for input)",
    )
    p.add_argument(
        "-s", "--server",
        help="app server (protocol, hostname, port)",
    )
    p.add_argument(
        "-e", "--env",
        help="conda environment to use (by name or path, relative to app server)",
    )
    p.add_argument(
        "notebook",
        help="notebook app name, URL, or path",
    )
    p.add_argument(
        'nbargs',
        nargs=argparse.REMAINDER
    )

    p.set_defaults(func=execute)


def execute(args, parser):
    from conda import launch
    try:
        launch.launch(
            notebook    = args.notebook,
            args        = args.nbargs,
            server      = args.server,
            env         = args.env,
            channels    = args.channel,
            view        = args.view
        )
    except ValueError as ex:
        print("invalid arguments: " + str(ex))
