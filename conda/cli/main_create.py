# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from argparse import RawDescriptionHelpFormatter

from utils import (add_parser_prefix, get_prefix, add_parser_yes, confirm,
                   add_parser_quiet)


descr = ("Create a new conda environment from a list of specified "
         "packages.  To use the created environment, invoke the binaries "
         "in that environment's bin directory or adjust your PATH to "
         "look in that directory first.  This command requires either "
         "the -n NAME or -p PREFIX option.")

example = """
examples:
    conda create -n myenv sqlite

"""

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'create',
        formatter_class = RawDescriptionHelpFormatter,
        description = descr,
        help = descr,
        epilog  = example,
    )
    add_parser_yes(p)
    p.add_argument(
        '-f', "--file",
        action = "store",
        help = "filename to read package specs from",
    )
    add_parser_prefix(p)
    add_parser_quiet(p)
    p.add_argument(
        'package_specs',
        metavar = 'package_spec',
        action = "store",
        nargs = '*',
        help = "specification of package to install into new environment",
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    import os
    import sys
    from os.path import abspath, exists

    import conda.plan as plan
    from conda.api import get_index


    if len(args.package_specs) == 0 and not args.file:
        raise RuntimeError('too few arguments, must supply command line '
                           'package specs or --file')

    if (not args.name) and (not args.prefix):
        raise RuntimeError('either -n NAME or -p PREFIX option required, '
                           'try "conda create -h" for more details')

    prefix = get_prefix(args)

    if exists(prefix):
        if args.prefix:
            raise RuntimeError("'%s' already exists, must supply new "
                               "directory for -p/--prefix" % prefix)
        else:
            raise RuntimeError("'%s' already exists, must supply new "
                               "directory for -n/--name" % prefix)

    if args.file:
        try:
            f = open(abspath(args.file))
            spec_strings = [line for line in f]
            f.close()
        except:
            raise RuntimeError('could not read file: %s', args.file)
    else:
        spec_strings = args.package_specs

    if any(s == 'conda' or s.startswith('conda=') for s in spec_strings):
        raise RuntimeError("Package 'conda' may only be installed in the "
                           "root environment")

    if len(spec_strings) == 0:
        raise RuntimeError('no package specifications supplied')

    index = get_index()
    actions = plan.install_actions(prefix, index, spec_strings)

    if plan.nothing_to_do(actions):
        print 'No matching packages could be found, nothing to do'
        return

    print
    print "Package plan for creating environment at %s:" % prefix
    plan.display_actions(actions)

    confirm(args)
    os.makedirs(prefix)
    # env = conda.lookup_environment(prefix) ???
    plan.execute_actions(actions, index, enable_progress=not args.quiet)

    if sys.platform != 'win32':
        activate_name = prefix
        if args.name:
            activate_name = args.name
        print "#"
        for cmd in ('activate', 'deactivate'):
            print "# To %s this environment, use:" % cmd
            print "# $ source %s %s" % (cmd, activate_name)
            print "#"
