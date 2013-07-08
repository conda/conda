# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

from argparse import RawDescriptionHelpFormatter

import common


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
    common.add_parser_yes(p)
    p.add_argument(
        '-f', "--file",
        action = "store",
        help = "filename to read package specs from",
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


def execute(args, parser):
    import sys
    from os.path import exists

    import conda.plan as plan
    from conda.api import get_index


    if len(args.package_specs) == 0 and not args.file:
        sys.exit('Error: too few arguments, must supply command line '
                 'package specs or --file')

    common.ensure_name_or_prefix(args, 'create')
    prefix = common.get_prefix(args)

    if exists(prefix):
        if args.prefix:
            raise RuntimeError("'%s' already exists, must supply new "
                               "directory for -p/--prefix" % prefix)
        else:
            raise RuntimeError("'%s' already exists, must supply new "
                               "directory for -n/--name" % prefix)

    if args.file:
        specs = common.specs_from_file(args.file)
    else:
        specs = common.specs_from_args(args.package_specs)

    common.check_specs(prefix, specs)

    channel_urls = args.channel or ()

    common.ensure_override_channels_requires_channel(args)
    index = get_index(channel_urls=channel_urls, prepend=not args.override_channels)
    actions = plan.install_actions(prefix, index, specs)

    if plan.nothing_to_do(actions):
        print 'No matching packages could be found, nothing to do'
        return

    print
    print "Package plan for creating environment at %s:" % prefix
    plan.display_actions(actions, index)

    common.confirm_yn(args)
    plan.execute_actions(actions, index, verbose=not args.quiet)

    if sys.platform != 'win32':
        activate_name = prefix
        if args.name:
            activate_name = args.name
        print "#"
        print "# To activate this environment, use:"
        print "# $ source activate %s" % activate_name
        print "#"
        print "# To deactivate this environment, use:"
        print "# $ source deactivate"
        print "#"
