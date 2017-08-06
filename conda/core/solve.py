# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from genericpath import exists
from logging import getLogger
from os.path import join

from enum import Enum

from .index import get_reduced_index
from .link import PrefixSetup, UnlinkLinkTransaction
from .linked_data import PrefixData, linked_data
from .._vendor.boltons.setutils import IndexedSet
from ..base.context import context
from ..common.compat import iteritems, itervalues, odict, string_types, text_type
from ..common.constants import NULL
from ..common.io import spinner
from ..common.path import paths_equal
from ..exceptions import PackagesNotFoundError
from ..history import History
from ..models.channel import Channel
from ..models.dag import PrefixDag
from ..models.dist import Dist
from ..models.match_spec import MatchSpec
from ..resolve import Resolve

try:
    from cytoolz.itertoolz import concat, concatv, groupby
except ImportError:
    from .._vendor.toolz.itertoolz import concat, concatv, groupby  # NOQA

log = getLogger(__name__)


class DepsModifier(Enum):
    """Flags to enable alternate handling of dependencies."""
    NO_DEPS = 'no_deps'
    ONLY_DEPS = 'only_deps'
    UPDATE_DEPS = 'update_deps'
    UPDATE_DEPS_ONLY_DEPS = 'update_deps_only_deps'
    UPDATE_ALL = 'update_all'
    FREEZE_INSTALLED = 'freeze_installed'  # freeze is a better name for --no-update-deps


class Solver(object):
    """
    A high-level API to conda's solving logic. Three public methods are provided to access a
    solution in various forms.

      * :meth:`solve_final_state`
      * :meth:`solve_for_diff`
      * :meth:`solve_for_transaction`

    """

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
        self._index = None
        self._r = None
        self._prepared = False

    def solve_final_state(self, deps_modifier=NULL, prune=NULL, ignore_pinned=NULL,
                          force_remove=NULL):
        """Gives the final, solved state of the environment.

        Args:
            deps_modifier (DepsModifier):
                An optional flag indicating special solver handling for dependencies. The
                default solver behavior is to be as conservative as possible with dependency
                updates (in the case the dependency already exists in the environment), while
                still ensuring all dependencies are satisfied.  Options include
                    * NO_DEPS
                    * ONLY_DEPS
                    * UPDATE_DEPS
                    * UPDATE_DEPS_ONLY_DEPS
            prune (bool):
                If ``True``, the solution will not contain packages that were
                previously brought into the environment as dependencies but are no longer
                required as dependencies and are not user-requested.
            ignore_pinned (bool):
                If ``True``, the solution will ignore pinned package configuration
                for the prefix.
            force_remove (bool):
                Forces removal of a package without removing packages that depend on it.

        Returns:
            Tuple[PackageRef]:
                In sorted dependency order from roots to leaves, the package references for
                the solved state of the environment.

        """
        prune = context.prune if prune is NULL else prune
        ignore_pinned = context.ignore_pinned if ignore_pinned is NULL else ignore_pinned
        deps_modifier = context.deps_modifier if deps_modifier is NULL else deps_modifier
        if isinstance(deps_modifier, string_types):
            deps_modifier = DepsModifier(deps_modifier.lower())
        specs_to_remove = self.specs_to_remove
        specs_to_add = self.specs_to_add

        # force_remove is a special case where we return early
        if specs_to_remove and force_remove:
            if specs_to_add:
                raise NotImplementedError()
            index, r = self._prepare(specs_to_remove)
            solution = tuple(Dist(rec) for rec in PrefixData(self.prefix).iter_records()
                             if not any(spec.match(rec) for spec in specs_to_remove))
            return IndexedSet(index[d] for d in r.dependency_sort({d.name: d for d in solution}))

        log.debug("solving prefix %s\n"
                  "  specs_to_remove: %s\n"
                  "  specs_to_add: %s\n"
                  "  prune: %s", self.prefix, specs_to_remove, specs_to_add, prune)

        # declare starting point, the initial state of the environment
        # `solution` and `specs_map` are mutated throughout this method
        prefix_data = PrefixData(self.prefix)
        solution = tuple(Dist(d) for d in prefix_data.iter_records())
        if prune or deps_modifier == DepsModifier.UPDATE_ALL:
            # start with empty specs map for UPDATE_ALL because we're optimizing the update
            # only for specs the user has requested; it's ok to remove dependencies
            specs_map = odict()
        else:
            specs_map = odict((d.name, MatchSpec(d.name)) for d in solution)

        # add in historically-requested specs
        specs_from_history_map = History(self.prefix).get_requested_specs_map()
        specs_map.update(specs_from_history_map)

        # let's pretend for now that this is the right place to build the index
        prepared_specs = tuple(concatv(specs_to_remove, specs_to_add,
                                       itervalues(specs_from_history_map)))
        index, r = self._prepare(prepared_specs)

        if specs_to_remove:
            # Rather than invoking SAT for removal, we can use the DAG and simple tree traversal
            # if we're careful about how we handle features.
            _provides_fts_specs = (spec for spec in specs_to_remove if 'provides_features' in spec)
            feature_names = set(concat(spec.get_raw_value('provides_features')
                                       for spec in _provides_fts_specs))
            dag = PrefixDag((index[dist] for dist in solution), itervalues(specs_map))

            removed_records = []
            for spec in specs_to_remove:
                # If the spec was a provides_features spec, then we need to also remove every
                # package with a requires_feature that matches the provides_feature.  The
                # `dag.remove_spec()` method handles that for us.
                removed_records.extend(dag.remove_spec(spec))

            for rec in removed_records:
                # We keep specs (minus the feature part) for the non provides_features packages
                # if they're in the history specs.  Otherwise, we pop them from the specs_map.
                rec_has_a_feature = set(rec.requires_features or ()) & feature_names
                if rec_has_a_feature and rec.name in specs_from_history_map:
                    spec = specs_map.get(rec.name, MatchSpec(rec.name))
                    spec._match_components.pop('requires_features', None)
                    specs_map[spec.name] = spec
                else:
                    specs_map.pop(rec.name, None)

            solution = tuple(Dist(rec) for rec in dag.records)

            if not removed_records and not prune:
                raise PackagesNotFoundError(tuple(spec.name for spec in specs_to_remove))

        # We handle as best as possible environments in inconsistent states. To do this,
        # we remove now from consideration the set of packages causing inconsistencies,
        # and then we add them back in following the main SAT call.
        _, inconsistent_dists = r.bad_installed(solution, ())
        add_back_map = {}  # name: (dist, spec)
        if inconsistent_dists:
            for dist in inconsistent_dists:
                # pop and save matching spec in specs_map
                add_back_map[dist.name] = (dist, specs_map.pop(dist.name, None))
            solution = tuple(dist for dist in solution if dist not in inconsistent_dists)

        # For the remaining specs in specs_map, add target to each spec. `target` is a reference
        # to the package currently existing in the environment. Setting target instructs the
        # solver to not disturb that package if it's not necessary.
        # If the spec.name is being modified by inclusion in specs_to_add, we don't set `target`,
        # since we *want* the solver to modify/update that package.
        #
        # TLDR: when working with MatchSpec objects,
        #  - to minimize the version change, set MatchSpec(name=name, target=dist.full_name)
        #  - to freeze the package, set all the components of MatchSpec individually
        for pkg_name, spec in iteritems(specs_map):
            matches_for_spec = tuple(dist for dist in solution if spec.match(index[dist]))
            if matches_for_spec:
                assert len(matches_for_spec) == 1
                target_dist = matches_for_spec[0]
                if deps_modifier == DepsModifier.FREEZE_INSTALLED:
                    new_spec = MatchSpec(index[target_dist])
                else:
                    target = Dist(target_dist).full_name
                    new_spec = MatchSpec(spec, target=target)
                specs_map[pkg_name] = new_spec

        # If we're in UPDATE_ALL mode, we need to drop all the constraints attached to specs,
        # so they can all float and the solver can find the most up-to-date solution. In the case
        # of UPDATE_ALL, `specs_map` wasn't initialized with packages from the current environment,
        # but *only* historically-requested specs.  This let's UPDATE_ALL drop dependencies if
        # they're no longer needed, and their presence would otherwise prevent the updated solution
        # the user most likely wants.
        if deps_modifier == DepsModifier.UPDATE_ALL:
            specs_map = {pkg_name: MatchSpec(spec.name, optional=spec.optional)
                         for pkg_name, spec in iteritems(specs_map)}

        # For the aggressive_update_packages configuration parameter, we strip any target
        # that's been set.
        if not context.offline:
            for spec in context.aggressive_update_packages:
                if spec.name in specs_map:
                    old_spec = specs_map[spec.name]
                    specs_map[spec.name] = MatchSpec(old_spec, target=None)
            if (context.auto_update_conda and paths_equal(self.prefix, context.root_prefix)
                    and any(dist.name == "conda" for dist in solution)):
                specs_map["conda"] = MatchSpec("conda")

        # add in explicitly requested specs from specs_to_add
        # this overrides any name-matching spec already in the spec map
        specs_map.update((s.name, s) for s in specs_to_add)

        # collect additional specs to add to the solution
        track_features_specs = pinned_specs = ()
        if context.track_features:
            track_features_specs = tuple(MatchSpec(x + '@') for x in context.track_features)
        if not ignore_pinned:
            pinned_specs = get_pinned_specs(self.prefix)

        final_environment_specs = IndexedSet(concatv(
            itervalues(specs_map),
            track_features_specs,
            pinned_specs,
        ))

        # We've previously checked `solution` for consistency (which at that point was the
        # pre-solve state of the environment). Now we check our compiled set of
        # `final_environment_specs` for the possibility of a solution.  If there are conflicts,
        # we can often avoid them by neutering specs that have a target (e.g. removing version
        # constraint) and also making them optional. The result here will be less cases of
        # `UnsatisfiableError` handed to users, at the cost of more packages being modified
        # or removed from the environment.
        conflicting_specs = r.get_conflicting_specs(tuple(final_environment_specs))
        for spec in conflicting_specs:
            if spec.target:
                final_environment_specs.remove(spec)
                neutered_spec = MatchSpec(spec.name, target=spec.target, optional=True)
                final_environment_specs.add(neutered_spec)

        # Finally! We get to call SAT.
        log.debug("final specs to add:\n    %s\n",
                  "\n    ".join(text_type(s) for s in final_environment_specs))
        pre_solution = solution
        solution = r.solve(tuple(final_environment_specs))  # return value is List[dist]

        # add back inconsistent packages to solution
        if add_back_map:
            for name, (dist, spec) in iteritems(add_back_map):
                if not any(d.name == name for d in solution):
                    solution.append(dist)
                    if spec:
                        final_environment_specs.add(spec)

        # Special case handling for various DepsModifer flags. Maybe this block could be pulled
        # out into its own non-public helper method?
        if deps_modifier == DepsModifier.NO_DEPS:
            # In the NO_DEPS case we're just filtering out packages from the solution.
            dont_add_packages = []
            new_packages = set(solution) - set(pre_solution)
            for dist in new_packages:
                if not any(spec.match(index[dist]) for spec in specs_to_add):
                    dont_add_packages.append(dist)
            solution = tuple(rec for rec in solution if rec not in dont_add_packages)
        elif deps_modifier == DepsModifier.ONLY_DEPS:
            # Using a special instance of the DAG to remove leaf nodes that match the original
            # specs_to_add.  It's important to only remove leaf nodes, because a typical use
            # might be `conda install --only-deps python=2 flask`, and in that case we'd want
            # to keep python.
            dag = PrefixDag((index[d] for d in solution), specs_to_add)
            dag.remove_leaf_nodes_with_specs()
            solution = tuple(Dist(rec) for rec in dag.records)
        elif deps_modifier in (DepsModifier.UPDATE_DEPS, DepsModifier.UPDATE_DEPS_ONLY_DEPS):
            # Here we have to SAT solve again :(  It's only now that we know the dependency
            # chain of specs_to_add.
            specs_to_add_names = set(spec.name for spec in specs_to_add)
            update_names = set()
            dag = PrefixDag((index[d] for d in solution), final_environment_specs)
            for spec in specs_to_add:
                node = dag.get_node_by_name(spec.name)
                for ascendant in node.all_ascendants():
                    ascendant_name = ascendant.record.name
                    if ascendant_name not in specs_to_add_names:
                        update_names.add(ascendant_name)
            grouped_specs = groupby(lambda s: s.name in update_names, final_environment_specs)
            new_final_environment_specs = set(grouped_specs[False])
            update_specs = set(MatchSpec(spec.name, optional=spec.optional)
                               for spec in grouped_specs[True])
            final_environment_specs = new_final_environment_specs | update_specs
            solution = r.solve(final_environment_specs)

            if deps_modifier == DepsModifier.UPDATE_DEPS_ONLY_DEPS:
                # duplicated from DepsModifier.ONLY_DEPS
                dag = PrefixDag((index[d] for d in solution), specs_to_add)
                dag.remove_leaf_nodes_with_specs()
                solution = tuple(Dist(rec) for rec in dag.records)

        if prune:
            dag = PrefixDag((index[d] for d in solution), final_environment_specs)
            dag.prune()
            solution = tuple(Dist(rec) for rec in dag.records)

        self._check_solution(solution, pinned_specs)

        solution = IndexedSet(r.dependency_sort({d.name: d for d in solution}))
        log.debug("solved prefix %s\n"
                  "  solved_linked_dists:\n"
                  "    %s\n",
                  self.prefix, "\n    ".join(text_type(d) for d in solution))
        return IndexedSet(index[d] for d in solution)

    def solve_for_diff(self, deps_modifier=None, prune=NULL, ignore_pinned=NULL,
                       force_remove=NULL, force_reinstall=NULL):
        """Gives the package references to remove from an environment, followed by
        the package references to add to an environment.

        Args:
            deps_modifier (DepsModifier):
                See :meth:`solve_final_state`.
            prune (bool):
                See :meth:`solve_final_state`.
            ignore_pinned (bool):
                See :meth:`solve_final_state`.
            force_remove (bool):
                See :meth:`solve_final_state`.
            force_reinstall (bool):
                For requested specs_to_add that are already satisfied in the environment,
                    instructs the solver to remove the package and spec from the environment,
                    and then add it back--possibly with the exact package instance modified,
                    depending on the spec exactness.

        Returns:
            Tuple[PackageRef], Tuple[PackageRef]:
                A two-tuple of PackageRef sequences.  The first is the group of packages to
                remove from the environment, in sorted dependency order from leaves to roots.
                The second is the group of packages to add to the environment, in sorted
                dependency order from roots to leaves.

        """
        final_precs = self.solve_final_state(deps_modifier, prune, ignore_pinned, force_remove)
        previous_records = IndexedSet(itervalues(linked_data(self.prefix)))
        unlink_precs = previous_records - final_precs
        link_precs = final_precs - previous_records

        if force_reinstall:
            for spec in self.specs_to_add:
                prec = next((rec for rec in final_precs if spec.match(rec)), None)
                assert prec
                link_precs.add(prec)
                unlink_precs.add(prec)

        # TODO: add back 'noarch: python' to unlink and link if python version changes
        # TODO: get the sort order correct for unlink_records
        # TODO: force_reinstall might not yet be fully implemented in :meth:`solve_final_state`,
        #       at least as described in the docstring.

        return unlink_precs, link_precs

    def solve_for_transaction(self, deps_modifier=NULL, prune=NULL, ignore_pinned=NULL,
                              force_remove=NULL, force_reinstall=False):
        """Gives an UnlinkLinkTransaction instance that can be used to execute the solution
        on an environment.

        Args:
            deps_modifier (DepsModifier):
                See :meth:`solve_final_state`.
            prune (bool):
                See :meth:`solve_final_state`.
            ignore_pinned (bool):
                See :meth:`solve_final_state`.
            force_remove (bool):
                See :meth:`solve_final_state`.
            force_reinstall (bool):
                See :meth:`solve_for_diff`.

        Returns:
            UnlinkLinkTransaction:

        """
        with spinner("Solving environment", not context.verbosity and not context.quiet,
                     context.json):
            if self.prefix == context.root_prefix and context.enable_private_envs:
                # This path has the ability to generate a multi-prefix transaction. The basic logic
                # is in the commented out get_install_transaction() function below. Exercised at
                # the integration level in the PrivateEnvIntegrationTests in test_create.py.
                raise NotImplementedError()
            else:
                unlink_precs, link_precs = self.solve_for_diff(deps_modifier, prune, ignore_pinned,
                                                               force_remove, force_reinstall)
                stp = PrefixSetup(self.prefix, unlink_precs, link_precs,
                                  self.specs_to_remove, self.specs_to_add)
                # TODO: Only explicitly requested remove and update specs are being included in
                #   History right now. Do we need to include other categories from the solve?
                return UnlinkLinkTransaction(stp)

    def _prepare(self, prepared_specs):
        # All of this _prepare() method is hidden away down here. Someday we may want to further
        # abstract away the use of `index` or the Resolve object.

        if self._prepared and prepared_specs == prepared_specs:
            return self._index, self._r

        def build_channel_priority_map():
            return odict((subdir_url, (c.canonical_name, priority))
                         for priority, c in enumerate(self.channels)
                         for subdir_url in c.urls(True, self.subdirs))

        # with spinner("Loading channels", not context.verbosity and not context.quiet,
        #              context.json):
        if hasattr(self, '_index'):
            # added in install_actions for conda-build back-compat
            self._prepared_specs = prepared_specs
            self._r = Resolve(self._index)
        else:
            reduced_index = get_reduced_index(self.prefix, self.channels,
                                              self.subdirs, prepared_specs)
            self._prepared_specs = prepared_specs
            self._index = reduced_index
            self._r = Resolve(reduced_index)

        # channel_priority_map = build_channel_priority_map()
        # if self._index is None:
        #     self._index = fetch_index(channel_priority_map, context.use_index_cache)
        #
        # known_channels = tuple(c.canonical_name for c in self.channels)
        #
        # _supplement_index_with_prefix(self._index, self.prefix, known_channels)
        # if context.offline or ('unknown' in context._argparse_args
        #                        and context._argparse_args.unknown):
        #     # This is really messed up right now.  Dates all the way back to
        #     # https://github.com/conda/conda/commit/f761f65a82b739562a0d997a2570e2b8a0bdc783
        #     # TODO: revisit this later
        #     _supplement_index_with_cache(self._index, known_channels)
        # _supplement_index_with_features(self._index)
        #
        # self._r = Resolve(self._index)

        self._prepared = True
        return self._index, self._r

    def _check_solution(self, solution, pinned_specs):
        # Ensure that solution is consistent with pinned specs.
        for spec in pinned_specs:
            spec = MatchSpec(spec, optional=False)
            if not any(spec.match(d) for d in solution):
                # if the spec doesn't match outright, make sure there's no package by that
                # name in the solution
                assert not any(d.name == spec.name for d in solution)

                # Let this be handled as part of txn.verify()
                # # Ensure conda or its dependencies aren't being uninstalled in conda's
                # # own environment.
                # if paths_equal(self.prefix, context.conda_prefix) and not context.force:
                #     conda_spec = MatchSpec("conda")
                #     conda_dist = next((conda_spec.match(d) for d in solution), None)
                #     assert conda_dist
                #     conda_deps_specs = self._r.ms_depends(conda_dist)
                #     for spec in conda_deps_specs:
                #         assert any(spec.match(d) for d in solution)


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


# NOTE: The remaining code in this module is being left for development reference until
#  the context.enable_private_envs portion is implemented in :meth:`solve_for_transaction`.

# def solve_prefix(prefix, r, specs_to_remove=(), specs_to_add=(), prune=False):
#     # this function gives a "final state" for an existing prefix given just these simple inputs
#     prune = context.prune or prune
#     log.debug("solving prefix %s\n"
#               "  specs_to_remove: %s\n"
#               "  specs_to_add: %s\n"
#               "  prune: %s", prefix, specs_to_remove, specs_to_add, prune)
#
#     # declare starting point
#     solved_linked_dists = () if prune else tuple(iterkeys(linked_data(prefix)))
#     # TODO: to change this whole function from working with dists to working with records, just
#     #       change iterkeys to itervalues
#
#     if solved_linked_dists and specs_to_remove:
#         solved_linked_dists = r.remove(tuple(text_type(s) for s in specs_to_remove),
#                                        solved_linked_dists)
#
#     specs_from_history = _get_relevant_specs_from_history(prefix, specs_to_remove, specs_to_add)
#     augmented_specs_to_add = augment_specs(prefix, concatv(specs_from_history, specs_to_add))
#
#     log.debug("final specs to add:\n    %s\n",
#               "\n    ".join(text_type(s) for s in augmented_specs_to_add))
#     solved_linked_dists = r.install(augmented_specs_to_add,
#                                     solved_linked_dists,
#                                     update_deps=context.update_dependencies)
#
#     if not context.ignore_pinned:
#         # TODO: assert all pinned specs are compatible with what's in solved_linked_dists
#         pass
#
#     # TODO: don't uninstall conda or its dependencies, probably need to check elsewhere
#
#     solved_linked_dists = IndexedSet(r.dependency_sort({d.name: d for d in solved_linked_dists}))
#
#     log.debug("solved prefix %s\n"
#               "  solved_linked_dists:\n"
#               "    %s\n",
#               prefix, "\n    ".join(text_type(d) for d in solved_linked_dists))
#
#     return solved_linked_dists, specs_to_add


# def solve_for_actions(prefix, r, specs_to_remove=(), specs_to_add=(), prune=False):
#     # this is not for force-removing packages, which doesn't invoke the solver
#
#     solved_dists, _specs_to_add = solve_prefix(prefix, r, specs_to_remove, specs_to_add, prune)
#     # TODO: this _specs_to_add part should be refactored when we can better pin package channel
#     #     origin  # NOQA
#     dists_for_unlinking, dists_for_linking = sort_unlink_link_from_solve(prefix, solved_dists,
#                                                                          _specs_to_add)
#
#     def remove_non_matching_dists(dists_set, specs_to_match):
#         _dists_set = IndexedSet(dists_set)
#         for dist in dists_set:
#             for spec in specs_to_match:
#                 if spec.match(dist):
#                     break
#             else:  # executed if the loop ended normally (no break)
#                 _dists_set.remove(dist)
#         return _dists_set
#
#     if context.no_dependencies:
#         # for `conda create --no-deps python=3 flask`, do we install python? yes
#         # the only dists we touch are the ones that match a specs_to_add
#         dists_for_linking = remove_non_matching_dists(dists_for_linking, specs_to_add)
#         dists_for_unlinking = remove_non_matching_dists(dists_for_unlinking, specs_to_add)
#     elif context.only_dependencies:
#         # for `conda create --only-deps python=3 flask`, do we install python? yes
#         # remove all dists that match a specs_to_add, as long as that dist isn't a dependency
#         #   of other specs_to_add
#         _index = r.index
#         _match_any = lambda spec, dists: next((dist for dist in dists
#                                                if spec.match(_index[dist])),
#                                               None)
#         _is_dependency = lambda spec, dist: any(r.depends_on(s, dist.name)
#                                                 for s in specs_to_add if s != spec)
#         for spec in specs_to_add:
#             link_matching_dist = _match_any(spec, dists_for_linking)
#             if link_matching_dist:
#                 if not _is_dependency(spec, link_matching_dist):
#                     # as long as that dist isn't a dependency of other specs_to_add
#                     dists_for_linking.remove(link_matching_dist)
#                     unlink_matching_dist = _match_any(spec, dists_for_unlinking)
#                     if unlink_matching_dist:
#                         dists_for_unlinking.remove(unlink_matching_dist)
#
#     if context.force:
#         dists_for_unlinking, dists_for_linking = forced_reinstall_specs(prefix, solved_dists,
#                                                                         dists_for_unlinking,
#                                                                         dists_for_linking,
#                                                                         specs_to_add)
#
#     dists_for_unlinking = IndexedSet(reversed(dists_for_unlinking))
#     return dists_for_unlinking, dists_for_linking


# def sort_unlink_link_from_solve(prefix, solved_dists, remove_satisfied_specs):
#     # solved_dists should be the return value of solve_prefix()
#     old_linked_dists = IndexedSet(iterkeys(linked_data(prefix)))
#
#     dists_for_unlinking = old_linked_dists - solved_dists
#     dists_for_linking = solved_dists - old_linked_dists
#
#     # TODO: add back 'noarch: python' to unlink and link if python version changes
#
#     # r_linked = Resolve(linked_data(prefix))
#     # for spec in remove_satisfied_specs:
#     #     if r_linked.find_matches(spec):
#     #         spec_name = spec.name
#     #         unlink_dist = next((d for d in dists_for_unlinking if d.name == spec_name), None)
#     #         link_dist = next((d for d in dists_for_linking if d.name == spec_name), None)
#     #         if unlink_dist:
#     #             dists_for_unlinking.discard(unlink_dist)
#     #         if link_dist:
#     #             dists_for_linking.discard(link_dist)
#
#     return dists_for_unlinking, dists_for_linking


# def get_install_transaction(prefix, index, spec_strs, force=False, only_names=None,
#                             always_copy=False, pinned=True, update_deps=True,
#                             prune=False, channel_priority_map=None, is_update=False):
#     # type: (str, Dict[Dist, Record], List[str], bool, Option[List[str]], bool, bool, bool,
#     #        bool, bool, bool, Dict[str, Sequence[str, int]]) -> List[Dict[weird]]
#
#     # split out specs into potentially multiple preferred envs if:
#     #  1. the user default env (root_prefix) is the prefix being considered here
#     #  2. the user has not specified the --name or --prefix command-line flags
#     if (prefix == context.root_prefix
#             and not context.prefix_specified
#             and prefix_is_writable(prefix)
#             and context.enable_private_envs):
#
#         # a registered package CANNOT be installed in the root env
#         # if ANY package requesting a private env is required in the root env, all packages for
#         #   that requested env must instead be installed in the root env
#
#         root_r = get_resolve_object(index.copy(), context.root_prefix)
#
#         def get_env_for_spec(spec):
#             # use resolve's get_dists_for_spec() to find the "best" matching record
#             record_for_spec = root_r.index[root_r.get_dists_for_spec(spec, emptyok=False)[-1]]
#             return ensure_pad(record_for_spec.preferred_env)
#
#         # specs grouped by target env, the 'None' key holds the specs for the root env
#         env_add_map = groupby(get_env_for_spec, (MatchSpec(s) for s in spec_strs))
#         requested_root_specs_to_add = {s for s in env_add_map.pop(None, ())}
#
#         ed = EnvsDirectory(join(context.root_prefix, 'envs'))
#         registered_packages = ed.get_registered_packages_keyed_on_env_name()
#
#         if len(env_add_map) == len(registered_packages) == 0:
#             # short-circuit the rest of this logic
#             return get_install_transaction_single(prefix, index, spec_strs, force, only_names,
#                                                   always_copy, pinned, update_deps,
#                                                   prune, channel_priority_map, is_update)
#
#         root_specs_to_remove = set(MatchSpec(s.name) for s in concat(itervalues(env_add_map)))
#         required_root_dists, _ = solve_prefix(context.root_prefix, root_r,
#                                               specs_to_remove=root_specs_to_remove,
#                                               specs_to_add=requested_root_specs_to_add,
#                                               prune=True)
#
#         required_root_package_names = tuple(d.name for d in required_root_dists)
#
#         # first handle pulling back requested specs to root
#         forced_root_specs_to_add = set()
#         pruned_env_add_map = defaultdict(list)
#         for env_name, specs in iteritems(env_add_map):
#             for spec in specs:
#                 spec_name = MatchSpec(spec).name
#                 if spec_name in required_root_package_names:
#                     forced_root_specs_to_add.add(spec)
#                 else:
#                     pruned_env_add_map[env_name].append(spec)
#         env_add_map = pruned_env_add_map
#
#         # second handle pulling back registered specs to root
#         env_remove_map = defaultdict(list)
#         for env_name, registered_package_entries in iteritems(registered_packages):
#             for rpe in registered_package_entries:
#                 if rpe['package_name'] in required_root_package_names:
#                     # ANY registered packages in this environment need to be pulled back
#                     for pe in registered_package_entries:
#                         # add an entry in env_remove_map
#                         # add an entry in forced_root_specs_to_add
#                         pname = pe['package_name']
#                         env_remove_map[env_name].append(MatchSpec(pname))
#                         forced_root_specs_to_add.add(MatchSpec(pe['requested_spec']))
#                 break
#
#         unlink_link_map = odict()
#
#         # solve all neede preferred_env prefixes
#         for env_name in set(concatv(env_add_map, env_remove_map)):
#             specs_to_add = env_add_map[env_name]
#             spec_to_remove = env_remove_map[env_name]
#             pfx = ed.preferred_env_to_prefix(env_name)
#             unlink, link = solve_for_actions(pfx, get_resolve_object(index.copy(), pfx),
#                                              specs_to_remove=spec_to_remove,
#                                              specs_to_add=specs_to_add,
#                                              prune=True)
#             unlink_link_map[env_name] = unlink, link, specs_to_add
#
#         # now solve root prefix
#         # we have to solve root a second time in all cases, because this time we don't prune
#         root_specs_to_add = set(concatv(requested_root_specs_to_add, forced_root_specs_to_add))
#         root_unlink, root_link = solve_for_actions(context.root_prefix, root_r,
#                                                    specs_to_remove=root_specs_to_remove,
#                                                    specs_to_add=root_specs_to_add)
#         if root_unlink or root_link:
#             # this needs to be added to odict last; the private envs need to be updated first
#             unlink_link_map[None] = root_unlink, root_link, root_specs_to_add
#
#         def make_txn_setup(pfx, unlink, link, specs):
#             # TODO: this index here is probably wrong; needs to be per-prefix
#             return PrefixSetup(index, pfx, unlink, link, 'INSTALL',
#                                tuple(specs))
#
#         txn_args = tuple(make_txn_setup(ed.to_prefix(ensure_pad(env_name)), *oink)
#                          for env_name, oink in iteritems(unlink_link_map))
#         txn = UnlinkLinkTransaction(*txn_args)
#         return txn
#
#     else:
#         # disregard any requested preferred env
#         return get_install_transaction_single(prefix, index, spec_strs, force, only_names,
#                                               always_copy, pinned, update_deps,
#                                               prune, channel_priority_map, is_update)
