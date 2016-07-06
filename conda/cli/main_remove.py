# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import errno
import logging
from argparse import RawDescriptionHelpFormatter
from os.path import join

from .common import (add_parser_help, add_parser_yes, add_parser_json, add_parser_no_pin,
                     add_parser_channels, add_parser_prefix, add_parser_quiet,
                     add_parser_no_use_index_cache, add_parser_use_index_cache,
                     add_parser_use_local, add_parser_offline, add_parser_pscheck,
                     InstalledPackages, error_and_exit, get_prefix, check_write,
                     ensure_use_local, ensure_override_channels_requires_channel,
                     get_index_trap, specs_from_args, names_in_specs, root_no_rm, stdout_json,
                     confirm_yn)
from ..config import default_prefix
from ..console import json_progress_bars
from ..compat import iteritems, iterkeys


help = "%s a list of packages from a specified conda environment."
descr = help + """

This command will also remove any package that depends on any of the
specified packages as well---unless a replacement can be found without
that dependency. If you wish to skip this dependency checking and remove
just the requested packages, add the '--force' option. Note however that
this may result in a broken environment, so use this with caution.
"""
example = """
Examples:

    conda %s -n myenv scipy

"""

uninstall_help = "Alias for conda remove.  See conda remove --help."
log = logging.getLogger(__name__)

def configure_parser(sub_parsers, name='remove'):
    if name == 'remove':
        p = sub_parsers.add_parser(
            name,
            formatter_class=RawDescriptionHelpFormatter,
            description=descr % name.capitalize(),
            help=help % name.capitalize(),
            epilog=example % name,
            add_help=False,
        )
    else:
        p = sub_parsers.add_parser(
            name,
            formatter_class=RawDescriptionHelpFormatter,
            description=uninstall_help,
            help=uninstall_help,
            epilog=example % name,
            add_help=False,
        )
    add_parser_help(p)
    add_parser_yes(p)
    add_parser_json(p)
    p.add_argument(
        "--all",
        action="store_true",
        help="%s all packages, i.e., the entire environment." % name.capitalize(),
    )
    p.add_argument(
        "--features",
        action="store_true",
        help="%s features (instead of packages)." % name.capitalize(),
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Forces removal of a package without removing packages that depend on it. "
             "Using this option will usually leave your environment in a broken and "
             "inconsistent state.",
    )
    add_parser_no_pin(p)
    add_parser_channels(p)
    add_parser_prefix(p)
    add_parser_quiet(p)
    # Putting this one first makes it the default
    add_parser_no_use_index_cache(p)
    add_parser_use_index_cache(p)
    add_parser_use_local(p)
    add_parser_offline(p)
    add_parser_pscheck(p)
    p.add_argument(
        'package_names',
        metavar='package_name',
        action="store",
        nargs='*',
        help="Package names to %s from the environment." % name,
    ).completer = InstalledPackages
    p.set_defaults(func=execute)


def execute(args, parser):
    import conda.plan as plan
    import conda.instructions as inst
    from conda.install import rm_rf, linked_data

    if not (args.all or args.package_names):
        error_and_exit('no package names supplied,\n'
                       '       try "conda remove -h" for more details',
                       json=args.json,
                       error_type="ValueError")

    prefix = get_prefix(args)
    if args.all and prefix == default_prefix:
        msg = "cannot remove current environment. deactivate and run conda remove again"
        error_and_exit(msg)
    check_write('remove', prefix, json=args.json)
    ensure_use_local(args)
    ensure_override_channels_requires_channel(args)
    channel_urls = args.channel or ()
    if not args.features and args.all:
        index = linked_data(prefix)
        index = {dist + '.tar.bz2': info for dist, info in iteritems(index)}
    else:
        index = get_index_trap(channel_urls=channel_urls,
                               prepend=not args.override_channels,
                               use_local=args.use_local,
                               use_cache=args.use_index_cache,
                               json=args.json,
                               prefix=prefix)
    specs = None
    if args.features:
        features = set(args.package_names)
        actions = plan.remove_features_actions(prefix, index, features)

    elif args.all:
        if plan.is_root_prefix(prefix):
            error_and_exit('cannot remove root environment,\n'
                           '       add -n NAME or -p PREFIX option',
                           json=args.json,
                           error_type="CantRemoveRoot")

        actions = {inst.PREFIX: prefix}
        for fkey in sorted(iterkeys(index)):
            plan.add_unlink(actions, fkey[:-8])

    else:
        specs = specs_from_args(args.package_names)
        if (plan.is_root_prefix(prefix) and names_in_specs(root_no_rm, specs)):
            error_and_exit('cannot remove %s from root environment' %
                           ', '.join(root_no_rm),
                           json=args.json,
                           error_type="CantRemoveFromRoot")
        actions = plan.remove_actions(prefix, specs, index=index,
                                      force=args.force, pinned=args.pinned)

    if plan.nothing_to_do(actions):
        if args.all:
            rm_rf(prefix)

            if args.json:
                stdout_json({
                    'success': True,
                    'actions': actions
                })
            return
        error_and_exit('no packages found to remove from '
                       'environment: %s' % prefix,
                       json=args.json,
                       error_type="PackageNotInstalled")

    if not args.json:
        print()
        print("Package plan for package removal in environment %s:" % prefix)
        plan.display_actions(actions, index)

    if args.json and args.dry_run:
        stdout_json({
            'success': True,
            'dry_run': True,
            'actions': actions
        })
        return

    if not args.json:
        confirm_yn(args)

    if args.json and not args.quiet:
        with json_progress_bars():
            plan.execute_actions(actions, index, verbose=not args.quiet)
    else:
        plan.execute_actions(actions, index, verbose=not args.quiet)
        if specs:
            try:
                with open(join(prefix, 'conda-meta', 'history'), 'a') as f:
                    f.write('# remove specs: %s\n' % specs)
            except IOError as e:
                if e.errno == errno.EACCES:
                    log.debug("Can't write the history file")
                else:
                    raise

    if args.all:
        rm_rf(prefix)

    if args.json:
        stdout_json({
            'success': True,
            'actions': actions
        })
