# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from argparse import RawDescriptionHelpFormatter

from conda.config import ROOT_DIR, PACKAGES_DIR
from conda.anaconda import Anaconda
from conda.planners import create_install_plan
from utils import (
    add_parser_prefix, add_parser_quiet, add_parser_yes, confirm, get_prefix, license_check_warn
)


descr = "Install a list of packages into a specified Anaconda environment."


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'install',
        formatter_class = RawDescriptionHelpFormatter,
        description = descr,
        help        = descr,
        epilog      = activate_example,
    )
    add_parser_yes(p)
    p.add_argument(
        '-f', "--file",
        action  = "store",
        help    = "filename to read package versions from",
    )
    add_parser_prefix(p)
    add_parser_quiet(p)
    p.add_argument(
        'packages',
        metavar = 'package_version',
        action  = "store",
        nargs   = '*',
        help    = "package versions to install into Anaconda environment",
    )
    p.set_defaults(func=execute)


def execute(args):
    if len(args.packages) == 0 and not args.file:
        raise RuntimeError('too few arguments, must supply command line '
                           'package specifications or --file')

    conda = Anaconda()

    license_check_warn()

    prefix = get_prefix(args)

    env = conda.lookup_environment(prefix)

    if args.file:
        try:
            req_strings = []
            with open(args.file) as fi:
                for line in fi:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        req_strings.append(line)
        except IOError:
            raise RuntimeError('could not read file: %s' % args.file)
    else:
        req_strings = args.packages

    if prefix != ROOT_DIR and any(s.startswith('conda') for s in req_strings):
        raise RuntimeError("package 'conda' may only be installed in the "
                           "root environment")

    if len(req_strings) == 0:
        raise RuntimeError('no package specifications supplied')

    if all(s.endswith('.tar.bz2') for s in req_strings):
        from conda.install import install_local_package
        for path in req_strings:
            install_local_package(path, PACKAGES_DIR, prefix)
        return

    if any(s.endswith('.tar.bz2') for s in req_strings):
        raise RuntimeError("mixing specifications and filename not supported")

    conda = Anaconda()

    plan = create_install_plan(env, req_strings)

    if plan.empty():
        print 'All requested packages already installed into environment: %s' % prefix
        return

    print
    print "Package plan for installation in environment %s:" % prefix
    print plan

    confirm(args)

    plan.execute(env, not args.quiet)


activate_example = '''
examples:
    conda install -n myenv scipy

'''
