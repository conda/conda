# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

from argparse import RawDescriptionHelpFormatter

from conda.cli import common, install


descr = "Update conda packages."
example = """
examples:
    conda update -p ~/anaconda/envs/myenv scipy

"""

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'update',
        formatter_class = RawDescriptionHelpFormatter,
        description = descr,
        help = descr,
        epilog = example,
    )
    common.add_parser_yes(p)
    common.add_parser_prefix(p)
    common.add_parser_quiet(p)
    p.add_argument(
        'packages',
        metavar = 'package_name',
        action = "store",
        nargs = '*',
        help = "names of packages to update",
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
    common.add_parser_channels(p)
    p.set_defaults(func=execute)


def execute(args, parser):
    install.install(args, parser, 'update')
