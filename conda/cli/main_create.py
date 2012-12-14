# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from argparse import RawDescriptionHelpFormatter
from os import makedirs
from os.path import abspath, exists

from conda.anaconda import anaconda
from conda.planners import create_create_plan
from utils import add_parser_prefix, get_prefix, add_parser_yes, confirm


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'create',
        formatter_class = RawDescriptionHelpFormatter,
        description     = "Create an Anaconda environment at a specified prefix from a list of package specifications.",
        help            = "Create an Anaconda environment at a specified prefix from a list of package specifications.",
        epilog          = activate_example,
    )
    add_parser_yes(p)
    p.add_argument(
        '-f', "--file",
        action  = "store",
        help    = "filename to read package specs from",
    )
    add_parser_prefix(p)
    p.add_argument(
        "--progress-bar",
        action  = "store",
        default = "yes",
        choices = ["yes", "no"],
        help    = "display progress bar for package downloads (default: yes)",
    )
    p.add_argument(
        'package_specs',
        metavar = 'package_spec',
        action  = "store",
        nargs   ='*',
        help    = "package specification of package to install into new Anaconda environment",
    )
    p.set_defaults(func=execute)


def execute(args):
    if len(args.package_specs) == 0 and not args.file:
        raise RuntimeError('too few arguments, must supply command line package specs or --file')

    conda = anaconda()

    prefix = get_prefix(args)

    if exists(prefix):
        if args.prefix:
            raise RuntimeError("'%s' already exists, must supply new directory for -p/--prefix" % prefix)
        else:
            raise RuntimeError("'%s' already exists, must supply new directory for -n/--name" % prefix)

    if args.file:
        try:
            f = open(abspath(args.file))
            spec_strings = [line for line in f]
            f.close()
        except:
            raise RuntimeError('could not read file: %s', args.file)
    else:
        spec_strings = args.package_specs

    if any(s.startswith('conda') for s in spec_strings):
        raise RuntimeError("Package 'conda' may only be installed in the "
                           "root environment")

    if len(spec_strings) == 0:
        raise RuntimeError('no package specifications supplied')

    plan = create_create_plan(prefix, conda, spec_strings)

    if plan.empty():
        print 'No matching packages could be found, nothing to do'
        return

    print
    print "Package plan for creating environment at %s:" % prefix

    print plan

    confirm(args)
    makedirs(prefix)
    env = conda.lookup_environment(prefix)

    plan.execute(env, args.progress_bar=="yes")

activate_example = '''
examples:
    conda create -n myenv sqlite

'''
