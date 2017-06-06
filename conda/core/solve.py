# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import defaultdict
from copy import copy
from genericpath import exists
from logging import getLogger
from os.path import basename, join

from conda.models.dag import SimpleDag
from conda.models.dist import Dist
from enum import Enum

from conda.common.constants import NULL
from .envs_manager import EnvsDirectory
from .index import (_supplement_index_with_cache, _supplement_index_with_features,
                    _supplement_index_with_prefix, fetch_index)
from .link import PrefixSetup, UnlinkLinkTransaction
from .linked_data import PrefixData, linked_data
from .._vendor.boltons.setutils import IndexedSet
from ..base.constants import UNKNOWN_CHANNEL
from ..base.context import context
from ..common.compat import iteritems, iterkeys, itervalues, odict, text_type
from ..common.path import ensure_pad
from ..exceptions import InstallError
from ..gateways.disk.test import prefix_is_writable
from ..history import History
from ..models.channel import Channel
from ..models.match_spec import MatchSpec
from ..resolve import Resolve

try:
    from cytoolz.itertoolz import concat, concatv, groupby
except ImportError:
    from .._vendor.toolz.itertoolz import concat, concatv, groupby  # NOQA


log = getLogger(__name__)


"""



conda update -h

Conda attempts to install the newest versions of the requested packages. To
accomplish this, it may update some packages that are already installed, or
install additional packages. To prevent existing packages from updating,
use the --no-update-deps option. This may force conda to install older
versions of the requested packages, and it does not prevent additional
dependency packages from being installed.

If you wish to skip dependency checking altogether, use the '--force'
option. This may result in an environment with incompatible packages, so
this option must be used with great caution.

  -f, --force           Force install (even when package already installed),
                        implies --no-deps.




conda remove -h

This command will also remove any package that depends on any of the
specified packages as well---unless a replacement can be found without
that dependency. If you wish to skip this dependency checking and remove
just the requested packages, add the '--force' option. Note however that
this may result in a broken environment, so use this with caution.



  --force               Forces removal of a package without removing packages
                        that depend on it. Using this option will usually
                        leave your environment in a broken and inconsistent
                        state.

"""

class DepsModifier(Enum):
    NO_DEPS = 'no_deps'
    ONLY_DEPS = 'only_deps'
    UPDATE_DEPS = 'update_deps'
    UPDATE_DEPS_ONLY_DEPS = 'update_deps_only_deps'
    FREEZE_DEPS = 'freeze_deps'  # freeze is a better name for --no-update-deps
    UPDATE_ALL = 'update_all'





class Solver(object):

    def __init__(self, prefix, channels, subdirs=(), specs_to_add=(), specs_to_remove=()):
        """

        Args:
            prefix (str):
                The conda prefix / environment location for which the :class:`Solver`
                is being instantiated.
            channels (Sequence[:class:`Channel`]): 
                A prioritized list of channels to use for the solution. 
            subdirs (Sequence[str]):
                A prioritized list of subdirs to use for the solution.
            specs_to_add (Set[:class:`MatchSpec`]):
                The set of package specs to add to the prefix.
            specs_to_remove (Set[:class:`MatchSpec`]):
                The set of package specs to remove from the prefix.

        """
        self.prefix = prefix
        self.channels = IndexedSet(Channel(c) for c in channels or context.channels)
        self.subdirs = tuple(s for s in subdirs or context.subdirs)
        self.specs_to_add = frozenset(MatchSpec(s) for s in specs_to_add)
        self.specs_to_remove = frozenset(MatchSpec(s) for s in specs_to_remove)

        assert all(s in context.known_subdirs for s in self.subdirs)
        self._prepared = False

    def solve_final_state(self, prune=NULL, force_reinstall=NULL, deps_modifier=None,
                          ignore_pinned=NULL):
        """Gives the final, solved state of the environment.
        
        Args:
            prune (bool):
                If ``True``, the solution will not contain packages that were 
                previously brought into the environment as dependencies but are no longer 
                required as dependencies and are not user-requested.
            force_reinstall (bool):
                Actually, the historic behavior is that force just bypasses the SAT solver entirely.
                Force has different meanings for specs_to_remove vs specs_to_add.
                For requested specs_to_add that are already satisfied in the environment,
                    instructs the solver to remove the package and spec from the environment,
                    and then add it back--possibly with the exact package instance modified, 
                    depending on the spec exactness.
                Therefore, this should NOT be equivalent to context.force!
            deps_modifier (DepsModifier):
                An optional flag indicating special solver handling for dependencies. The
                default solver behavior is to be as conservative as possible with dependency
                updates (in the case the dependency already exists in the environment), while 
                still ensuring all dependencies are satisfied.  Options include
                    * NO_DEPS
                    * ONLY_DEPS
                    * UPDATE_DEPS
                    * UPDATE_DEPS_ONLY_DEPS
                    * FREEZE_DEPS  # freeze is a better name for --no-update-deps
            ignore_pinned (bool):
                If ``True``, the solution will ignore pinned package configuration
                for the prefix.

        Returns:
            Tuple[PackageRef]:
                In sorted dependency order from roots to leaves, the package references for 
                the solved state of the environment.

        """
        index, r = self._prepare()
        prune = context.prune if prune is NULL else prune
        force_reinstall = force_reinstall is NULL and context.force or force_reinstall
        ignore_pinned = ignore_pinned is NULL and context.ignore_pinned or ignore_pinned
        specs_to_remove = self.specs_to_remove
        specs_to_add = self.specs_to_add
        update_deps = deps_modifier == DepsModifier.UPDATE_DEPS or context.update_dependencies

        log.debug("solving prefix %s\n"
                  "  specs_to_remove: %s\n"
                  "  specs_to_add: %s\n"
                  "  prune: %s", self.prefix, specs_to_remove, specs_to_add, prune)

        # declare starting point, the initial state of the environment
        prefix_data = PrefixData(self.prefix)
        solution = tuple(Dist(d) for d in prefix_data.iter_records())

        # removed = ()
        # if specs_to_remove:
        #     pre_solution = set(solution)
        #     solution = r.remove(specs_to_remove, solution)
        #     removed = pre_solution - set(solution)



        if prune:
            specs_map = {}
        else:
            specs_map = {d.name: MatchSpec(d.name) for d in solution}

        # get specs from history, and replace any historically-requested specs with
        # the current specs_to_add
        specs_map.update(History(self.prefix).get_requested_specs_map())

        dag = SimpleDag((index[dist] for dist in solution), itervalues(specs_map))

        removed_records = []
        for spec in specs_to_remove:
            removed_records.extend(dag.remove_spec(spec))

        for rec in removed_records:
            specs_map.pop(rec.name, None)
        solution = tuple(Dist(rec) for rec in dag.records)




        # # remove specs in specs_to_remove
        # for spec in specs_to_remove:
        #     specs_map.pop(spec.name, None)
        #
        # # remove specs that got removed in the initial r.remove() operation above
        # remove_specs = []
        # for rec in removed:
        #     for spec in itervalues(specs_map):
        #         if spec.match(rec):
        #             remove_specs.append(spec)
        #             continue
        # for spec in remove_specs:
        #     specs_map.pop(spec.name, None)


        # for the remaining specs in specs_map, add target to each spec
        for pkg_name, spec in iteritems(specs_map):
            matches_for_spec = tuple(rec for rec in solution if spec.match(rec))
            if matches_for_spec:
                if len(matches_for_spec) > 1:
                    raise NotImplementedError()  # IDontKnowWhatToDoYetError
                else:
                    target = Dist(matches_for_spec[0]).full_name
                    specs_map[pkg_name] = MatchSpec(spec, target=target)

        if deps_modifier == DepsModifier.UPDATE_ALL:
            specs_map = {pkg_name: MatchSpec(spec.name)
                         for pkg_name, spec in iteritems(specs_map)}


        # now add in explicitly requested specs from specs_to_add
        # this overrides any name-matching spec already in the spec map
        specs_map.update((s.name, s) for s in specs_to_add)



        # collect "optional"-type specs, which represent pinned specs and
        # aggressive update specs
        optional_specs = set()
        if not ignore_pinned:
            optional_specs.update(get_pinned_specs(self.prefix))
        if not context.offline:
            optional_specs.update(context.aggressive_update_packages)

        # support track_features config parameter
        track_features_specs = ()
        if context.track_features:
            track_features_specs = (MatchSpec(x + '@') for x in context.track_features)

        compiled_specs_to_add = tuple(concatv(
            itervalues(specs_map),
            optional_specs,
            track_features_specs,
        ))





        # # run initial removal operation
        # # if force_reinstall, specs_to_add get included with specs_to_remove
        # if solution:
        #     if force_reinstall and specs_to_add:
        #         solution = r.remove(concatv(specs_to_remove, specs_to_add), solution)
        #     elif specs_to_remove:
        #         solution = r.remove(specs_to_remove, solution)

        # # if there are no specs_to_add, maybe we should be done now?
        # if not specs_to_add:
        #     solution = IndexedSet(index[d] for d in solution)
        #     return solution



        # NO_DEPS = 'no_deps'  # filter solution
        # ONLY_DEPS = 'only_deps'  # filter solution
        # UPDATE_DEPS = 'update_deps'  # use dag to add additional specs
        # UPDATE_DEPS_ONLY_DEPS = 'update_deps_only_deps'
        # FREEZE_DEPS = 'freeze_deps'  # freeze is a better name for --no-update-deps

        final_environment_specs = compiled_specs_to_add


        log.debug("final specs to add:\n    %s\n",
                  "\n    ".join(text_type(s) for s in final_environment_specs))
        pre_solution = solution

        solution = r.install(final_environment_specs,
                             solution,
                             update_deps=update_deps)

        if deps_modifier == DepsModifier.NO_DEPS:
            dont_add_packages = []
            new_packages = set(solution) - set(pre_solution)
            for record in new_packages:
                if not any(spec.match(record) for spec in specs_to_add):
                    dont_add_packages.append(record)
            solution = tuple(rec for rec in solution if rec not in dont_add_packages)
        elif deps_modifier == DepsModifier.ONLY_DEPS:
            dont_add_packages = []
            new_packages = set(solution) - set(pre_solution)
            for record in new_packages:
                if any(spec.match(record) for spec in specs_to_add):
                    dont_add_packages.append(record)
            solution = tuple(rec for rec in solution if rec not in dont_add_packages)


        # now do safety checks on the solution
        # assert all pinned specs are compatible with what's in solved_linked_dists
        # don't uninstall conda or its dependencies, probably need to check elsewhere

        if prune:
            solution = IndexedSet(r.dependency_sort({d.name: d for d in solution}))
            dag = SimpleDag((index[d] for d in solution), final_environment_specs)
            dag.prune()
            solution = tuple(Dist(rec) for rec in dag.records)

        solution = IndexedSet(r.dependency_sort({d.name: d for d in solution}))
        log.debug("solved prefix %s\n"
                  "  solved_linked_dists:\n"
                  "    %s\n",
                  self.prefix, "\n    ".join(text_type(d) for d in solution))
        solution = IndexedSet(index[d] for d in solution)

        return solution








    def solve_for_diff(self, prune=False, force_reinstall=False, deps_modifier=None,
                          ignore_pinned=False):
        """Gives the package references to remove from an environment, followed by
        the package references to add to an environment.
        
        Args:
            prune (bool):
                See :meth:`solve_final_state`.
            force_reinstall (bool):
                See :meth:`solve_final_state`.
            deps_modifier (DepsModifier):
                See :meth:`solve_final_state`.
            ignore_pinned (bool):
                See :meth:`solve_final_state`.

        Returns:
            Tuple[PackageRef], Tuple[PackageRef]:

        """
        # need to take the final state, but force_reinstall and deps_modifier are also relevant here (also add back requested specs if force_reinstall)
        force_reinstall = force_reinstall is NULL and context.force or force_reinstall
        final_dists = self.solve_final_state(prune, force_reinstall, deps_modifier, ignore_pinned)

        unlink_dists, link_dists = None, None
        return unlink_dists, link_dists


    def solve_for_transaction(self, prune=False, force_reinstall=False, deps_modifier=None,
                          ignore_pinned=False):
        """
        
        Args:
            prune (bool):
                See :meth:`solve_final_state`.
            force_reinstall (bool):
                See :meth:`solve_final_state`.
            deps_modifier (DepsModifier):
                See :meth:`solve_final_state`.
            ignore_pinned (bool):
                See :meth:`solve_final_state`.

        Returns:
            UnlinkLinkTransaction:

        """
        if self.prefix == context.root_prefix and context.enable_private_envs:
            # hold on, it's a while ride
            pass
        else:
            unlink_dists, link_dists = self.solve_for_diff(prune, force_reinstall,
                                                           deps_modifier, ignore_pinned)
            stp = PrefixSetup(self.index, self.prefix, unlink_dists, link_dists, 'INSTALL',
                              self.specs_to_add, self.specs_to_remove)
            return UnlinkLinkTransaction(stp)

    def _prepare(self):
        if self._prepared:
            return self.index, self.r

        def build_channel_priority_map():
            return odict((subdir_url, (c.canonical_name, priority))
                         for priority, c in enumerate(self.channels)
                         for subdir_url in c.urls(True, self.subdirs))

        channel_priority_map = build_channel_priority_map()
        index = fetch_index(channel_priority_map, context.use_index_cache)

        known_channels = tuple(c.canonical_name for c in self.channels)

        _supplement_index_with_prefix(index, self.prefix, known_channels)
        _supplement_index_with_cache(index, known_channels)
        _supplement_index_with_features(index)

        self.index = index
        self.r = Resolve(index)
        return self.index, self.r
















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

    specs_from_history = _get_relevant_specs_from_history(prefix, specs_to_remove, specs_to_add)
    augmented_specs_to_add = augment_specs(prefix, concatv(specs_from_history, specs_to_add))

    log.debug("final specs to add:\n    %s\n",
              "\n    ".join(text_type(s) for s in augmented_specs_to_add))
    solved_linked_dists = r.install(augmented_specs_to_add,
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


def _get_relevant_specs_from_history(prefix, specs_to_remove, specs_to_add):
    # TODO: this should probably be part of the History manager, and brought in through PrefixData

    # add in specs from requested history,
    #   but not if we're requesting a spec with the same name in this operation
    ignore_these_spec_names = set(s.name for s in concatv(specs_to_remove, specs_to_add))
    user_requested_specs_and_dists = History(prefix).get_requested_specs()

    # this effectively pins packages to channels on first use
    user_requested_specs_and_schannels = (
        (s, (d and d.channel or UNKNOWN_CHANNEL))
        for s, d in user_requested_specs_and_dists
    )
    requested_specs_from_history = tuple(
        (MatchSpec(s, channel=schannel) if schannel != UNKNOWN_CHANNEL else s)
        for s, schannel in user_requested_specs_and_schannels
        if not s.name.endswith('@')  # no clue
    )

    # # don't pin packages to channels on first use, in lieu of above code block
    # user_requested_specs = tuple(map(itemgetter(0), user_requested_specs_and_dists))

    log.debug("user requested specs from history:\n    %s\n",
              "\n    ".join(text_type(s) for s in requested_specs_from_history))
    specs_map = {s.name: s for s in requested_specs_from_history
                 if s.name not in ignore_these_spec_names}

    # don't include conda if auto_update_conda is off
    if not context.auto_update_conda and not any(s.name == 'conda' for s in specs_to_add):
        specs_map.pop('conda', None)
        specs_map.pop('conda-env', None)

    return tuple(s for s in itervalues(specs_map))


def solve_for_actions(prefix, r, specs_to_remove=(), specs_to_add=(), prune=False):
    # this is not for force-removing packages, which doesn't invoke the solver

    solved_dists, _specs_to_add = solve_prefix(prefix, r, specs_to_remove, specs_to_add, prune)
    # TODO: this _specs_to_add part should be refactored when we can better pin package channel origin  # NOQA
    dists_for_unlinking, dists_for_linking = sort_unlink_link_from_solve(prefix, solved_dists,
                                                                         _specs_to_add)

    def remove_non_matching_dists(dists_set, specs_to_match):
        _dists_set = IndexedSet(dists_set)
        for dist in dists_set:
            for spec in specs_to_match:
                if spec.match(dist):
                    break
            else:  # executed if the loop ended normally (no break)
                _dists_set.remove(dist)
        return _dists_set

    if context.no_dependencies:
        # for `conda create --no-deps python=3 flask`, do we install python? yes
        # the only dists we touch are the ones that match a specs_to_add
        dists_for_linking = remove_non_matching_dists(dists_for_linking, specs_to_add)
        dists_for_unlinking = remove_non_matching_dists(dists_for_unlinking, specs_to_add)
    elif context.only_dependencies:
        # for `conda create --only-deps python=3 flask`, do we install python? yes
        # remove all dists that match a specs_to_add, as long as that dist isn't a dependency
        #   of other specs_to_add
        _index = r.index
        _match_any = lambda spec, dists: next((dist for dist in dists if spec.match(_index[dist])),
                                              None)
        _is_dependency = lambda spec, dist: any(r.depends_on(s, dist.name)
                                                for s in specs_to_add if s != spec)
        for spec in specs_to_add:
            link_matching_dist = _match_any(spec, dists_for_linking)
            if link_matching_dist:
                if not _is_dependency(spec, link_matching_dist):
                    # as long as that dist isn't a dependency of other specs_to_add
                    dists_for_linking.remove(link_matching_dist)
                    unlink_matching_dist = _match_any(spec, dists_for_unlinking)
                    if unlink_matching_dist:
                        dists_for_unlinking.remove(unlink_matching_dist)

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


def get_install_transaction_single(prefix, index, specs, force=False, only_names=None,
                                   always_copy=False, pinned=True, update_deps=True,
                                   prune=False, channel_priority_map=None, is_update=False):
    specs = tuple(MatchSpec(s) for s in specs)
    r = get_resolve_object(index.copy(), prefix)
    unlink_dists, link_dists = solve_for_actions(prefix, r, specs_to_add=specs, prune=prune)

    stp = PrefixSetup(r.index, prefix, unlink_dists, link_dists, 'INSTALL',
                      tuple(specs))
    txn = UnlinkLinkTransaction(stp)
    return txn


def get_install_transaction(prefix, index, spec_strs, force=False, only_names=None,
                            always_copy=False, pinned=True, update_deps=True,
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
                                                  always_copy, pinned, update_deps,
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
                               tuple(specs))

        txn_args = tuple(make_txn_setup(ed.to_prefix(ensure_pad(env_name)), *oink)
                         for env_name, oink in iteritems(unlink_link_map))
        txn = UnlinkLinkTransaction(*txn_args)
        return txn

    else:
        # disregard any requested preferred env
        return get_install_transaction_single(prefix, index, spec_strs, force, only_names,
                                              always_copy, pinned, update_deps,
                                              prune, channel_priority_map, is_update)


def augment_specs(prefix, specs, ignore_pinned=None):
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


def get_pinned_specs(prefix):
    """Find pinned specs from file and return a tuple of MatchSpec."""
    pinfile = join(prefix, 'conda-meta', 'pinned')
    if exists(pinfile):
        with open(pinfile) as f:
            from_file = (i for i in f.read().strip().splitlines()
                         if i and not i.strip().startswith('#'))
    else:
        from_file = ()

    return tuple(MatchSpec(s, optional=True) for s in
                 concatv(context.pinned_packages, from_file))
