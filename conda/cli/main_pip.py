# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import sys

from . import common
from . import main_install

descr = "Call pip and create a conda package in an environment. (DEPRECATED)"


def configure_parser(sub_parsers):
    from common import add_parser_yes
    p = sub_parsers.add_parser('pip', description=descr, help=descr)

    common.add_parser_prefix(p)

    p.add_argument(
        'packages',
        action  = "store",
        metavar = 'name',
        nargs   = '+',
        help    = "name of package to pip install",
    )
    add_parser_yes(p)
    p.set_defaults(func=execute)


def execute(args, parser):
    from conda.builder.commands import pip
    from conda.api import get_index
    from conda.resolve import Resolve

    prefix = common.get_prefix(args)

    index = get_index()
    r = Resolve(index)
    for pkg_request in args.packages:
        if pkg_request.lower() in r.groups:
            print( "The package {package} is already available in conda. "
                   "You can install it with 'conda install "
                   "{package_lower}'.").format(
                package=pkg_request,
                package_lower=pkg_request.lower())

            choice = common.confirm(args, "Install with conda, install with "
                "pip, or abort", ('conda', 'pip', 'abort'), default='conda')
            if choice == 'abort':
                sys.exit(1)
            if choice == 'conda':
                # conda pip options do not correspond to conda install options
                args.force = False
                args.file = None
                args.no_deps = False
                args.override_channels = False
                args.channel = None
                main_install.execute(args, parser)
                continue

        pip(prefix, pkg_request)
