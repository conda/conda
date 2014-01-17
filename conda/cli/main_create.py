# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import sys
from argparse import RawDescriptionHelpFormatter

from conda.cli import common, install


help = "Create a new conda environment from a list of specified packages. "
descr = (help +
         "To use the created environment, use 'source activate "
         "envname' look in that directory first.  This command requires either "
         "the -n NAME or -p PREFIX option.")

example = """
examples:
    conda create -n myenv sqlite

"""

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'create',
        formatter_class = RawDescriptionHelpFormatter,
        description = descr,
        help = help,
        epilog  = example,
    )
    common.add_parser_yes(p)
    p.add_argument(
        '-f', "--file",
        action = "store",
        help = "filename to read package specs from",
    )
    p.add_argument(
        "--clone",
        action = "store",
        help = 'path to (or name of) existing local environment',
        metavar = 'ENV',
    )
    p.add_argument(
        "--no-default-packages",
        action = "store_true",
        help = 'ignore create_default_packages in condarc file',
    )
    common.add_parser_channels(p)
    common.add_parser_prefix(p)
    common.add_parser_quiet(p)
    p.add_argument(
        'packages',
        metavar = 'package_spec',
        action = "store",
        nargs = '*',
        help = "specification of package to install into new environment",
    )
    p.add_argument(
        "--no-deps",
        action = "store_true",
        help = "do not install dependencies",
    )
    p.add_argument(
        "--no-pip",
        action = "store_false",
        default=True,
        dest="pip",
        help = "do not use pip to install if conda fails",
    )
    p.add_argument(
        "--use-local",
        action="store_true",
        default=False,
        dest='use_local',
        help = "use locally built packages",
    )

    p.set_defaults(func=execute)


def execute(args, parser):
    install.install(args, parser, 'create')
