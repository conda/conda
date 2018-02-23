# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import defaultdict
import logging
from os.path import isdir
import sys

from .common import check_non_admin, confirm_yn, specs_from_args, stdout_json
from .install import handle_txn
from ..base.context import context
from ..common.compat import iteritems, iterkeys
from ..core.envs_manager import unregister_env
from ..core.prefix_data import linked_data
from ..core.solve import Solver
from ..exceptions import CondaEnvironmentError, CondaValueError
from ..gateways.disk.delete import delete_trash, rm_rf
from ..gateways.disk.test import is_conda_environment
from ..instructions import PREFIX
from ..models.match_spec import MatchSpec
from ..plan import (add_unlink, display_actions)

log = logging.getLogger(__name__)


def execute(args, parser):

    if not (args.all or args.package_names):
        raise CondaValueError('no package names supplied,\n'
                              '       try "conda remove -h" for more details')

    prefix = context.target_prefix
    check_non_admin()

    if args.all and prefix == context.default_prefix:
        msg = "cannot remove current environment. deactivate and run conda remove again"
        raise CondaEnvironmentError(msg)
    if args.all and not isdir(prefix):
        # full environment removal was requested, but environment doesn't exist anyway
        return 0

    if not is_conda_environment(prefix):
        from ..exceptions import EnvironmentLocationNotFound
        raise EnvironmentLocationNotFound(prefix)

    delete_trash()
    if args.all:
        if prefix == context.root_prefix:
            raise CondaEnvironmentError('cannot remove root environment,\n'
                                        '       add -n NAME or -p PREFIX option')
        print("\nRemove all packages in environment %s:\n" % prefix, file=sys.stderr)

        index = linked_data(prefix)
        index = {dist: info for dist, info in iteritems(index)}

        actions = defaultdict(list)
        actions[PREFIX] = prefix
        for dist in sorted(iterkeys(index)):
            add_unlink(actions, dist)
        actions['ACTION'] = 'REMOVE_ALL'
        action_groups = (actions, index),

        if not context.json:
            display_actions(actions, index)
            confirm_yn()
        rm_rf(prefix)
        unregister_env(prefix)

        if context.json:
            stdout_json({
                'success': True,
                'actions': tuple(x[0] for x in action_groups)
            })
        return

    else:
        if args.features:
            specs = tuple(MatchSpec(track_features=f) for f in set(args.package_names))
        else:
            specs = specs_from_args(args.package_names)
        channel_urls = ()
        subdirs = ()
        solver = Solver(prefix, channel_urls, subdirs, specs_to_remove=specs)
        txn = solver.solve_for_transaction(force_remove=args.force)
        handle_txn(txn, prefix, args, False, True)

    # Keep this code for dev reference until private envs can be re-enabled in
    # Solver.solve_for_transaction

    # specs = None
    # if args.features:
    #     specs = [MatchSpec(track_features=f) for f in set(args.package_names)]
    #     actions = remove_actions(prefix, specs, index, pinned=not context.ignore_pinned)
    #     actions['ACTION'] = 'REMOVE_FEATURE'
    #     action_groups = (actions, index),
    # elif args.all:
    #     if prefix == context.root_prefix:
    #         raise CondaEnvironmentError('cannot remove root environment,\n'
    #                                     '       add -n NAME or -p PREFIX option')
    #     actions = defaultdict(list)
    #     actions[PREFIX] = prefix
    #     for dist in sorted(iterkeys(index)):
    #         add_unlink(actions, dist)
    #     actions['ACTION'] = 'REMOVE_ALL'
    #     action_groups = (actions, index),
    # elif prefix == context.root_prefix and not context.prefix_specified:
    #     from ..core.envs_manager import EnvsDirectory
    #     ed = EnvsDirectory(join(context.root_prefix, 'envs'))
    #     get_env = lambda s: ed.get_registered_preferred_env(MatchSpec(s).name)
    #     specs = specs_from_args(args.package_names)
    #     env_spec_map = groupby(get_env, specs)
    #     action_groups = []
    #     for env_name, spcs in iteritems(env_spec_map):
    #         pfx = ed.to_prefix(env_name)
    #         r = get_resolve_object(index.copy(), pfx)
    #         specs_to_remove = tuple(MatchSpec(s) for s in spcs)
    #         prune = pfx != context.root_prefix
    #         dists_for_unlinking, dists_for_linking = solve_for_actions(
    #             pfx, r,
    #             specs_to_remove=specs_to_remove, prune=prune,
    #         )
    #         actions = get_blank_actions(pfx)
    #         actions['UNLINK'].extend(dists_for_unlinking)
    #         actions['LINK'].extend(dists_for_linking)
    #         actions['SPECS'].extend(text_type(s) for s in specs_to_remove)
    #         actions['ACTION'] = 'REMOVE'
    #         action_groups.append((actions, r.index))
    #     action_groups = tuple(action_groups)
    # else:
    #     specs = specs_from_args(args.package_names)
    #     if sys.prefix == abspath(prefix) and names_in_specs(ROOT_NO_RM, specs) and not args.force:  # NOQA
    #         raise CondaEnvironmentError('cannot remove %s from root environment' %
    #                                     ', '.join(ROOT_NO_RM))
    #     action_groups = (remove_actions(prefix, list(specs), index=index,
    #                                     force=args.force,
    #                                     pinned=not context.ignore_pinned,
    #                                     ), index),
    #
    #
    # delete_trash()
    # if any(nothing_to_do(x[0]) for x in action_groups):
    #     if args.all:
    #         print("\nRemove all packages in environment %s:\n" % prefix, file=sys.stderr)
    #         if not context.json:
    #             confirm_yn(args)
    #         rm_rf(prefix)
    #
    #         if context.json:
    #             stdout_json({
    #                 'success': True,
    #                 'actions': tuple(x[0] for x in action_groups)
    #             })
    #         return
    #
    #     pkg = str(args.package_names).replace("['", "")
    #     pkg = pkg.replace("']", "")
    #
    #     error_message = "No packages named '%s' found to remove from environment." % pkg
    #     raise PackageNotFoundError(error_message)
    # if not context.json:
    #     for actions, ndx in action_groups:
    #         print()
    #         print("Package plan for package removal in environment %s:" % actions["PREFIX"])
    #         display_actions(actions, ndx)
    # elif context.json and args.dry_run:
    #     stdout_json({
    #         'success': True,
    #         'dry_run': True,
    #         'actions': tuple(x[0] for x in action_groups),
    #     })
    #     return
    #
    # if not context.json:
    #     confirm_yn(args)
    #
    # for actions, ndx in action_groups:
    #     if context.json and not context.quiet:
    #         with json_progress_bars():
    #             execute_actions(actions, ndx, verbose=not context.quiet)
    #     else:
    #         execute_actions(actions, ndx, verbose=not context.quiet)
    #
    #     target_prefix = actions["PREFIX"]
    #     if is_private_env_path(target_prefix) and linked_data(target_prefix) == {}:
    #         rm_rf(target_prefix)
    #
    # if args.all:
    #     rm_rf(prefix)
    #
    # if context.json:
    #     stdout_json({
    #         'success': True,
    #         'actions': tuple(x[0] for x in action_groups),
    #     })
