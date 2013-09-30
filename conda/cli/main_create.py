# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import sys
from argparse import RawDescriptionHelpFormatter

from conda.cli import common


help = "Create a new conda environment from a list of specified packages. "
descr = (help +
         "To use the created environment, use 'source activate "
         "envname' look in that directory first.  This command requires either "
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
        help = help,
        epilog  = example,
    )
    common.add_parser_yes(p)
    p.add_argument(
        '-f', "--file",
        action = "store",
        help = "filename to read package specs from",
    )
    p.add_argument(
        "--clone",
        action = "store",
        help = 'path to (or name of) existing environment',
        metavar = 'ENV',
    )
    common.add_parser_channels(p)
    common.add_parser_prefix(p)
    common.add_parser_quiet(p)
    p.add_argument(
        'package_specs',
        metavar = 'package_spec',
        action = "store",
        nargs = '*',
        help = "specification of package to install into new environment",
    )
    p.set_defaults(func=execute)


def check_prefix(prefix):
    from os.path import basename, exists
    from conda.config import root_env_name

    name = basename(prefix)
    if name.startswith('.'):
        sys.exit("Error: environment name cannot start with '.': %s" % name)
    if name == root_env_name:
        sys.exit("Error: '%s' is a reserved environment name" % name)
    if exists(prefix):
        sys.exit("Error: prefix already exists: %s" % prefix)


def print_activate(arg):
    print("#")
    print("# To activate this environment, use:")
    if sys.platform == 'win32':
        print("# > activate %s" % arg)
    else:
        print("# $ source activate %s" % arg)
        print("#")
        print("# To deactivate this environment, use:")
        print("# $ source deactivate")
    print("#")


def clone(src_arg, dst_prefix):
    import os
    from os.path import abspath, isdir

    from conda.misc import clone_env

    if os.sep in src_arg:
        src_prefix = abspath(src_arg)
        if not isdir(src_prefix):
            sys.exit('Error: could such directory: %s' % src_arg)
    else:
        src_prefix = common.find_prefix_name(src_arg)
        if src_prefix is None:
            sys.exit('Error: could not find environment: %s' % src_arg)

    print("src_prefix: %r" % src_prefix)
    print("dst_prefix: %r" % dst_prefix)
    clone_env(src_prefix, dst_prefix)


def execute(args, parser):
    import conda.config as config
    import conda.plan as plan
    from conda.api import get_index

    common.ensure_name_or_prefix(args, 'create')
    prefix = common.get_prefix(args, search=False)
    check_prefix(prefix)
    config.set_pkgs_dirs(prefix)

    if args.clone:
        if args.package_specs:
            sys.exit('Error: did not expect any arguments for --clone')
        clone(args.clone, prefix)
        print_activate(args.name if args.name else prefix)
        return

    if len(args.package_specs) == 0 and not args.file:
        sys.exit('Error: too few arguments, must supply command line '
                 'package specs or --file')

    if args.file:
        specs = common.specs_from_url(args.file)
    else:
        specs = common.specs_from_args(args.package_specs)

    common.check_specs(prefix, specs)

    channel_urls = args.channel or ()

    common.ensure_override_channels_requires_channel(args)
    index = get_index(channel_urls=channel_urls,
                      prepend=not args.override_channels)
    actions = plan.install_actions(prefix, index, specs)

    if plan.nothing_to_do(actions):
        print('No matching packages could be found, nothing to do')
        return

    print()
    print("Package plan for creating environment at %s:" % prefix)
    plan.display_actions(actions, index)

    common.confirm_yn(args)
    plan.execute_actions(actions, index, verbose=not args.quiet)

    print_activate(args.name if args.name else prefix)
