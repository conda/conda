# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

from argparse import RawDescriptionHelpFormatter

from conda.cli import common, install


help = "Install a list of packages into a specified conda environment."
descr = help + """
The arguments may be packages specifications (e.g. bitarray=0.8),
or explicit conda packages filesnames (e.g. lxml-3.2.0-py27_0.tar.bz2) which
must exist on the local filesystem.  The two types of arguments cannot be
mixed and the latter implies the --force and --no-deps options.
"""
example = """
examples:
    conda install -n myenv scipy

"""

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'install',
        formatter_class = RawDescriptionHelpFormatter,
        description = descr,
        help = help,
        epilog = example,
    )
    common.add_parser_yes(p)
    p.add_argument(
        '-f', "--force",
        action = "store_true",
        help = "force install (even when package already installed), "
               "implies --no-deps",
    )
    p.add_argument(
        "--file",
        action = "store",
        help = "read package versions from FILE",
    )
    p.add_argument(
        "--no-deps",
        action = "store_true",
        help = "do not install dependencies",
    )
    p.add_argument(
        '-m', "--mkdir",
        action = "store_true",
        help = "create prefix directory if necessary",
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
    common.add_parser_prefix(p)
    common.add_parser_quiet(p)
    p.add_argument(
        'packages',
        metavar = 'package_spec',
        action = "store",
        nargs = '*',
        help = "package versions to install into conda environment",
    )
    p.set_defaults(func=execute)




def execute(args, parser):
    install.install(args, parser, 'install')
