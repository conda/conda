# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

from argparse import RawDescriptionHelpFormatter

from conda.cli import common


descr = "Update conda packages."
example = """
examples:
    conda update -p ~/anaconda/envs/myenv scipy

"""

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'update',
        formatter_class = RawDescriptionHelpFormatter,
        description = descr,
        help = descr,
        epilog = example,
    )
    common.add_parser_yes(p)
    common.add_parser_prefix(p)
    common.add_parser_quiet(p)
    p.add_argument(
        'pkg_names',
        metavar = 'package_name',
        action = "store",
        nargs = '*',
        help = "names of packages to update",
    )
    common.add_parser_channels(p)
    p.set_defaults(func=execute)


def execute(args, parser):
    import sys

    import conda.install as ci
    import conda.config as config
    import conda.plan as plan
    from conda.api import get_index

    from conda.cli import pscheck


    prefix = common.get_prefix(args)
    if len(args.pkg_names) == 0:
        sys.exit("""Error: no package names supplied
# If you want to update to a newer version of Anaconda, type:
#
# $ conda update --prefix %s anaconda
""" % prefix)
    config.set_pkgs_dirs(prefix)
    linked = set(ci.name_dist(d) for d in ci.linked(prefix))
    for name in args.pkg_names:
        common.arg2spec(name)
        if '=' in name:
            sys.exit("Invalid package name: '%s'" % (name))
        if name not in linked:
            sys.exit("Error: package '%s' is not installed in %s" %
                     (name, prefix))

    common.ensure_override_channels_requires_channel(args)
    channel_urls = args.channel or ()
    index = get_index(channel_urls=channel_urls,
                      prepend=not args.override_channels)
    actions = plan.install_actions(prefix, index, args.pkg_names)

    if plan.nothing_to_do(actions):
        from conda.cli.main_list import list_packages

        regex = '^(%s)$' %  '|'.join(args.pkg_names)
        print('# All packages already at latest version, nothing to do.')
        list_packages(prefix, regex)
        return

    print("Updating conda environment at %s" % prefix)
    plan.display_actions(actions, index)
    common.check_write('update', prefix)

    if not pscheck.main(args):
        common.confirm_yn(args)

    plan.execute_actions(actions, index, verbose=not args.quiet)
