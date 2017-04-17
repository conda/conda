# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import defaultdict
from copy import copy
from genericpath import exists
from logging import getLogger
from operator import itemgetter
from os.path import basename, join

from .envs_manager import EnvsDirectory
from .index import _supplement_index_with_prefix
from .link import PrefixSetup, UnlinkLinkTransaction
from .linked_data import linked_data
from .._vendor.boltons.setutils import IndexedSet
from ..base.context import context
from ..common.compat import iteritems, iterkeys, itervalues, odict, text_type
from ..common.path import ensure_pad
from ..exceptions import InstallError
from ..gateways.disk.test import prefix_is_writable
from ..history import History
from ..models.match_spec import MatchSpec
from ..resolve import Resolve

try:
    from cytoolz.itertoolz import concat, concatv, groupby
except ImportError:
    from .._vendor.toolz.itertoolz import concat, concatv, groupby  # NOQA


log = getLogger(__name__)


def get_pinned_specs(prefix):
    pinfile = join(prefix, 'conda-meta', 'pinned')
    if exists(pinfile):
        with open(pinfile) as f:
            from_file = (i for i in f.read().strip().splitlines()
                         if i and not i.strip().startswith('#'))
    else:
        from_file = ()

    from ..cli.common import spec_from_line

    def munge_spec(s):
        return s if ' ' in s else spec_from_line(s)

    return tuple(munge_spec(s) for s in concatv(context.pinned_packages, from_file))


def solve_prefix(prefix, r, specs_to_remove=(), specs_to_add=(), prune=False):
    # this function gives a "final state" for an existing prefix given just these simple inputs
    prune = context.prune or prune
    log.debug("solving prefix %s\n"
              "  specs_to_remove: %s\n"
              "  specs_to_add: %s\n"
              "  prune: %s", prefix, specs_to_remove, specs_to_add, prune)

    # declare starting point
    solved_linked_dists = () if prune else tuple(iterkeys(linked_data(prefix)))
    # TODO: to change this whole function from working with dists to working with records, just
    #       change iterkeys to itervalues

    if solved_linked_dists and specs_to_remove:
        solved_linked_dists = r.remove(tuple(text_type(s) for s in specs_to_remove),
                                       solved_linked_dists)

    # add in specs from requested history,
    #   but not if we're requesting removal in this operation
    spec_names_to_remove = set(s.name for s in specs_to_remove)
    user_requested_specs_and_dists = History(prefix).get_requested_specs()

    # this effectively pins packages to channels on first use
    #  might not ultimately be the desired behavior
    user_requested_specs = tuple((MatchSpec(s, schannel=d.channel) if d else s)
                                 for s, d in user_requested_specs_and_dists)

    # # don't pin packages to channels on first use, in lieu of above code block
    # user_requested_specs = tuple(map(itemgetter(0), user_requested_specs_and_dists))

    log.debug("user requested specs from history:\n    %s\n",
              "\n    ".join(text_type(s) for s in user_requested_specs))
    specs_map = {s.name: s for s in user_requested_specs if s.name not in spec_names_to_remove}

    if not context.auto_update_conda and not any(s.name == 'conda' for s in specs_to_add):
        specs_map.pop('conda', None)
        specs_map.pop('conda-env', None)

    # replace specs matching same name with new specs_to_add
    specs_map.update({s.name: s for s in specs_to_add})
    specs_to_add = itervalues(specs_map)

    specs_to_add = augment_specs(prefix, specs_to_add)

    log.debug("final specs to add:\n    %s\n",
              "\n    ".join(text_type(s) for s in specs_to_add))
    solved_linked_dists = r.install(specs_to_add,
                                    solved_linked_dists,
                                    update_deps=context.update_dependencies)

    if context.respect_pinned:
        # TODO: assert all pinned specs are compatible with what's in solved_linked_dists
        pass

    # TODO: don't uninstall conda or its dependencies, probably need to check elsewhere

    solved_linked_dists = IndexedSet(r.dependency_sort({d.name: d for d in solved_linked_dists}))

    log.debug("solved prefix %s\n"
              "  solved_linked_dists:\n"
              "    %s\n",
              prefix, "\n    ".join(text_type(d) for d in solved_linked_dists))

    return solved_linked_dists, specs_to_add


def solve_for_actions(prefix, r, specs_to_remove=(), specs_to_add=(), prune=False):
    # this is not for force-removing packages, which doesn't invoke the solver

    solved_dists, _specs_to_add = solve_prefix(prefix, r, specs_to_remove, specs_to_add, prune)
    dists_for_unlinking, dists_for_linking = sort_unlink_link_from_solve(prefix, solved_dists,
                                                                         _specs_to_add)
    # TODO: this _specs_to_add part should be refactored when we can better pin package channel origin  # NOQA

    if context.force:
        dists_for_unlinking, dists_for_linking = forced_reinstall_specs(prefix, solved_dists,
                                                                        dists_for_unlinking,
                                                                        dists_for_linking,
                                                                        specs_to_add)

    dists_for_unlinking = IndexedSet(reversed(dists_for_unlinking))
    return dists_for_unlinking, dists_for_linking


def forced_reinstall_specs(prefix, solved_dists, dists_for_unlinking, dists_for_linking,
                           specs_to_add):
    _dists_for_unlinking, _dists_for_linking = copy(dists_for_unlinking), copy(dists_for_linking)
    old_linked_dists = IndexedSet(iterkeys(linked_data(prefix)))

    # re-install any specs_to_add
    def find_first(dists, package_name):
        return next((d for d in dists if d.name == package_name), None)

    for spec in specs_to_add:
        spec_name = MatchSpec(spec).name
        old_dist_with_same_name = find_first(old_linked_dists, spec_name)
        if old_dist_with_same_name:
            _dists_for_unlinking.add(old_dist_with_same_name)

        new_dist_with_same_name = find_first(solved_dists, spec_name)
        if new_dist_with_same_name:
            _dists_for_linking.add(new_dist_with_same_name)

    return _dists_for_unlinking, _dists_for_linking


def sort_unlink_link_from_solve(prefix, solved_dists, remove_satisfied_specs):
    # solved_dists should be the return value of solve_prefix()
    old_linked_dists = IndexedSet(iterkeys(linked_data(prefix)))

    dists_for_unlinking = old_linked_dists - solved_dists
    dists_for_linking = solved_dists - old_linked_dists

    # TODO: add back 'noarch: python' to unlink and link if python version changes

    # r_linked = Resolve(linked_data(prefix))
    # for spec in remove_satisfied_specs:
    #     if r_linked.find_matches(spec):
    #         spec_name = spec.name
    #         unlink_dist = next((d for d in dists_for_unlinking if d.name == spec_name), None)
    #         link_dist = next((d for d in dists_for_linking if d.name == spec_name), None)
    #         if unlink_dist:
    #             dists_for_unlinking.discard(unlink_dist)
    #         if link_dist:
    #             dists_for_linking.discard(link_dist)

    return dists_for_unlinking, dists_for_linking


def get_resolve_object(index, prefix):
    # instantiate resolve object
    _supplement_index_with_prefix(index, prefix, {})
    r = Resolve(index)
    return r


def get_install_transaction(prefix, index, spec_strs, force=False, only_names=None,
                            always_copy=False, pinned=True, minimal_hint=False, update_deps=True,
                            prune=False, channel_priority_map=None, is_update=False):
    # type: (str, Dict[Dist, Record], List[str], bool, Option[List[str]], bool, bool, bool,
    #        bool, bool, bool, Dict[str, Sequence[str, int]]) -> List[Dict[weird]]

    # split out specs into potentially multiple preferred envs if:
    #  1. the user default env (root_prefix) is the prefix being considered here
    #  2. the user has not specified the --name or --prefix command-line flags
    if (prefix == context.root_prefix
            and not context.prefix_specified
            and prefix_is_writable(prefix)
            and context.enable_private_envs):

        # a registered package CANNOT be installed in the root env
        # if ANY package requesting a private env is required in the root env, all packages for
        #   that requested env must instead be installed in the root env

        root_r = get_resolve_object(index.copy(), context.root_prefix)

        def get_env_for_spec(spec):
            # use resolve's get_dists_for_spec() to find the "best" matching record
            record_for_spec = root_r.index[root_r.get_dists_for_spec(spec, emptyok=False)[-1]]
            return ensure_pad(record_for_spec.preferred_env)

        # specs grouped by target env, the 'None' key holds the specs for the root env
        env_add_map = groupby(get_env_for_spec, (MatchSpec(s) for s in spec_strs))
        requested_root_specs_to_add = {s for s in env_add_map.pop(None, ())}

        ed = EnvsDirectory(join(context.root_prefix, 'envs'))
        registered_packages = ed.get_registered_packages_keyed_on_env_name()

        if len(env_add_map) == len(registered_packages) == 0:
            # short-circuit the rest of this logic
            return get_install_transaction_single(prefix, index, spec_strs, force, only_names,
                                                  always_copy, pinned, minimal_hint, update_deps,
                                                  prune, channel_priority_map, is_update)

        root_specs_to_remove = set(MatchSpec(s.name) for s in concat(itervalues(env_add_map)))
        required_root_dists, _ = solve_prefix(context.root_prefix, root_r,
                                              specs_to_remove=root_specs_to_remove,
                                              specs_to_add=requested_root_specs_to_add,
                                              prune=True)

        required_root_package_names = tuple(d.name for d in required_root_dists)

        # first handle pulling back requested specs to root
        forced_root_specs_to_add = set()
        pruned_env_add_map = defaultdict(list)
        for env_name, specs in iteritems(env_add_map):
            for spec in specs:
                spec_name = MatchSpec(spec).name
                if spec_name in required_root_package_names:
                    forced_root_specs_to_add.add(spec)
                else:
                    pruned_env_add_map[env_name].append(spec)
        env_add_map = pruned_env_add_map

        # second handle pulling back registered specs to root
        env_remove_map = defaultdict(list)
        for env_name, registered_package_entries in iteritems(registered_packages):
            for rpe in registered_package_entries:
                if rpe['package_name'] in required_root_package_names:
                    # ANY registered packages in this environment need to be pulled back
                    for pe in registered_package_entries:
                        # add an entry in env_remove_map
                        # add an entry in forced_root_specs_to_add
                        pname = pe['package_name']
                        env_remove_map[env_name].append(MatchSpec(pname))
                        forced_root_specs_to_add.add(MatchSpec(pe['requested_spec']))
                break

        unlink_link_map = odict()

        # solve all neede preferred_env prefixes
        for env_name in set(concatv(env_add_map, env_remove_map)):
            specs_to_add = env_add_map[env_name]
            spec_to_remove = env_remove_map[env_name]
            pfx = ed.preferred_env_to_prefix(env_name)
            unlink, link = solve_for_actions(pfx, get_resolve_object(index.copy(), pfx),
                                             specs_to_remove=spec_to_remove,
                                             specs_to_add=specs_to_add,
                                             prune=True)
            unlink_link_map[env_name] = unlink, link, specs_to_add

        # now solve root prefix
        # we have to solve root a second time in all cases, because this time we don't prune
        root_specs_to_add = set(concatv(requested_root_specs_to_add, forced_root_specs_to_add))
        root_unlink, root_link = solve_for_actions(context.root_prefix, root_r,
                                                   specs_to_remove=root_specs_to_remove,
                                                   specs_to_add=root_specs_to_add)
        if root_unlink or root_link:
            # this needs to be added to odict last; the private envs need to be updated first
            unlink_link_map[None] = root_unlink, root_link, root_specs_to_add

        def make_txn_setup(pfx, unlink, link, specs):
            # TODO: this index here is probably wrong; needs to be per-prefix
            return PrefixSetup(index, pfx, unlink, link, 'INSTALL',
                               tuple(s.spec for s in specs))

        txn_args = tuple(make_txn_setup(ed.to_prefix(ensure_pad(env_name)), *oink)
                         for env_name, oink in iteritems(unlink_link_map))
        txn = UnlinkLinkTransaction(*txn_args)
        return txn

    else:
        # disregard any requested preferred env
        return get_install_transaction_single(prefix, index, spec_strs, force, only_names,
                                              always_copy, pinned, minimal_hint, update_deps,
                                              prune, channel_priority_map, is_update)


def get_install_transaction_single(prefix, index, specs, force=False, only_names=None,
                                   always_copy=False, pinned=True, minimal_hint=False,
                                   update_deps=True, prune=False, channel_priority_map=None,
                                   is_update=False):
    specs = set(MatchSpec(s) for s in specs)
    r = get_resolve_object(index.copy(), prefix)
    unlink_dists, link_dists = solve_for_actions(prefix, r, specs_to_add=specs, prune=prune)

    stp = PrefixSetup(r.index, prefix, unlink_dists, link_dists, 'INSTALL',
                      tuple(s.spec for s in specs))
    txn = UnlinkLinkTransaction(stp)
    return txn


def augment_specs(prefix, specs, pinned=True):
    _specs = list(specs)

    # get conda-meta/pinned
    if context.respect_pinned:
        pinned_specs = get_pinned_specs(prefix)
        log.debug("Pinned specs=%s", pinned_specs)
        _specs += [MatchSpec(spec) for spec in pinned_specs]

    # support aggressive auto-update conda
    #   Only add a conda spec if conda and conda-env are not in the specs.
    #   Also skip this step if we're offline.
    root_only = ('conda', 'conda-env')
    mss = [MatchSpec(s) for s in _specs if s.name.startswith(root_only)]
    mss = [ms for ms in mss if ms.name in root_only]

    if prefix == context.root_prefix:
        if context.auto_update_conda and not context.offline and not mss:
            log.debug("Adding 'conda' to specs.")
            _specs.append(MatchSpec('conda'))
            _specs.append(MatchSpec('conda-env'))
    elif basename(prefix).startswith('_'):
        # anything (including conda) can be installed into environments
        # starting with '_', mainly to allow conda-build to build conda
        pass
    elif mss:
        raise InstallError("Error: 'conda' can only be installed into the root environment")

    # support track_features config parameter
    if context.track_features:
        _specs.extend(x + '@' for x in context.track_features)
    return _specs
