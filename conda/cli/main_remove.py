# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import sys

import argparse
from argparse import RawDescriptionHelpFormatter

from conda import config
from conda.cli import common
from conda.console import json_progress_bars


help = "Remove a list of packages from a specified conda environment."
descr = help + """
Normally, only the specified package is removed, and not the packages
which may depend on the package.  Hence this command should be used
with caution.
"""
example = """
examples:
    conda remove -n myenv scipy

"""

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'remove',
        formatter_class = RawDescriptionHelpFormatter,
        description = descr,
        help = help,
        epilog = example,
    )
    common.add_parser_yes(p)
    common.add_parser_json(p)
    p.add_argument(
        "--all",
        action = "store_true",
        help = "remove all packages, i.e. the entire environment",
    )
    p.add_argument(
        "--features",
        action = "store_true",
        help = "remove features (instead of packages)",
    )
    common.add_parser_no_pin(p)
    common.add_parser_channels(p)
    common.add_parser_prefix(p)
    common.add_parser_quiet(p)
    common.add_parser_use_index_cache(p)
    p.add_argument(
        "--force-pscheck",
        action = "store_true",
        help = ("force removal (when package process is running)"
                if config.platform == 'win' else argparse.SUPPRESS)
    )
    p.add_argument(
        'package_names',
        metavar = 'package_name',
        action = "store",
        nargs = '*',
        help = "package names to remove from environment",
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    import sys

    import conda.plan as plan
    from conda.cli import pscheck
    from conda.install import rm_rf, linked
    from conda import config

    if not (args.all or args.package_names):
        common.error_and_exit('no package names supplied,\n'
                              '       try "conda remove -h" for more details',
                              json=args.json,
                              error_type="ValueError")

    prefix = common.get_prefix(args)
    common.check_write('remove', prefix, json=args.json)
    common.ensure_override_channels_requires_channel(args, json=args.json)
    channel_urls = args.channel or ()
    index = common.get_index_trap(channel_urls=channel_urls,
                                  use_cache=args.use_index_cache,
                                  prepend=not args.override_channels,
                                  json=args.json)
    if args.features:
        features = set(args.package_names)
        actions = plan.remove_features_actions(prefix, index, features)

    elif args.all:
        if plan.is_root_prefix(prefix):
            common.error_and_exit('cannot remove root environment,\n'
                                  '       add -n NAME or -p PREFIX option',
                                  json=args.json,
                                  error_type="CantRemoveRoot")

        actions = {plan.PREFIX: prefix,
                   plan.UNLINK: sorted(linked(prefix))}

    else:
        specs = common.specs_from_args(args.package_names)
        if (plan.is_root_prefix(prefix) and
            common.names_in_specs(common.root_no_rm, specs)):
            common.error_and_exit('cannot remove %s from root environment' %
                                  ', '.join(common.root_no_rm),
                                  json=args.json,
                                  error_type="CantRemoveFromRoot")
        actions = plan.remove_actions(prefix, specs, pinned=args.pinned)

    if plan.nothing_to_do(actions):
        if args.all:
            rm_rf(prefix)

            if args.json:
                common.stdout_json({
                    'success': True,
                    'actions': actions
                })
            return
        common.error_and_exit('no packages found to remove from '
                              'environment: %s' % prefix,
                              json=args.json,
                              error_type="PackageNotInstalled")

    if not args.json:
        print()
        print("Package plan for package removal in environment %s:" % prefix)
        plan.display_actions(actions, index)

    if args.json and args.dry_run:
        common.stdout_json({
            'success': True,
            'dry_run': True,
            'actions': actions
        })
        return

    if not args.json:
        if not pscheck.main(args):
            common.confirm_yn(args)
    elif (sys.platform == 'win32' and not args.force_pscheck and
          not pscheck.check_processes(verbose=False)):
        common.error_and_exit("Cannot continue removal while processes "
                              "from packages are running without --force-pscheck.",
                              json=True,
                              error_type="ProcessesStillRunning")

    if args.json and not args.quiet:
        with json_progress_bars():
            plan.execute_actions(actions, index, verbose=not args.quiet)
    else:
        plan.execute_actions(actions, index, verbose=not args.quiet)

    if args.all:
        rm_rf(prefix)

    if args.json:
        common.stdout_json({
            'success': True,
            'actions': actions
        })
