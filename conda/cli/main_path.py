# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from os.path import abspath, join
import re

from config import ROOT_DIR


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'path',
        description     = "Display the full path to a named Anaconda environment.",
        help            = "Display the full path to a named Anaconda environment.",
    )
    p.add_argument(
        '-n', "--name",
        action  = "store",
        help    = "name of directory (in %s/envs) to display full path to" % ROOT_DIR,
    )
    p.set_defaults(func=execute)


def execute(args):
    if args.name:
        prefix = join(ROOT_DIR, 'envs', args.name)
    else:
        prefix = abspath(ROOT_DIR)

    print join(prefix, 'bin')