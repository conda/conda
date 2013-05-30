# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from argparse import RawDescriptionHelpFormatter

import common


help = "Install a list of packages into a specified conda environment."
descr = help + """
The arguments may be packages specifications (e.g. bitarray=0.8),
or explicit conda packages filesnames (e.g. lxml-3.2.0-py27_0.tar.bz2) which
must exist on the local filesystem.  The two types of arguments cannot be
mixed and the latter implied the --force and --no-deps options.
"""
example = """
examples:
    conda install -n myenv scipy

"""

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'install',
        formatter_class = RawDescriptionHelpFormatter,
        description = descr,
        help = help,
        epilog = example,
    )
    common.add_parser_yes(p)
    p.add_argument(
        '-f', "--force",
        action = "store_true",
        help = "force install (even when package already installed), "
               "implies --no-deps",
    )
    p.add_argument(
        "--file",
        action = "store",
        help = "read package versions from FILE",
    )
    p.add_argument(
        "--no-deps",
        action = "store_true",
        help = "do not install dependencies",
    )
    common.add_parser_prefix(p)
    common.add_parser_quiet(p)
    p.add_argument(
        'packages',
        metavar = 'package_spec',
        action = "store",
        nargs = '*',
        help = "package versions to install into conda environment",
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    import conda.plan as plan
    from conda.api import get_index


    prefix = common.get_prefix(args)

    # handle explict installs of conda packages
    if args.packages and all(s.endswith('.tar.bz2') for s in args.packages):
        from conda.misc import install_local_packages
        install_local_packages(prefix, args.packages, verbose=not args.quiet)
        return
    if any(s.endswith('.tar.bz2') for s in args.packages):
        raise RuntimeError("cannot mix specifications with conda package "
                           "filenames")

    if args.force:
        args.no_deps = True

    if args.file:
        specs = common.specs_from_file(args.file)
    else:
        specs = common.specs_from_args(args.packages)

    common.check_specs(prefix, specs)

    spec_names = set(s.split()[0] for s in specs)
    if args.no_deps:
        only_names = spec_names
    else:
        only_names = None

    index = get_index()
    actions = plan.install_actions(prefix, index, specs,
                                   force=args.force, only_names=only_names)

    if plan.nothing_to_do(actions):
        from main_list import list_packages

        regex = '|'.join('^%s$' % name for name in spec_names)
        print '# All requested packages already installed.'
        list_packages(prefix, regex)
        return

    print
    print "Package plan for installation in environment %s:" % prefix
    plan.display_actions(actions, index)

    common.confirm(args)
    plan.execute_actions(actions, index, verbose=not args.quiet)
