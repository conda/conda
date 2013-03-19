# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from argparse import RawDescriptionHelpFormatter
from os import listdir
from os.path import join
from shutil import rmtree

from conda.anaconda import Anaconda
from conda.planners import create_download_plan
from utils import add_parser_yes, confirm, add_parser_quiet


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'local',
        formatter_class = RawDescriptionHelpFormatter,
        description     = "Add and remove Anaconda packages from local availability. ",
        help            = "Add and remove Anaconda packages from local availability. (ADVANCED)",
        epilog          = local_example,
    )
    add_parser_yes(p)
    p.add_argument(
        '-f', "--force",
        action  = "store_true",
        help    = "force package downloads even when specific package is already available",
    )
    add_parser_quiet(p)
    p.add_argument(
        'canonical_names',
        action  = "store",
        metavar = 'canonical_name',
        nargs   = '+',
        help    = "canonical name of package to download and make locally available",
    )
    drgroup = p.add_mutually_exclusive_group()
    drgroup.add_argument(
        '-d', "--download",
        action  = "store_true",
        help    = "download Anaconda packages and their dependencies.",
    )
    drgroup.add_argument(
        '-r', "--remove",
        action  = "store_true",
        help    = "remove packages from local availability.",
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    conda = Anaconda()

    if args.download:
        plan = create_download_plan(conda, args.canonical_names, args.force)

        if plan.empty():
            if len(args.canonical_names) == 1:
                print "Could not find package with canonical name '%s' to download (already downloaded or unknown)." % args.canonical_names[0]
            else:
                print 'Could not find packages with canonical names %s to download (already downloaded or unknown).' % args.canonical_names
            return

        print plan

        confirm(args)

        # pass default environment because some env is required,
        # but it is unused here
        plan.execute(conda.default_environment, not args.quiet)

    elif args.remove:
        to_remove = set(listdir(conda.packages_dir)) & set(args.canonical_names)

        if not to_remove:
            if len(args.canonical_names) == 1:
                print "Could not find package with canonical name '%s' to remove (already removed or unknown)." % args.canonical_names[0]
            else:
                print 'Could not find packages with canonical names %s to remove.' % args.canonical_names
            return

        print "    The following packages were found and will be removed from local availability:"
        print
        for pkg_name in to_remove:
            print "         %s" % pkg_name
        print

        confirm(args)

        for pkg_name in to_remove:
            rmtree(join(conda.packages_dir, pkg_name))

    else:
        raise RuntimeError("One of -d/--download or -r/--remove is required.")

local_example = '''
examples:
    conda local --download zeromq-2.2.0-0

    conda local --remove zeromq-2.2.0-0
'''
