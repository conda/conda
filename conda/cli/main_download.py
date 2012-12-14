# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from argparse import RawDescriptionHelpFormatter

from conda.anaconda import anaconda
from conda.planners import create_download_plan
from utils import add_parser_yes, confirm, add_parser_quiet


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'download',
        formatter_class = RawDescriptionHelpFormatter,
        description     = "Download Anaconda packages and their dependencies.",
        help            = "Download Anaconda packages and their dependencies. (ADVANCED)",
        epilog          = activate_example,
    )
    add_parser_yes(p)
    p.add_argument(
        '-f', "--force",
        action  = "store_true",
        default = False,
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
    p.set_defaults(func=execute)


def execute(args):
    conda = anaconda()

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


activate_example = '''
examples:
    conda download zeromq-2.2.0-0

'''
