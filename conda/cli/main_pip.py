# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from os.path import abspath, expanduser, join

from conda.config import ROOT_DIR
from conda.builder.packup import pip

descr = "Call pip and create a conda package in an environment. (ADVANCED)"


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser('pip', description=descr, help=descr)

    npgroup = p.add_mutually_exclusive_group()
    npgroup.add_argument(
        '-n', "--name",
        action  = "store",
        help    = "name of new directory (in %s/envs) to list packages in" %
                  ROOT_DIR,
    )
    npgroup.add_argument(
        '-p', "--prefix",
        action  = "store",
        default = ROOT_DIR,
        help    = "full path to Anaconda environment to list packages in "
                  "(default: %s)" % ROOT_DIR,
    )
    p.add_argument(
        'names',
        action  = "store",
        metavar = 'name',
        nargs   = '+',
        help    = "name of package to pip install",
    )
    p.set_defaults(func=execute)


def execute(args):
    if args.name:
        prefix = join(ROOT_DIR, 'envs', args.name)
    else:
        prefix = abspath(expanduser(args.prefix))

    for pkg_name in args.names:
        pip(prefix, pkg_name)
