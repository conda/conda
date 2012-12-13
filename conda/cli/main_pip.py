# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from conda.builder.packup import pip
from utils import add_parser_prefix, get_prefix

descr = "Call pip and create a conda package in an environment. (ADVANCED)"


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser('pip', description=descr, help=descr)

    add_parser_prefix(p)

    p.add_argument(
        'names',
        action  = "store",
        metavar = 'name',
        nargs   = '+',
        help    = "name of package to pip install",
    )
    p.set_defaults(func=execute)


def execute(args):
    prefix = get_prefix(args)

    for pkg_name in args.names:
        pip(prefix, pkg_name)
