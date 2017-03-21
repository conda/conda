# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import absolute_import, division, print_function, unicode_literals

from argparse import RawDescriptionHelpFormatter
import errno
import logging
from os.path import join
import sys

from collections import defaultdict

from .common import (InstalledPackages, add_parser_channels, add_parser_help, add_parser_json,
                     add_parser_no_pin, add_parser_no_use_index_cache, add_parser_offline,
                     add_parser_prefix, add_parser_pscheck, add_parser_quiet,
                     add_parser_use_index_cache, add_parser_use_local, add_parser_yes, confirm_yn,
                     ensure_override_channels_requires_channel,
                     ensure_use_local, names_in_specs, specs_from_args, stdout_json)
from .install import check_write
from ..base.constants import ROOT_NO_RM
from ..base.context import context
from ..common.compat import iteritems, iterkeys
from ..common.path import is_private_env_path, prefix_to_env_name
from ..console import json_progress_bars
from ..core.index import get_index
from ..exceptions import CondaEnvironmentError, CondaValueError, PackageNotFoundError
from ..gateways.disk.delete import delete_trash
from ..resolve import Resolve, MatchSpec

try:
    from cytoolz.itertoolz import groupby
except ImportError:
    from .._vendor.toolz.itertoolz import groupby

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


def create_prefix_spec_map_with_deps(r, specs, default_prefix):
    from ..core.envs_manager import EnvsDirectory
    ed = EnvsDirectory(join(context.root_prefix, 'envs'))
    get_env = lambda s: ed.get_registered_preferred_env(MatchSpec(s).name)
    env_spec_map = groupby(get_env, specs)
    for spec in specs:
        ed.get_registered_preferred_env(MatchSpec(spec).name)


    prefix_spec_map = {}
    for spec in specs:
        spec_prefix = ed.prefix_if_in_private_env(spec)
        spec_prefix = spec_prefix if spec_prefix is not None else default_prefix
        if spec_prefix in prefix_spec_map.keys():
            prefix_spec_map[spec_prefix].add(spec)
        else:
            prefix_spec_map[spec_prefix] = {spec}

        if is_private_env_path(spec_prefix):
            from ..core.linked_data import linked_data
            linked = linked_data(spec_prefix)
            for linked_spec in linked:
                if not linked_spec.name.startswith(spec) and r.depends_on(spec, linked_spec):
                    prefix_spec_map[spec_prefix].add(linked_spec.name)
    import pdb; pdb.set_trace()
    return prefix_spec_map


def execute(args, parser):
    import conda.plan as plan
    import conda.instructions as inst
    from conda.gateways.disk.delete import rm_rf
    from conda.core.linked_data import linked_data

    if not (args.all or args.package_names):
        raise CondaValueError('no package names supplied,\n'
                              '       try "conda remove -h" for more details')

    prefix = context.prefix_w_legacy_search
    if args.all and prefix == context.default_prefix:
        msg = "cannot remove current environment. deactivate and run conda remove again"
        raise CondaEnvironmentError(msg)
    check_write('remove', prefix, json=context.json)
    ensure_use_local(args)
    ensure_override_channels_requires_channel(args)
    if not args.features and args.all:
        index = linked_data(prefix)
        index = {dist: info for dist, info in iteritems(index)}
    else:
        index = get_index(channel_urls=context.channels,
                          prepend=not args.override_channels,
                          use_local=args.use_local,
                          use_cache=args.use_index_cache,
                          prefix=prefix)
    specs = None
    if args.features:
        specs = ['@' + f for f in set(args.package_names)]
        actions = plan.remove_actions(prefix, specs, index, pinned=context.respect_pinned)
        actions['ACTION'] = 'REMOVE_FEATURE'
        action_groups = (actions, index),
    elif args.all:
        if plan.is_root_prefix(prefix):
            raise CondaEnvironmentError('cannot remove root environment,\n'
                                        '       add -n NAME or -p PREFIX option')
        actions = defaultdict(list)
        actions[inst.PREFIX] = prefix
        for dist in sorted(iterkeys(index)):
            plan.add_unlink(actions, dist)
        actions['ACTION'] = 'REMOVE_ALL'
        action_groups = (actions, index),
    elif prefix == context.root_prefix and not context.prefix_specified:
        from ..core.envs_manager import EnvsDirectory
        ed = EnvsDirectory(join(context.root_prefix, 'envs'))
        get_env = lambda s: ed.get_registered_preferred_env(MatchSpec(s).name)
        specs = specs_from_args(args.package_names)
        env_spec_map = groupby(get_env, specs)
        action_groups = []
        for env_name, spcs in iteritems(env_spec_map):
            pfx = ed.to_prefix(env_name)
            r = plan.get_resolve_object(index.copy(), pfx)
            specs_to_remove = tuple(MatchSpec(s) for s in spcs)
            prune = pfx != context.root_prefix
            dists_for_unlinking, dists_for_linking = plan.solve_for_actions(
                pfx, r,
                specs_to_remove=specs_to_remove, prune=prune,
            )
            actions = plan.get_blank_actions(pfx)
            actions['UNLINK'].extend(dists_for_unlinking)
            actions['LINK'].extend(dists_for_linking)
            actions['SPECS'].extend(s.spec for s in specs_to_remove)
            actions['ACTION'] = 'REMOVE'
            action_groups.append((actions, r.index))
        action_groups = tuple(action_groups)

    else:
        specs = specs_from_args(args.package_names)
        if (context.conda_in_root and plan.is_root_prefix(prefix) and names_in_specs(
                ROOT_NO_RM, specs) and not args.force):
            raise CondaEnvironmentError('cannot remove %s from root environment' %
                                        ', '.join(ROOT_NO_RM))
        action_groups = (plan.remove_actions(prefix, list(specs), index=index, force=args.force,
                                               pinned=context.respect_pinned), index),


    delete_trash()
    if any(plan.nothing_to_do(x[0]) for x in action_groups):
        if args.all:
            print("\nRemove all packages in environment %s:\n" % prefix, file=sys.stderr)
            if not context.json:
                confirm_yn(args)
            rm_rf(prefix)

            if context.json:
                stdout_json({
                    'success': True,
                    'actions': tuple(x[0] for x in action_groups)
                })
            return
        error_message = 'no packages found to remove from environment: %s' % prefix
        raise PackageNotFoundError(error_message)
    if not context.json:
        for actions, ndx in action_groups:
            print()
            print("Package plan for package removal in environment %s:" % actions["PREFIX"])
            plan.display_actions(actions, ndx)
    elif context.json and args.dry_run:
        stdout_json({
            'success': True,
            'dry_run': True,
            'actions': tuple(x[0] for x in action_groups),
        })
        return

    if not context.json:
        confirm_yn(args)

    for actions, ndx in action_groups:
        if context.json and not context.quiet:
            with json_progress_bars():
                plan.execute_actions(actions, ndx, verbose=not context.quiet)
        else:
            plan.execute_actions(actions, ndx, verbose=not context.quiet)

        target_prefix = actions["PREFIX"]
        if is_private_env_path(target_prefix) and linked_data(target_prefix) == {}:
            rm_rf(target_prefix)

    if args.all:
        rm_rf(prefix)

    if context.json:
        stdout_json({
            'success': True,
            'actions': tuple(x[0] for x in action_groups),
        })
