# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import os
from os.path import abspath, exists, expanduser, join


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'init',
        description = "Bootstrap Anaconda installation.",
        help        = "Bootstrap Anaconda installation.",
    )
    p.add_argument(
        '-p', "--prefix",
        action  = "store",
        help    = "directory to install Anaconda into",
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    if not args.prefix:
        raise RuntimeError("Must provide directory location to install into.")

    prefix = abspath(expanduser(args.prefix))

    if exists(prefix):
        raise RuntimeError("Install directory '%s' already exists." % prefix)

    os.makedirs(prefix)
    for sd in 'envs', 'pkgs':
        os.mkdir(join(prefix, sd))

    print "Anaconda initalized into directory '%s'" % prefix
