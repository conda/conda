# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from os.path import abspath, expanduser, join

from config import ROOT_DIR

from conda.builder.packup import make_tarbz2


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'package',
        description = "Create a conda package in an Anaconda environment. (ADVANCED)",
        help        = "Create a conda package in an Anaconda environment. (ADVANCED)",
    )
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
        "--pkg-name",
        action  = "store",
        default = "unknown",
        help    = "package name of the created package",
    )
    p.add_argument(
        "--pkg-version",
        action  = "store",
        default = "0.0",
        help    = "package version of the created package",
    )
    p.add_argument(
        "--pkg-build",
        action  = "store",
        default = 0,
        help    = "package build number of the created package",
    )
    p.set_defaults(func=execute)


def execute(args):
    if args.name:
        prefix = join(ROOT_DIR, 'envs', args.name)
    else:
        prefix = abspath(expanduser(args.prefix))

    fn = make_tarbz2(prefix,
                     name = args.pkg_name,
                     version = args.pkg_version,
                     build_number = args.pkg_build)
    if fn is not None:
        print '%s created successfully' % fn
