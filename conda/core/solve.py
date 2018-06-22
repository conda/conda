# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

from genericpath import exists
from logging import DEBUG, getLogger
from os.path import join
import sys
from textwrap import dedent

from .index import get_reduced_index
from .link import PrefixSetup, UnlinkLinkTransaction
from .prefix_data import PrefixData
from .subdir_data import SubdirData
from .. import CondaError, __version__ as CONDA_VERSION
from .._vendor.auxlib.ish import dals
from .._vendor.boltons.setutils import IndexedSet
from ..base.constants import DepsModifier, UNKNOWN_CHANNEL, UpdateModifier
from ..base.context import context
from ..common.compat import iteritems, text_type
from ..common.constants import NULL
from ..common.io import Spinner
from ..common.path import get_major_minor_version, paths_equal
from ..exceptions import PackagesNotFoundError
from ..gateways.logging import TRACE
from ..history import History
from ..models.channel import Channel
from ..models.enums import NoarchType
from ..models.match_spec import MatchSpec
from ..models.prefix_graph import PrefixGraph
from ..models.specs_group import SpecsGroup
from ..models.version import VersionOrder
from ..resolve import Resolve, dashlist

try:
    from cytoolz.itertoolz import concat, concatv, groupby
except ImportError:
    from .._vendor.toolz.itertoolz import concat, concatv, groupby  # NOQA

log = getLogger(__name__)


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
        self.specs_to_add = frozenset(MatchSpec.merge(s for s in specs_to_add))
        self.specs_to_remove = frozenset(MatchSpec.merge(s for s in specs_to_remove))

        assert all(s in context.known_subdirs for s in self.subdirs)
        self._index = None
        self._r = None
        self._prepared = False

    def solve_final_state(self, update_modifier=NULL, deps_modifier=NULL, prune=NULL,
                          ignore_pinned=NULL, force_remove=NULL):
        """Gives the final, solved state of the environment.

        Args:
            update_modifier (UpdateModifier):
                An optional flag directing how updates are handled regarding packages already
                existing in the environment.

            deps_modifier (DepsModifier):
                An optional flag indicating special solver handling for dependencies. The
                default solver behavior is to be as conservative as possible with dependency
                updates (in the case the dependency already exists in the environment), while
                still ensuring all dependencies are satisfied.  Options include
                    * NO_DEPS
                    * ONLY_DEPS
                    * UPDATE_DEPS
                    * UPDATE_DEPS_ONLY_DEPS
                    * FREEZE_INSTALLED
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
        if update_modifier is NULL:
            update_modifier = context.update_modifier
        else:
            update_modifier = UpdateModifier(text_type(update_modifier).lower())
        if deps_modifier is NULL:
            deps_modifier = context.deps_modifier
        else:
            deps_modifier = DepsModifier(text_type(deps_modifier).lower())
        prune = context.prune if prune is NULL else prune
        ignore_pinned = context.ignore_pinned if ignore_pinned is NULL else ignore_pinned
        force_remove = context.force_remove if force_remove is NULL else force_remove
        specs_to_remove = self.specs_to_remove
        specs_to_add = self.specs_to_add

        # force_remove is a special case where we return early
        if specs_to_remove and force_remove:
            if specs_to_add:
                raise NotImplementedError()
            solution = tuple(prec for prec in PrefixData(self.prefix).iter_records()
                             if not any(spec.match(prec) for spec in specs_to_remove))
            return IndexedSet(PrefixGraph(solution).graph)

        log.debug("solving prefix %s\n"
                  "  specs_to_remove: %s\n"
                  "  specs_to_add: %s\n"
                  "  prune: %s", self.prefix, specs_to_remove, specs_to_add, prune)

        # declare starting point, the initial state of the environment
        # `solution` and `specs_map` are mutated throughout this method
        prefix_data = PrefixData(self.prefix)
        solution = tuple(prec for prec in prefix_data.iter_records())

        # Check if specs are satisfied by current environment. If they are, exit early.
        if (update_modifier == UpdateModifier.SPECS_SATISFIED_SKIP_SOLVE
                and not specs_to_remove and not prune):
            for spec in specs_to_add:
                if not next(prefix_data.query(spec), None):
                    break
            else:
                # All specs match a package in the current environment.
                # Return early, with a solution that should just be PrefixData().iter_records()
                return IndexedSet(PrefixGraph(solution).graph)

        specs_group_from_history = History(self.prefix).get_requested_specs()
        if prune:  # or update_modifier == UpdateModifier.UPDATE_ALL  # pending conda/constructor#138  # NOQA
            # Users are struggling with the prune functionality in --update-all, due to
            # https://github.com/conda/constructor/issues/138.  Until that issue is resolved,
            # and for the foreseeable future, it's best to be more conservative with --update-all.

            # Start with empty specs map for UPDATE_ALL because we're optimizing the update
            # only for specs the user has requested; it's ok to remove dependencies.
            specs_group = SpecsGroup()

            # However, because of https://github.com/conda/constructor/issues/138, we need
            # to hard-code keeping conda, conda-build, and anaconda, if they're already in
            # the environment.
            solution_pkg_names = set(d.name for d in solution)
            specs_from_history_names = set(specs_group_from_history._specs_map)
            ensure_these = (pkg_name for pkg_name in {
                'anaconda', 'conda', 'conda-build',
            } if pkg_name not in specs_from_history_names and pkg_name in solution_pkg_names)
            for pkg_name in ensure_these:
                specs_group.add(MatchSpec(pkg_name))
        else:
            specs_group = SpecsGroup(
                MatchSpec(namespace=prec.namespace, name=prec.name) for prec in solution
            )

        # add in historically-requested specs
        specs_group.update(specs_group_from_history)

        # let's pretend for now that this is the right place to build the index
        prepared_specs = set(concatv(
            specs_to_remove,
            specs_to_add,
            specs_group.iter_specs(),
        ))

        index, r = self._prepare(prepared_specs)

        if specs_to_remove:
            # In a previous implementation, we invoked SAT here via `r.remove()` to help with
            # spec removal, and then later invoking SAT again via `r.solve()`. Rather than invoking
            # SAT for spec removal determination, we can use the PrefixGraph and simple tree
            # traversal if we're careful about how we handle features. We still invoke sat via
            # `r.solve()` later.
            _track_fts_specs = (spec for spec in specs_to_remove if 'track_features' in spec)
            feature_names = set(concat(spec.get_raw_value('track_features')
                                       for spec in _track_fts_specs))
            graph = PrefixGraph(solution, specs_group.iter_specs())

            all_removed_records = []
            no_removed_records_specs = []
            for spec in specs_to_remove:
                # If the spec was a track_features spec, then we need to also remove every
                # package with a feature that matches the track_feature. The
                # `graph.remove_spec()` method handles that for us.
                log.trace("using PrefixGraph to remove records for %s", spec)
                removed_records = graph.remove_spec(spec)
                if removed_records:
                    all_removed_records.extend(removed_records)
                else:
                    no_removed_records_specs.append(spec)

            # ensure that each spec in specs_to_remove is actually associated with removed records
            unmatched_specs_to_remove = tuple(
                spec for spec in no_removed_records_specs
                if not any(spec.match(rec) for rec in all_removed_records)
            )
            if unmatched_specs_to_remove:
                raise PackagesNotFoundError(
                    tuple(sorted(str(s) for s in unmatched_specs_to_remove))
                )

            for rec in all_removed_records:
                # We keep specs (minus the feature part) for the non provides_features packages
                # if they're in the history specs.  Otherwise, we pop them from the specs_map.
                rec_has_a_feature = set(rec.features or ()) & feature_names
                if rec_has_a_feature and specs_group_from_history.get_specs_by_name(rec.name):
                    for spec in specs_group.get_matches(rec):
                        new_spec = MatchSpec(spec)
                        new_spec._match_components.pop('features', None)
                        specs_group.add(new_spec)
                else:
                    specs_group.remove_record_match(rec)

            solution = tuple(graph.graph)

        # We handle as best as possible environments in inconsistent states. To do this,
        # we remove now from consideration the set of packages causing inconsistencies,
        # and then we add them back in following the main SAT call.
        _, inconsistent_precs = r.bad_installed(solution, ())
        add_back_map = {}  # name: (prec, List[MatchSpec])
        if log.isEnabledFor(DEBUG):
            log.debug("inconsistent precs: %s",
                      dashlist(inconsistent_precs) if inconsistent_precs else 'None')
        if inconsistent_precs:
            for prec in inconsistent_precs:
                # pop and save matching spec in specs_map
                matches = specs_group.get_specs_by_name(prec.name, namespace=prec.namespace)
                for spec in matches:
                    specs_group.remove(spec)
                add_back_map[prec] = matches
            solution = tuple(prec for prec in solution if prec not in inconsistent_precs)

        # For the remaining specs in specs_map, add target to each spec. `target` is a reference
        # to the package currently existing in the environment. Setting target instructs the
        # solver to not disturb that package if it's not necessary.
        # If the spec.name is being modified by inclusion in specs_to_add, we don't set `target`,
        # since we *want* the solver to modify/update that package.
        #
        # TLDR: when working with MatchSpec objects,
        #  - to minimize the version change, set MatchSpec(name=name, target=prec.dist_str())
        #  - to freeze the package, set all the components of MatchSpec individually
        for spec in specs_group.iter_specs():
            matches_for_spec = tuple(prec for prec in solution if spec.match(prec))
            if matches_for_spec:
                if len(matches_for_spec) != 1:
                    raise CondaError(dals("""
                    Conda encountered an error with your environment.  Please report an issue
                    at https://github.com/conda/conda/issues/new.  In your report, please include
                    the output of 'conda info' and 'conda list' for the active environment, along
                    with the command you invoked that resulted in this error.
                      pkg_name: %s
                      spec: %s
                      matches_for_spec: %s
                    """) % (spec.name, spec,
                            dashlist((text_type(s) for s in matches_for_spec), indent=4)))
                target_prec = matches_for_spec[0]
                if update_modifier == UpdateModifier.FREEZE_INSTALLED:
                    new_spec = MatchSpec(target_prec)
                else:
                    target = target_prec.dist_str()
                    new_spec = MatchSpec(spec, target=target)
                specs_group.add(new_spec)
        if log.isEnabledFor(TRACE):
            log.trace("specs_map with targets: %s", specs_group)

        # If we're in UPDATE_ALL mode, we need to drop all the constraints attached to specs,
        # so they can all float and the solver can find the most up-to-date solution. In the case
        # of UPDATE_ALL, `specs_map` wasn't initialized with packages from the current environment,
        # but *only* historically-requested specs.  This lets UPDATE_ALL drop dependencies if
        # they're no longer needed, and their presence would otherwise prevent the updated solution
        # the user most likely wants.
        if update_modifier == UpdateModifier.UPDATE_ALL:
            _specs = groupby(lambda s: s.name != '*', specs_group.iter_specs())
            specs_group = SpecsGroup(concatv(
                (MatchSpec(namespace=spec.namespace, name=spec.name, optional=spec.optional)
                 for spec in _specs.get(True, ())),
                _specs.get(False, ()),
            ))

        # As a business rule, we never want to update python beyond the current minor version,
        # unless that's requested explicitly by the user (which we actively discourage).
        python_specs = specs_group.get_specs_by_name('python')
        if python_specs:
            python_prefix_rec = prefix_data.get('python')
            if python_prefix_rec:
                assert len(python_specs) == 1, python_specs
                python_spec = python_specs[0]
                if not python_spec.get('version'):
                    pinned_version = get_major_minor_version(python_prefix_rec.version) + '.*'
                    specs_group.add(MatchSpec(python_spec, version=pinned_version))

        # For the aggressive_update_packages configuration parameter, we strip any target
        # that's been set.
        if not context.offline:
            for spec in context.aggressive_update_packages:
                name_matches = specs_group.get_specs_by_name(spec.name)
                if name_matches:
                    specs_group.add(MatchSpec(namespace=spec.namespace, name=spec.name))
            if (context.auto_update_conda and paths_equal(self.prefix, context.root_prefix)
                    and any(prec.name == "conda" for prec in solution)):
                specs_group.add(MatchSpec("conda"))

        # add in explicitly requested specs from specs_to_add
        # this overrides any name-matching spec already in the spec map
        for spec in specs_to_add:
            specs_group.add(spec)

        # collect additional specs to add to the solution
        track_features_specs = pinned_specs = ()
        if context.track_features:
            track_features_specs = tuple(MatchSpec(x + '@') for x in context.track_features)
        if not ignore_pinned:
            pinned_specs = get_pinned_specs(self.prefix)

        final_environment_specs = IndexedSet(concatv(
            specs_group.iter_specs(),
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
        if log.isEnabledFor(DEBUG):
            log.debug("conflicting specs: %s", dashlist(conflicting_specs))
        for spec in conflicting_specs:
            if spec.target:
                final_environment_specs.remove(spec)
                neutered_spec = MatchSpec(spec.name, target=spec.target, optional=True)
                final_environment_specs.add(neutered_spec)

        # Finally! We get to call SAT.
        if log.isEnabledFor(DEBUG):
            log.debug("final specs to add: %s",
                      dashlist(sorted(text_type(s) for s in final_environment_specs)))
        solution = r.solve(tuple(final_environment_specs))  # return value is List[PackageRecord]

        # add back inconsistent packages to solution
        for prec, specs in iteritems(add_back_map):
            package_name = prec.name
            if not any(d.name == package_name for d in solution):
                solution.append(prec)
                if specs:
                    final_environment_specs.update(specs)

        # Special case handling for various DepsModifier flags. Maybe this block could be pulled
        # out into its own non-public helper method?
        if deps_modifier == DepsModifier.NO_DEPS:
            # In the NO_DEPS case, we need to start with the original list of packages in the
            # environment, and then only modify packages that match specs_to_add or
            # specs_to_remove.
            _no_deps_solution = IndexedSet(prefix_data.iter_records())
            only_remove_these = set(prec
                                    for spec in specs_to_remove
                                    for prec in _no_deps_solution
                                    if spec.match(prec))
            _no_deps_solution -= only_remove_these

            only_add_these = set(prec
                                 for spec in specs_to_add
                                 for prec in solution
                                 if spec.match(prec))
            remove_before_adding_back = set(prec.name for prec in only_add_these)
            _no_deps_solution = IndexedSet(prec for prec in _no_deps_solution
                                           if prec.name not in remove_before_adding_back)
            _no_deps_solution |= only_add_these
            solution = _no_deps_solution
        elif (deps_modifier == DepsModifier.ONLY_DEPS
                and update_modifier != UpdateModifier.UPDATE_DEPS):
            # Using a special instance of PrefixGraph to remove youngest child nodes that match
            # the original specs_to_add.  It's important to remove only the *youngest* child nodes,
            # because a typical use might be `conda install --only-deps python=2 flask`, and in
            # that case we'd want to keep python.
            graph = PrefixGraph(solution, specs_to_add)
            graph.remove_youngest_descendant_nodes_with_specs()
            solution = tuple(graph.graph)

        elif update_modifier == UpdateModifier.UPDATE_DEPS:
            # Here we have to SAT solve again :(  It's only now that we know the dependency
            # chain of specs_to_add.
            specs_to_add_names = set(spec.name for spec in specs_to_add)
            update_names = set()
            graph = PrefixGraph(solution, final_environment_specs)
            for spec in specs_to_add:
                node = graph.get_node_by_name(spec.name)
                for ancestor_record in graph.all_ancestors(node):
                    ancestor_name = ancestor_record.name
                    if ancestor_name not in specs_to_add_names:
                        update_names.add(ancestor_name)
            grouped_specs = groupby(lambda s: s.name in update_names, final_environment_specs)
            new_final_environment_specs = set(grouped_specs.get(False, ()))
            update_specs = set(MatchSpec(spec.name, optional=spec.optional)
                               for spec in grouped_specs.get(True, ()))
            final_environment_specs = new_final_environment_specs | update_specs
            solution = r.solve(final_environment_specs)

            if deps_modifier == DepsModifier.ONLY_DEPS:
                # duplicated from DepsModifier.ONLY_DEPS
                graph = PrefixGraph(solution, specs_to_add)
                graph.remove_youngest_descendant_nodes_with_specs()
                solution = tuple(graph.graph)

        if prune:
            graph = PrefixGraph(solution, final_environment_specs)
            graph.prune()
            solution = tuple(graph.graph)

        self._check_solution(solution, pinned_specs)

        solution = IndexedSet(PrefixGraph(solution).graph)
        log.debug("solved prefix %s\n"
                  "  solved_linked_dists:\n"
                  "    %s\n",
                  self.prefix, "\n    ".join(prec.dist_str() for prec in solution))
        return solution

    def solve_for_diff(self, update_modifier=NULL, deps_modifier=NULL, prune=NULL,
                       ignore_pinned=NULL, force_remove=NULL, force_reinstall=NULL):
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
        final_precs = self.solve_final_state(update_modifier, deps_modifier, prune, ignore_pinned,
                                             force_remove)
        unlink_precs, link_precs = diff_for_unlink_link_precs(
            self.prefix, final_precs, self.specs_to_add, force_reinstall
        )
        return unlink_precs, link_precs

    def solve_for_transaction(self, update_modifier=NULL, deps_modifier=NULL, prune=NULL,
                              ignore_pinned=NULL, force_remove=NULL, force_reinstall=NULL):
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
        if self.prefix == context.root_prefix and context.enable_private_envs:
            # This path has the ability to generate a multi-prefix transaction. The basic logic
            # is in the commented out get_install_transaction() function below. Exercised at
            # the integration level in the PrivateEnvIntegrationTests in test_create.py.
            raise NotImplementedError()
        else:
            with Spinner("Solving environment", not context.verbosity and not context.quiet,
                         context.json):
                unlink_precs, link_precs = self.solve_for_diff(update_modifier, deps_modifier,
                                                               prune, ignore_pinned,
                                                               force_remove, force_reinstall)
                stp = PrefixSetup(self.prefix, unlink_precs, link_precs,
                                  self.specs_to_remove, self.specs_to_add)
                # TODO: Only explicitly requested remove and update specs are being included in
                #   History right now. Do we need to include other categories from the solve?

            self._notify_conda_outdated(link_precs)
            return UnlinkLinkTransaction(stp)

    def _notify_conda_outdated(self, link_precs):
        if not context.notify_outdated_conda or context.quiet:
            return
        current_conda_prefix_rec = PrefixData(context.conda_prefix).get('conda', None)
        if current_conda_prefix_rec:
            channel_name = current_conda_prefix_rec.channel.canonical_name
            if channel_name == UNKNOWN_CHANNEL:
                channel_name = "defaults"

            # only look for a newer conda in the channel conda is currently installed from
            conda_newer_spec = MatchSpec('%s::conda>%s' % (channel_name, CONDA_VERSION))

            if paths_equal(self.prefix, context.conda_prefix):
                if any(conda_newer_spec.match(prec) for prec in link_precs):
                    return

            conda_newer_precs = sorted(
                SubdirData.query_all(conda_newer_spec, self.channels, self.subdirs),
                key=lambda x: VersionOrder(x.version)
                # VersionOrder is fine here rather than r.version_key because all precs
                # should come from the same channel
            )
            if conda_newer_precs:
                latest_version = conda_newer_precs[-1].version
                # If conda comes from defaults, ensure we're giving instructions to users
                # that should resolve release timing issues between defaults and conda-forge.
                add_channel = "-c defaults " if channel_name == "defaults" else ""
                print(dedent("""

                ==> WARNING: A newer version of conda exists. <==
                  current version: %s
                  latest version: %s

                Please update conda by running

                    $ conda update -n base %sconda

                """) % (CONDA_VERSION, latest_version, add_channel), file=sys.stderr)

    def _prepare(self, prepared_specs):
        # All of this _prepare() method is hidden away down here. Someday we may want to further
        # abstract away the use of `index` or the Resolve object.

        if self._prepared and prepared_specs == self._prepared_specs:
            return self._index, self._r

        if hasattr(self, '_index') and self._index:
            # added in install_actions for conda-build back-compat
            self._prepared_specs = prepared_specs
            self._r = Resolve(self._index, channels=self.channels)
        else:
            # add in required channels that aren't explicitly given in the channels list
            # For correctness, we should probably add to additional_channels any channel that
            #  is given by PrefixData(self.prefix).all_subdir_urls().  However that causes
            #  usability problems with bad / expired tokens.

            additional_channels = set()
            for spec in self.specs_to_add:
                # TODO: correct handling for subdir isn't yet done
                channel = spec.get_exact_value('channel')
                if channel:
                    additional_channels.add(Channel(channel))

            self.channels.update(additional_channels)
            reduced_index = get_reduced_index(self.prefix, self.channels,
                                              self.subdirs, prepared_specs)
            self._prepared_specs = prepared_specs
            self._index = reduced_index
            self._r = Resolve(reduced_index, channels=self.channels)

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


def diff_for_unlink_link_precs(prefix, final_precs, specs_to_add=(), force_reinstall=NULL):
    assert isinstance(final_precs, IndexedSet)
    final_precs = final_precs
    previous_records = IndexedSet(PrefixGraph(PrefixData(prefix).iter_records()).graph)
    force_reinstall = context.force_reinstall if force_reinstall is NULL else force_reinstall

    unlink_precs = previous_records - final_precs
    link_precs = final_precs - previous_records

    def _add_to_unlink_and_link(rec):
        link_precs.add(rec)
        if prec in previous_records:
            unlink_precs.add(rec)

    # If force_reinstall is enabled, make sure any package in specs_to_add is unlinked then
    # re-linked
    if force_reinstall:
        for spec in specs_to_add:
            prec = next((rec for rec in final_precs if spec.match(rec)), None)
            assert prec
            _add_to_unlink_and_link(prec)

    # add back 'noarch: python' packages to unlink and link if python version changes
    python_spec = MatchSpec('python')
    prev_python = next((rec for rec in previous_records if python_spec.match(rec)), None)
    curr_python = next((rec for rec in final_precs if python_spec.match(rec)), None)
    gmm = get_major_minor_version
    if prev_python and curr_python and gmm(prev_python.version) != gmm(curr_python.version):
        noarch_python_precs = (p for p in final_precs if p.noarch == NoarchType.python)
        for prec in noarch_python_precs:
            _add_to_unlink_and_link(prec)

    unlink_precs = IndexedSet(reversed(sorted(unlink_precs,
                                              key=lambda x: previous_records.index(x))))
    link_precs = IndexedSet(sorted(link_precs, key=lambda x: final_precs.index(x)))
    return unlink_precs, link_precs


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
