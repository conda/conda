# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

import copy
from genericpath import exists
from logging import DEBUG, getLogger
from os.path import join
import sys
from textwrap import dedent
from itertools import chain
from collections import defaultdict

from .index import get_reduced_index, _supplement_index_with_system
from .link import PrefixSetup, UnlinkLinkTransaction
from .package_cache_data import PackageCacheData
from .prefix_data import PrefixData
from .subdir_data import SubdirData
from .. import CondaError, __version__ as CONDA_VERSION
from .._vendor.auxlib.decorators import memoizedproperty
from .._vendor.auxlib.ish import dals
from .._vendor.boltons.setutils import IndexedSet
from .._vendor.toolz import concat, concatv, groupby
from ..base.constants import (DepsModifier, UNKNOWN_CHANNEL, UpdateModifier, REPODATA_FN,
                              ChannelPriority)
from ..base.context import context
from ..common.compat import iteritems, itervalues, odict, text_type
from ..common.constants import NULL
from ..common.io import Spinner, dashlist, time_recorder
from ..common.path import get_major_minor_version, paths_equal
from ..common.url import escape_channel_url, split_anaconda_token, remove_auth
from ..exceptions import (PackagesNotFoundError, SpecsConfigurationConflictError,
                          UnsatisfiableError, RawStrUnsatisfiableError)
from ..history import History
from ..models.channel import Channel
from ..models.enums import NoarchType
from ..models.match_spec import MatchSpec
from ..models.prefix_graph import PrefixGraph
from ..models.version import VersionOrder
from ..resolve import Resolve

log = getLogger(__name__)


def _get_solver_logic(key=None):
    key = key or str(context.solver_logic)
    return {
        "legacy": Solver,
        "libsolv": LibSolvSolver,
    }[key]


class Solver(object):
    """
    A high-level API to conda's solving logic. Three public methods are provided to access a
    solution in various forms.

      * :meth:`solve_final_state`
      * :meth:`solve_for_diff`
      * :meth:`solve_for_transaction`

    """
    _uses_ssc = True  # used in tests

    def __init__(self, prefix, channels, subdirs=(), specs_to_add=(), specs_to_remove=(),
                 repodata_fn=REPODATA_FN, command=NULL):
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
        self._channels = channels or context.channels
        self.channels = IndexedSet(Channel(c) for c in self._channels)
        self.subdirs = tuple(s for s in subdirs or context.subdirs)
        self.specs_to_add = frozenset(MatchSpec.merge(s for s in specs_to_add))
        self.specs_to_add_names = frozenset(_.name for _ in self.specs_to_add)
        self.specs_to_remove = frozenset(MatchSpec.merge(s for s in specs_to_remove))
        self.neutered_specs = tuple()
        self._command = command

        assert all(s in context.known_subdirs for s in self.subdirs)
        self._repodata_fn = repodata_fn
        self._index = None
        self._r = None
        self._prepared = False
        self._pool_cache = {}

    def solve_for_transaction(self, update_modifier=NULL, deps_modifier=NULL, prune=NULL,
                              ignore_pinned=NULL, force_remove=NULL, force_reinstall=NULL,
                              should_retry_solve=False):
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
            should_retry_solve (bool):
                See :meth:`solve_final_state`.

        Returns:
            UnlinkLinkTransaction:

        """
        if self.prefix == context.root_prefix and context.enable_private_envs:
            # This path has the ability to generate a multi-prefix transaction. The basic logic
            # is in the commented out get_install_transaction() function below. Exercised at
            # the integration level in the PrivateEnvIntegrationTests in test_create.py.
            raise NotImplementedError()
        else:
            unlink_precs, link_precs = self.solve_for_diff(update_modifier, deps_modifier,
                                                           prune, ignore_pinned,
                                                           force_remove, force_reinstall,
                                                           should_retry_solve)
            stp = PrefixSetup(self.prefix, unlink_precs, link_precs,
                              self.specs_to_remove, self.specs_to_add, self.neutered_specs)
            # TODO: Only explicitly requested remove and update specs are being included in
            #   History right now. Do we need to include other categories from the solve?

            self._notify_conda_outdated(link_precs)
            return UnlinkLinkTransaction(stp)

    def solve_for_diff(self, update_modifier=NULL, deps_modifier=NULL, prune=NULL,
                       ignore_pinned=NULL, force_remove=NULL, force_reinstall=NULL,
                       should_retry_solve=False):
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
            should_retry_solve (bool):
                See :meth:`solve_final_state`.

        Returns:
            Tuple[PackageRef], Tuple[PackageRef]:
                A two-tuple of PackageRef sequences.  The first is the group of packages to
                remove from the environment, in sorted dependency order from leaves to roots.
                The second is the group of packages to add to the environment, in sorted
                dependency order from roots to leaves.

        """
        final_precs = self.solve_final_state(update_modifier, deps_modifier, prune, ignore_pinned,
                                             force_remove, should_retry_solve)
        unlink_precs, link_precs = diff_for_unlink_link_precs(
            self.prefix, final_precs, self.specs_to_add, force_reinstall
        )

        # assert that all unlink_precs are manageable
        unmanageable = groupby(lambda prec: prec.is_unmanageable, unlink_precs).get(True)
        if unmanageable:
            raise RuntimeError("Cannot unlink unmanageable packages:%s"
                               % dashlist(prec.record_id() for prec in unmanageable))

        return unlink_precs, link_precs

    def solve_final_state(self, update_modifier=NULL, deps_modifier=NULL, prune=NULL,
                          ignore_pinned=NULL, force_remove=NULL, should_retry_solve=False):
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
            should_retry_solve (bool):
                Indicates whether this solve will be retried. This allows us to control
                whether to call find_conflicts (slow) in ssc.r.solve

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
        ignore_pinned = context.ignore_pinned if ignore_pinned is NULL else ignore_pinned
        force_remove = context.force_remove if force_remove is NULL else force_remove

        log.debug("solving prefix %s\n"
                  "  specs_to_remove: %s\n"
                  "  specs_to_add: %s\n"
                  "  prune: %s", self.prefix, self.specs_to_remove, self.specs_to_add, prune)

        retrying = hasattr(self, 'ssc')

        if not retrying:
            ssc = SolverStateContainer(
                self.prefix, update_modifier, deps_modifier, prune, ignore_pinned, force_remove,
                should_retry_solve,
            )
            self.ssc = ssc
        else:
            ssc = self.ssc
            ssc.update_modifier = update_modifier
            ssc.deps_modifier = deps_modifier
            ssc.should_retry_solve = should_retry_solve

        # force_remove is a special case where we return early
        if self.specs_to_remove and force_remove:
            if self.specs_to_add:
                raise NotImplementedError()
            solution = tuple(prec for prec in ssc.solution_precs
                             if not any(spec.match(prec) for spec in self.specs_to_remove))
            return IndexedSet(PrefixGraph(solution).graph)

        # Check if specs are satisfied by current environment. If they are, exit early.
        if (update_modifier == UpdateModifier.SPECS_SATISFIED_SKIP_SOLVE
                and not self.specs_to_remove and not prune):
            for spec in self.specs_to_add:
                if not next(ssc.prefix_data.query(spec), None):
                    break
            else:
                # All specs match a package in the current environment.
                # Return early, with a solution that should just be PrefixData().iter_records()
                return IndexedSet(PrefixGraph(ssc.solution_precs).graph)

        if not ssc.r:
            with Spinner("Collecting package metadata (%s)" % self._repodata_fn,
                         (not context.verbosity and not context.quiet and not retrying),
                         context.json):
                ssc = self._collect_all_metadata(ssc)

        if should_retry_solve and update_modifier == UpdateModifier.FREEZE_INSTALLED:
            fail_message = "failed with initial frozen solve. Retrying with flexible solve.\n"
        elif self._repodata_fn != REPODATA_FN:
            fail_message = ("failed with repodata from %s, will retry with next repodata"
                            " source.\n" % self._repodata_fn)
        else:
            fail_message = "failed\n"

        with Spinner("Solving environment", not context.verbosity and not context.quiet,
                     context.json, fail_message=fail_message):
            ssc = self._remove_specs(ssc)
            ssc = self._add_specs(ssc)
            solution_precs = copy.copy(ssc.solution_precs)

            pre_packages = self.get_request_package_in_solution(ssc.solution_precs, ssc.specs_map)
            ssc = self._find_inconsistent_packages(ssc)
            # this will prune precs that are deps of precs that get removed due to conflicts
            ssc = self._run_sat(ssc)
            post_packages = self.get_request_package_in_solution(ssc.solution_precs, ssc.specs_map)

            if ssc.update_modifier == UpdateModifier.UPDATE_SPECS:
                constrained = self.get_constrained_packages(
                    pre_packages, post_packages, ssc.index.keys())
                if len(constrained) > 0:
                    for spec in constrained:
                        self.determine_constricting_specs(spec, ssc.solution_precs)

            # if there were any conflicts, we need to add their orphaned deps back in
            if ssc.add_back_map:
                orphan_precs = (set(solution_precs)
                                - set(ssc.solution_precs)
                                - set(ssc.add_back_map))
                solution_prec_names = [_.name for _ in ssc.solution_precs]
                ssc.solution_precs.extend(
                    [_ for _ in orphan_precs
                     if _.name not in ssc.specs_map and _.name not in solution_prec_names])

            ssc = self._post_sat_handling(ssc)

        time_recorder.log_totals()

        ssc.solution_precs = IndexedSet(PrefixGraph(ssc.solution_precs).graph)
        log.debug("solved prefix %s\n"
                  "  solved_linked_dists:\n"
                  "    %s\n",
                  self.prefix, "\n    ".join(prec.dist_str() for prec in ssc.solution_precs))

        return ssc.solution_precs

    def determine_constricting_specs(self, spec, solution_precs):
        highest_version = [VersionOrder(sp.version) for sp in solution_precs
                           if sp.name == spec.name][0]
        constricting = []
        for prec in solution_precs:
            if any(j for j in prec.depends if spec.name in j):
                for dep in prec.depends:
                    m_dep = MatchSpec(dep)
                    if m_dep.name == spec.name and \
                            m_dep.version is not None and \
                            (m_dep.version.exact_value or "<" in m_dep.version.spec):
                        if "," in m_dep.version.spec:
                            constricting.extend([
                                (prec.name, MatchSpec("%s %s" % (m_dep.name, v)))
                                for v in m_dep.version.tup if "<" in v.spec])
                        else:
                            constricting.append((prec.name, m_dep))

        hard_constricting = [i for i in constricting if i[1].version.matcher_vo <= highest_version]
        if len(hard_constricting) == 0:
            return None

        print("\n\nUpdating {spec} is constricted by \n".format(spec=spec.name))
        for const in hard_constricting:
            print("{package} -> requires {conflict_dep}".format(
                package=const[0], conflict_dep=const[1]))
        print("\nIf you are sure you want an update of your package either try "
              "`conda update --all` or install a specific version of the "
              "package you want using `conda install <pkg>=<version>`\n")
        return hard_constricting

    def get_request_package_in_solution(self, solution_precs, specs_map):
        requested_packages = {}
        for pkg in self.specs_to_add:
            update_pkg_request = pkg.name

            requested_packages[update_pkg_request] = [
                (i.name, str(i.version)) for i in solution_precs
                if i.name == update_pkg_request and i.version is not None
            ]
            requested_packages[update_pkg_request].extend(
                [(v.name, str(v.version)) for k, v in specs_map.items()
                 if k == update_pkg_request and v.version is not None])

        return requested_packages

    def get_constrained_packages(self, pre_packages, post_packages, index_keys):
        update_constrained = set()

        def empty_package_list(pkg):
            for k, v in pkg.items():
                if len(v) == 0:
                    return True
            return False

        if empty_package_list(pre_packages) or empty_package_list(post_packages):
            return update_constrained

        for pkg in self.specs_to_add:
            if pkg.name.startswith('__'):  # ignore virtual packages
                continue
            current_version = max(i[1] for i in pre_packages[pkg.name])
            if current_version == max(i.version for i in index_keys if i.name == pkg.name):
                continue
            else:
                if post_packages == pre_packages:
                    update_constrained = update_constrained | set([pkg])
        return update_constrained

    @time_recorder(module_name=__name__)
    def _collect_all_metadata(self, ssc):
        # add in historically-requested specs
        ssc.specs_map.update(ssc.specs_from_history_map)

        # these are things that we want to keep even if they're not explicitly specified.  This
        #     is to compensate for older installers not recording these appropriately for them
        #     to be preserved.
        for pkg_name in ('anaconda', 'conda', 'conda-build', 'python.app',
                         'console_shortcut', 'powershell_shortcut'):
            if pkg_name not in ssc.specs_map and ssc.prefix_data.get(pkg_name, None):
                ssc.specs_map[pkg_name] = MatchSpec(pkg_name)

        # Add virtual packages so they are taken into account by the solver
        virtual_pkg_index = {}
        _supplement_index_with_system(virtual_pkg_index)
        virtual_pkgs = [p.name for p in virtual_pkg_index.keys()]
        for virtual_pkgs_name in (virtual_pkgs):
            if virtual_pkgs_name not in ssc.specs_map:
                ssc.specs_map[virtual_pkgs_name] = MatchSpec(virtual_pkgs_name)

        for prec in ssc.prefix_data.iter_records():
            # first check: add everything if we have no history to work with.
            #    This happens with "update --all", for example.
            #
            # second check: add in aggressively updated packages
            #
            # third check: add in foreign stuff (e.g. from pip) into the specs
            #    map. We add it so that it can be left alone more. This is a
            #    declaration that it is manually installed, much like the
            #    history map. It may still be replaced if it is in conflict,
            #    but it is not just an indirect dep that can be pruned.
            if (not ssc.specs_from_history_map
                    or MatchSpec(prec.name) in context.aggressive_update_packages
                    or prec.subdir == 'pypi'):
                ssc.specs_map.update({prec.name: MatchSpec(prec.name)})

        prepared_specs = set(concatv(
            self.specs_to_remove,
            self.specs_to_add,
            itervalues(ssc.specs_from_history_map),
        ))

        index, r = self._prepare(prepared_specs)
        ssc.set_repository_metadata(index, r)
        return ssc

    def _remove_specs(self, ssc):
        if self.specs_to_remove:
            # In a previous implementation, we invoked SAT here via `r.remove()` to help with
            # spec removal, and then later invoking SAT again via `r.solve()`. Rather than invoking
            # SAT for spec removal determination, we can use the PrefixGraph and simple tree
            # traversal if we're careful about how we handle features. We still invoke sat via
            # `r.solve()` later.
            _track_fts_specs = (spec for spec in self.specs_to_remove if 'track_features' in spec)
            feature_names = set(concat(spec.get_raw_value('track_features')
                                       for spec in _track_fts_specs))
            graph = PrefixGraph(ssc.solution_precs, itervalues(ssc.specs_map))

            all_removed_records = []
            no_removed_records_specs = []
            for spec in self.specs_to_remove:
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
                if rec_has_a_feature and rec.name in ssc.specs_from_history_map:
                    spec = ssc.specs_map.get(rec.name, MatchSpec(rec.name))
                    spec._match_components.pop('features', None)
                    ssc.specs_map[spec.name] = spec
                else:
                    ssc.specs_map.pop(rec.name, None)

            ssc.solution_precs = tuple(graph.graph)
        return ssc

    @time_recorder(module_name=__name__)
    def _find_inconsistent_packages(self, ssc):
        # We handle as best as possible environments in inconsistent states. To do this,
        # we remove now from consideration the set of packages causing inconsistencies,
        # and then we add them back in following the main SAT call.
        _, inconsistent_precs = ssc.r.bad_installed(ssc.solution_precs, ())
        if inconsistent_precs:
            # It is possible that the package metadata is incorrect, for example when
            # un-patched metadata from the Miniconda or Anaconda installer is present, see:
            # https://github.com/conda/conda/issues/8076
            # Update the metadata with information from the index and see if that makes the
            # environment consistent.
            ssc.solution_precs = tuple(ssc.index.get(k, k) for k in ssc.solution_precs)
            _, inconsistent_precs = ssc.r.bad_installed(ssc.solution_precs, ())
        if log.isEnabledFor(DEBUG):
            log.debug("inconsistent precs: %s",
                      dashlist(inconsistent_precs) if inconsistent_precs else 'None')
        if inconsistent_precs:
            print(dedent("""
            The environment is inconsistent, please check the package plan carefully
            The following packages are causing the inconsistency:"""), file=sys.stderr)
            print(dashlist(inconsistent_precs), file=sys.stderr)
            for prec in inconsistent_precs:
                # pop and save matching spec in specs_map
                spec = ssc.specs_map.pop(prec.name, None)
                ssc.add_back_map[prec.name] = (prec, spec)
                # let the package float.  This is essential to keep the package's dependencies
                #    in the solution
                ssc.specs_map[prec.name] = MatchSpec(prec.name, target=prec.dist_str())
                # inconsistent environments should maintain the python version
                # unless explicitly requested by the user. This along with the logic in
                # _add_specs maintains the major.minor version
                if prec.name == 'python' and spec:
                    ssc.specs_map['python'] = spec
            ssc.solution_precs = tuple(prec for prec in ssc.solution_precs
                                       if prec not in inconsistent_precs)
        return ssc

    def _package_has_updates(self, ssc, spec, installed_pool):
        installed_prec = installed_pool.get(spec.name)
        has_update = False

        if installed_prec:
            installed_prec = installed_prec[0]
            for prec in ssc.r.groups.get(spec.name, []):
                if prec.version > installed_prec.version:
                    has_update = True
                    break
                elif (prec.version == installed_prec.version and
                      prec.build_number > installed_prec.build_number):
                    has_update = True
                    break
        # let conda determine the latest version by just adding a name spec
        return (MatchSpec(spec.name, version=prec.version, build_number=prec.build_number)
                if has_update else spec)

    def _should_freeze(self, ssc, target_prec, conflict_specs, explicit_pool, installed_pool):
        # never, ever freeze anything if we have no history.
        if not ssc.specs_from_history_map:
            return False
        # never freeze if not in FREEZE_INSTALLED mode
        if ssc.update_modifier != UpdateModifier.FREEZE_INSTALLED:
            return False

        # if all package specs have overlapping package choices (satisfiable in at least one way)
        pkg_name = target_prec.name
        no_conflict = (pkg_name not in conflict_specs and
                       (pkg_name not in explicit_pool or
                        target_prec in explicit_pool[pkg_name]))

        return no_conflict

    def _add_specs(self, ssc):
        # For the remaining specs in specs_map, add target to each spec. `target` is a reference
        # to the package currently existing in the environment. Setting target instructs the
        # solver to not disturb that package if it's not necessary.
        # If the spec.name is being modified by inclusion in specs_to_add, we don't set `target`,
        # since we *want* the solver to modify/update that package.
        #
        # TLDR: when working with MatchSpec objects,
        #  - to minimize the version change, set MatchSpec(name=name, target=prec.dist_str())
        #  - to freeze the package, set all the components of MatchSpec individually

        installed_pool = groupby(lambda x: x.name, ssc.prefix_data.iter_records())

        # the only things we should consider freezing are things that don't conflict with the new
        #    specs being added.
        explicit_pool = ssc.r._get_package_pool(self.specs_to_add)

        conflict_specs = ssc.r.get_conflicting_specs(tuple(concatv(
            (_.to_match_spec() for _ in ssc.prefix_data.iter_records()))), self.specs_to_add
        ) or tuple()
        conflict_specs = set(_.name for _ in conflict_specs)

        for pkg_name, spec in iteritems(ssc.specs_map):
            matches_for_spec = tuple(prec for prec in ssc.solution_precs if spec.match(prec))
            if matches_for_spec:
                if len(matches_for_spec) != 1:
                    raise CondaError(dals("""
                    Conda encountered an error with your environment.  Please report an issue
                    at https://github.com/conda/conda/issues.  In your report, please include
                    the output of 'conda info' and 'conda list' for the active environment, along
                    with the command you invoked that resulted in this error.
                      pkg_name: %s
                      spec: %s
                      matches_for_spec: %s
                    """) % (pkg_name, spec,
                            dashlist((text_type(s) for s in matches_for_spec), indent=4)))
                target_prec = matches_for_spec[0]
                if target_prec.is_unmanageable:
                    ssc.specs_map[pkg_name] = target_prec.to_match_spec()
                elif MatchSpec(pkg_name) in context.aggressive_update_packages:
                    ssc.specs_map[pkg_name] = MatchSpec(pkg_name)
                elif self._should_freeze(ssc, target_prec, conflict_specs, explicit_pool,
                                         installed_pool):
                    ssc.specs_map[pkg_name] = target_prec.to_match_spec()
                elif pkg_name in ssc.specs_from_history_map:
                    ssc.specs_map[pkg_name] = MatchSpec(
                        ssc.specs_from_history_map[pkg_name],
                        target=target_prec.dist_str())
                else:
                    ssc.specs_map[pkg_name] = MatchSpec(pkg_name, target=target_prec.dist_str())

        pin_overrides = set()
        for s in ssc.pinned_specs:
            if s.name in explicit_pool:
                if s.name not in self.specs_to_add_names and not ssc.ignore_pinned:
                    ssc.specs_map[s.name] = MatchSpec(s, optional=False)
                elif explicit_pool[s.name] & ssc.r._get_package_pool([s]).get(s.name, set()):
                    ssc.specs_map[s.name] = MatchSpec(s, optional=False)
                    pin_overrides.add(s.name)
                else:
                    log.warn("pinned spec %s conflicts with explicit specs.  "
                             "Overriding pinned spec.", s)

        # we want to freeze any packages in the env that are not conflicts, so that the
        #     solve goes faster.  This is kind of like an iterative solve, except rather
        #     than just providing a starting place, we are preventing some solutions.
        #     A true iterative solve would probably be better in terms of reaching the
        #     optimal output all the time.  It would probably also get rid of the need
        #     to retry with an unfrozen (UPDATE_SPECS) solve.
        if ssc.update_modifier == UpdateModifier.FREEZE_INSTALLED:
            precs = [_ for _ in ssc.prefix_data.iter_records() if _.name not in ssc.specs_map]
            for prec in precs:
                if prec.name not in conflict_specs:
                    ssc.specs_map[prec.name] = prec.to_match_spec()
                else:
                    ssc.specs_map[prec.name] = MatchSpec(
                        prec.name, target=prec.to_match_spec(), optional=True)
        log.debug("specs_map with targets: %s", ssc.specs_map)

        # If we're in UPDATE_ALL mode, we need to drop all the constraints attached to specs,
        # so they can all float and the solver can find the most up-to-date solution. In the case
        # of UPDATE_ALL, `specs_map` wasn't initialized with packages from the current environment,
        # but *only* historically-requested specs.  This lets UPDATE_ALL drop dependencies if
        # they're no longer needed, and their presence would otherwise prevent the updated solution
        # the user most likely wants.
        if ssc.update_modifier == UpdateModifier.UPDATE_ALL:
            # history is preferable because it has explicitly installed stuff in it.
            #   that simplifies our solution.
            if ssc.specs_from_history_map:
                ssc.specs_map = odict((spec, MatchSpec(spec))
                                      if MatchSpec(spec).name not in
                                      (_.name for _ in ssc.pinned_specs)
                                      else (MatchSpec(spec).name,
                                            ssc.specs_map[MatchSpec(spec).name])
                                      for spec in ssc.specs_from_history_map
                                      )
                for prec in ssc.prefix_data.iter_records():
                    # treat pip-installed stuff as explicitly installed, too.
                    if prec.subdir == 'pypi':
                        ssc.specs_map.update({prec.name: MatchSpec(prec.name)})
            else:
                ssc.specs_map = odict((prec.name, MatchSpec(prec.name))
                                      if prec.name not in (_.name for _ in ssc.pinned_specs) else
                                      (prec.name, ssc.specs_map[prec.name])
                                      for prec in ssc.prefix_data.iter_records()
                                      )

        # ensure that our self.specs_to_add are not being held back by packages in the env.
        #    This factors in pins and also ignores specs from the history.  It is unfreezing only
        #    for the indirect specs that otherwise conflict with update of the immediate request
        elif ssc.update_modifier == UpdateModifier.UPDATE_SPECS:
            skip = lambda x: ((x.name not in pin_overrides and
                               any(x.name == _.name for _ in ssc.pinned_specs) and
                               not ssc.ignore_pinned) or
                              x.name in ssc.specs_from_history_map)

            specs_to_add = tuple(self._package_has_updates(ssc, _, installed_pool)
                                 for _ in self.specs_to_add if not skip(_))
            # the index is sorted, so the first record here gives us what we want.
            conflicts = ssc.r.get_conflicting_specs(tuple(MatchSpec(_)
                                                          for _ in ssc.specs_map.values()),
                                                    specs_to_add)
            for conflict in conflicts or ():
                # neuter the spec due to a conflict
                if (conflict.name in ssc.specs_map and (
                        # add optional because any pinned specs will include it
                        MatchSpec(conflict, optional=True) not in ssc.pinned_specs or
                        ssc.ignore_pinned) and
                        conflict.name not in ssc.specs_from_history_map):
                    ssc.specs_map[conflict.name] = MatchSpec(conflict.name)

        # As a business rule, we never want to update python beyond the current minor version,
        # unless that's requested explicitly by the user (which we actively discourage).
        py_in_prefix = any(_.name == 'python' for _ in ssc.solution_precs)
        py_requested_explicitly = any(s.name == 'python' for s in self.specs_to_add)
        if py_in_prefix and not py_requested_explicitly:
            python_prefix_rec = ssc.prefix_data.get('python')
            freeze_installed = ssc.update_modifier == UpdateModifier.FREEZE_INSTALLED
            if 'python' not in conflict_specs and freeze_installed:
                ssc.specs_map['python'] = python_prefix_rec.to_match_spec()
            else:
                # will our prefix record conflict with any explict spec?  If so, don't add
                #     anything here - let python float when it hasn't been explicitly specified
                python_spec = ssc.specs_map.get('python', MatchSpec('python'))
                if not python_spec.get('version'):
                    pinned_version = get_major_minor_version(python_prefix_rec.version) + '.*'
                    python_spec = MatchSpec(python_spec, version=pinned_version)

                spec_set = (python_spec, ) + tuple(self.specs_to_add)
                if ssc.r.get_conflicting_specs(spec_set, self.specs_to_add):
                    if self._command != 'install' or (
                            self._repodata_fn == REPODATA_FN and
                            (not ssc.should_retry_solve or not freeze_installed)):
                        # raises a hopefully helpful error message
                        ssc.r.find_conflicts(spec_set)
                    else:
                        raise UnsatisfiableError({})
                ssc.specs_map['python'] = python_spec

        # For the aggressive_update_packages configuration parameter, we strip any target
        # that's been set.
        if not context.offline:
            for spec in context.aggressive_update_packages:
                if spec.name in ssc.specs_map:
                    ssc.specs_map[spec.name] = spec

        # add in explicitly requested specs from specs_to_add
        # this overrides any name-matching spec already in the spec map
        ssc.specs_map.update((s.name, s) for s in self.specs_to_add if s.name not in pin_overrides)

        # As a business rule, we never want to downgrade conda below the current version,
        # unless that's requested explicitly by the user (which we actively discourage).
        if 'conda' in ssc.specs_map and paths_equal(self.prefix, context.conda_prefix):
            conda_prefix_rec = ssc.prefix_data.get('conda')
            if conda_prefix_rec:
                version_req = ">=%s" % conda_prefix_rec.version
                conda_requested_explicitly = any(s.name == 'conda' for s in self.specs_to_add)
                conda_spec = ssc.specs_map['conda']
                conda_in_specs_to_add_version = ssc.specs_map.get('conda', {}).get('version')
                if not conda_in_specs_to_add_version:
                    conda_spec = MatchSpec(conda_spec, version=version_req)
                if context.auto_update_conda and not conda_requested_explicitly:
                    conda_spec = MatchSpec('conda', version=version_req, target=None)
                ssc.specs_map['conda'] = conda_spec

        return ssc

    @time_recorder(module_name=__name__)
    def _run_sat(self, ssc):
        final_environment_specs = IndexedSet(concatv(
            itervalues(ssc.specs_map),
            ssc.track_features_specs,
            # pinned specs removed here - added to specs_map in _add_specs instead
        ))

        absent_specs = [s for s in ssc.specs_map.values() if not ssc.r.find_matches(s)]
        if absent_specs:
            raise PackagesNotFoundError(absent_specs)

        # We've previously checked `solution` for consistency (which at that point was the
        # pre-solve state of the environment). Now we check our compiled set of
        # `final_environment_specs` for the possibility of a solution.  If there are conflicts,
        # we can often avoid them by neutering specs that have a target (e.g. removing version
        # constraint) and also making them optional. The result here will be less cases of
        # `UnsatisfiableError` handed to users, at the cost of more packages being modified
        # or removed from the environment.
        #
        # get_conflicting_specs() returns a "minimal unsatisfiable subset" which
        # may not be the only unsatisfiable subset. We may have to call get_conflicting_specs()
        # several times, each time making modifications to loosen constraints.

        conflicting_specs = set(ssc.r.get_conflicting_specs(tuple(final_environment_specs),
                                                            self.specs_to_add) or [])
        while conflicting_specs:
            specs_modified = False
            if log.isEnabledFor(DEBUG):
                log.debug("conflicting specs: %s", dashlist(
                    s.target if s.target else s for s in conflicting_specs))

            # Are all conflicting specs in specs_map? If not, that means they're in
            # track_features_specs or pinned_specs, which we should raise an error on.
            specs_map_set = set(itervalues(ssc.specs_map))
            grouped_specs = groupby(lambda s: s in specs_map_set, conflicting_specs)
            # force optional to true. This is what it is originally in
            # pinned_specs, but we override that in _add_specs to make it
            # non-optional when there's a name match in the explicit package
            # pool
            conflicting_pinned_specs = groupby(lambda s: MatchSpec(s, optional=True)
                                               in ssc.pinned_specs, conflicting_specs)

            if conflicting_pinned_specs.get(True):
                in_specs_map = grouped_specs.get(True, ())
                pinned_conflicts = conflicting_pinned_specs.get(True, ())
                in_specs_map_or_specs_to_add = ((set(in_specs_map) | set(self.specs_to_add))
                                                - set(pinned_conflicts))

                raise SpecsConfigurationConflictError(
                    sorted(s.__str__() for s in in_specs_map_or_specs_to_add),
                    sorted(s.__str__() for s in {s for s in pinned_conflicts}),
                    self.prefix
                )
            for spec in conflicting_specs:
                if spec.target and not spec.optional:
                    specs_modified = True
                    final_environment_specs.remove(spec)
                    if spec.get('version'):
                        neutered_spec = MatchSpec(spec.name, version=spec.version)
                    else:
                        neutered_spec = MatchSpec(spec.name)
                    final_environment_specs.add(neutered_spec)
                    ssc.specs_map[spec.name] = neutered_spec
            if specs_modified:
                conflicting_specs = set(ssc.r.get_conflicting_specs(
                    tuple(final_environment_specs), self.specs_to_add))
            else:
                # Let r.solve() use r.find_conflicts() to report conflict chains.
                break

        # Finally! We get to call SAT.
        if log.isEnabledFor(DEBUG):
            log.debug("final specs to add: %s",
                      dashlist(sorted(text_type(s) for s in final_environment_specs)))

        # this will raise for unsatisfiable stuff.  We can
        if not conflicting_specs or context.unsatisfiable_hints:
            ssc.solution_precs = ssc.r.solve(tuple(final_environment_specs),
                                             specs_to_add=self.specs_to_add,
                                             history_specs=ssc.specs_from_history_map,
                                             should_retry_solve=ssc.should_retry_solve
                                             )
        else:
            # shortcut to raise an unsat error without needing another solve step when
            # unsatisfiable_hints is off
            raise UnsatisfiableError({})

        self.neutered_specs = tuple(v for k, v in ssc.specs_map.items() if
                                    k in ssc.specs_from_history_map and
                                    v.strictness < ssc.specs_from_history_map[k].strictness)

        # add back inconsistent packages to solution
        if ssc.add_back_map:
            for name, (prec, spec) in iteritems(ssc.add_back_map):
                # spec here will only be set if the conflicting prec was in the original specs_map
                #    if it isn't there, then we restore the conflict.  If it is there, though,
                #    we keep the new, consistent solution
                if not spec:
                    # filter out solution precs and reinsert the conflict.  Any resolution
                    #    of the conflict should be explicit (i.e. it must be in ssc.specs_map)
                    ssc.solution_precs = [_ for _ in ssc.solution_precs if _.name != name]
                    ssc.solution_precs.append(prec)
                    final_environment_specs.add(spec)

        ssc.final_environment_specs = final_environment_specs
        return ssc

    def _post_sat_handling(self, ssc):
        # Special case handling for various DepsModifier flags.
        final_environment_specs = ssc.final_environment_specs
        if ssc.deps_modifier == DepsModifier.NO_DEPS:
            # In the NO_DEPS case, we need to start with the original list of packages in the
            # environment, and then only modify packages that match specs_to_add or
            # specs_to_remove.
            #
            # Help information notes that use of NO_DEPS is expected to lead to broken
            # environments.
            _no_deps_solution = IndexedSet(ssc.prefix_data.iter_records())
            only_remove_these = set(prec
                                    for spec in self.specs_to_remove
                                    for prec in _no_deps_solution
                                    if spec.match(prec))
            _no_deps_solution -= only_remove_these

            only_add_these = set(prec
                                 for spec in self.specs_to_add
                                 for prec in ssc.solution_precs
                                 if spec.match(prec))
            remove_before_adding_back = set(prec.name for prec in only_add_these)
            _no_deps_solution = IndexedSet(prec for prec in _no_deps_solution
                                           if prec.name not in remove_before_adding_back)
            _no_deps_solution |= only_add_these
            ssc.solution_precs = _no_deps_solution

            # TODO: check if solution is satisfiable, and emit warning if it's not

        elif (ssc.deps_modifier == DepsModifier.ONLY_DEPS
                and ssc.update_modifier != UpdateModifier.UPDATE_DEPS):
            # Using a special instance of PrefixGraph to remove youngest child nodes that match
            # the original specs_to_add.  It's important to remove only the *youngest* child nodes,
            # because a typical use might be `conda install --only-deps python=2 flask`, and in
            # that case we'd want to keep python.
            #
            # What are we supposed to do if flask was already in the environment?
            # We can't be removing stuff here that's already in the environment.
            #
            # What should be recorded for the user-requested specs in this case? Probably all
            # direct dependencies of flask.
            graph = PrefixGraph(ssc.solution_precs, self.specs_to_add)
            removed_nodes = graph.remove_youngest_descendant_nodes_with_specs()
            self.specs_to_add = set(self.specs_to_add)
            for prec in removed_nodes:
                for dep in prec.depends:
                    dep = MatchSpec(dep)
                    if dep.name not in ssc.specs_map:
                        self.specs_to_add.add(dep)
            # unfreeze
            self.specs_to_add = frozenset(self.specs_to_add)

            # Add back packages that are already in the prefix.
            specs_to_remove_names = set(spec.name for spec in self.specs_to_remove)
            add_back = tuple(ssc.prefix_data.get(node.name, None) for node in removed_nodes
                             if node.name not in specs_to_remove_names)
            ssc.solution_precs = tuple(
                PrefixGraph(concatv(graph.graph, filter(None, add_back))).graph
            )

            # TODO: check if solution is satisfiable, and emit warning if it's not

        elif ssc.update_modifier == UpdateModifier.UPDATE_DEPS:
            # Here we have to SAT solve again :(  It's only now that we know the dependency
            # chain of specs_to_add.
            #
            # UPDATE_DEPS is effectively making each spec in the dependency chain a user-requested
            # spec.  We don't modify pinned_specs, track_features_specs, or specs_to_add.  For
            # all other specs, we drop all information but name, drop target, and add them to
            # the specs_to_add that gets recorded in the history file.
            #
            # It's like UPDATE_ALL, but only for certain dependency chains.
            graph = PrefixGraph(ssc.solution_precs)
            update_names = set()
            for spec in self.specs_to_add:
                node = graph.get_node_by_name(spec.name)
                update_names.update(ancest_rec.name for ancest_rec in graph.all_ancestors(node))
            specs_map = {name: MatchSpec(name) for name in update_names}

            # Remove pinned_specs and any python spec (due to major-minor pinning business rule).
            # Add in the original specs_to_add on top.
            for spec in ssc.pinned_specs:
                specs_map.pop(spec.name, None)
            if "python" in specs_map:
                python_rec = ssc.prefix_data.get("python")
                py_ver = ".".join(python_rec.version.split(".")[:2]) + ".*"
                specs_map["python"] = MatchSpec(name="python", version=py_ver)
            specs_map.update({spec.name: spec for spec in self.specs_to_add})
            new_specs_to_add = tuple(itervalues(specs_map))

            # It feels wrong/unsafe to modify this instance, but I guess let's go with it for now.
            self.specs_to_add = new_specs_to_add
            ssc.solution_precs = self.solve_final_state(
                update_modifier=UpdateModifier.UPDATE_SPECS,
                deps_modifier=ssc.deps_modifier,
                prune=ssc.prune,
                ignore_pinned=ssc.ignore_pinned,
                force_remove=ssc.force_remove
            )
            ssc.prune = False

        if ssc.prune:
            graph = PrefixGraph(ssc.solution_precs, final_environment_specs)
            graph.prune()
            ssc.solution_precs = tuple(graph.graph)

        return ssc

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
                SubdirData.query_all(conda_newer_spec, self.channels, self.subdirs,
                                     repodata_fn=self._repodata_fn),
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
            _supplement_index_with_system(self._index)
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
                                              self.subdirs, prepared_specs, self._repodata_fn)
            _supplement_index_with_system(reduced_index)

            self._prepared_specs = prepared_specs
            self._index = reduced_index
            self._r = Resolve(reduced_index, channels=self.channels)

        self._prepared = True
        return self._index, self._r


class LibSolvSolver(Solver):
    """
    This alternative Solver logic wraps ``libsolv`` through their Python bindings.

    We mainly replace ``Solver.solve_final_state``, quite high in the abstraction
    tree, which means that ``conda.resolve`` and ``conda.common.logic`` are no longer
    used here. All those bits are replaced by the logic implemented in ``libsolv`` itself.

    This means that ``libsolv`` governs processes like:

    - Building the SAT clauses
    - Pruning the repodata (?) - JRG: Not sure if this happens internally or at all.
    - Prioritizing different aspects of the solver (version, build strings, track_features...)
    """
    _uses_ssc = False

    def solve_final_state(self, update_modifier=NULL, deps_modifier=NULL, prune=NULL,
                          ignore_pinned=NULL, force_remove=NULL, force_reinstall=NULL,
                          should_retry_solve=False):
        # Logic heavily based on Mamba's implementation (solver parts):
        # https://github.com/mamba-org/mamba/blob/fe4ecc5061a49c5b400fa7e7390b679e983e8456/mamba/mamba.py#L289

        if not context.json and not context.quiet:
            print("------ USING EXPERIMENTAL MAMBA INTEGRATIONS ------")

        # 0. Identify strategies
        kwargs = self._merge_signature_flags_with_context(
            update_modifier=update_modifier,
            deps_modifier=deps_modifier,
            prune=prune,
            ignore_pinned=ignore_pinned,
            force_remove=force_remove,
            force_reinstall=force_reinstall,
            should_retry_solve=should_retry_solve
        )

        # Tasks that do not require a solver can be tackled right away
        # This returns either None (did nothing) or a final state
        none_or_final_state = self._early_exit_tasks(
            update_modifier=kwargs["update_modifier"],
            force_remove=kwargs["force_remove"],
        )
        if none_or_final_state is not None:
            return none_or_final_state

        # These tasks DO need a solver
        # 1. Populate repos with installed packages
        state = self._setup_state()

        # This might be too many attempts in large environments
        # We are technically allowing as many conflicts as packages
        # Mamba will only report one problem at a time for now, so
        # this is a limitation
        n_installed_pkgs = len(state["installed_pkgs"])
        attempts = n_installed_pkgs
        while attempts:
            attempts -=1
            log.debug(
                "Attempt number %s. Current conflicts (including learnt ones): %s",
                n_installed_pkgs-attempts,
                state['conflicting'],
            )
            result = self._solve_attempt(state, kwargs)
            if result is not None:
                return result

        # Last attempt, we report everything installed as a conflict just in case
        log.debug("Last attempt: reporting all installed as conflicts:")
        state["conflicting"].update(
            {pkg.name: pkg.to_match_spec() for pkg in state["conda_prefix_data"].iter_records()
             if not pkg.is_unmanageable}
        )
        result = self._solve_attempt(state, kwargs)
        if result is not None:
            return result

        # If we didn't return already, raise last known issue.
        problems = state["solver"].problems_to_str()
        log.debug("We didn't find a solution. Reporting problems: %s", problems)
        raise self.raise_for_problems(problems)

    def _solve_attempt(self, state, kwargs):
        # 2. Create solver and needed flags, tasks and jobs
        self._configure_solver(
            state,
            update_modifier=kwargs["update_modifier"],
            deps_modifier=kwargs["deps_modifier"],
            ignore_pinned=kwargs["ignore_pinned"],
            force_remove=kwargs["force_remove"],
            force_reinstall=kwargs["force_reinstall"],
            prune=kwargs["prune"],
        )
        # 3. Run the SAT solver
        success = self._run_solver(state)
        if not success:
            # conflicts were reported, try again
            # an exception will be raised from _run_solver
            # if we end up in a conflict loop
            log.debug("Failed attempt!")
            return
        # 4. Export back to conda
        self._export_final_state(state)
        # 5. Refine solutions depending on the value of some modifier flags
        return self._post_solve_tasks(
            state,
            update_modifier=kwargs["update_modifier"],
            deps_modifier=kwargs["deps_modifier"],
            ignore_pinned=kwargs["ignore_pinned"],
            force_remove=kwargs["force_remove"],
            force_reinstall=kwargs["force_reinstall"],
            prune=kwargs["prune"],
        )


    def _merge_signature_flags_with_context(
            self,
            update_modifier=NULL,
            deps_modifier=NULL,
            ignore_pinned=NULL,
            force_remove=NULL,
            force_reinstall=NULL,
            prune=NULL,
            should_retry_solve=False):
        """
        Context options can be overriden with the signature flags.

        We need this, at least, for some unit tests that change this behaviour through
        the function signature instead of the context / env vars.
        """
        # Sometimes a str is passed instead of the Enum item
        str_to_enum = {
            "NOT_SET": DepsModifier.NOT_SET,
            "NO_DEPS": DepsModifier.NO_DEPS,
            "ONLY_DEPS": DepsModifier.ONLY_DEPS,
            "SPECS_SATISFIED_SKIP_SOLVE": UpdateModifier.SPECS_SATISFIED_SKIP_SOLVE,
            "FREEZE_INSTALLED": UpdateModifier.FREEZE_INSTALLED,
            "UPDATE_DEPS": UpdateModifier.UPDATE_DEPS,
            "UPDATE_SPECS": UpdateModifier.UPDATE_SPECS,
            "UPDATE_ALL": UpdateModifier.UPDATE_ALL,
        }

        def context_if_null(name, value):
            return getattr(context, name) if value is NULL else str_to_enum.get(value, value)

        return {
            "update_modifier": context_if_null("update_modifier", update_modifier),
            "deps_modifier": context_if_null("deps_modifier", deps_modifier),
            "ignore_pinned": context_if_null("ignore_pinned", ignore_pinned),
            "force_remove": context_if_null("force_remove", force_remove),
            "force_reinstall": context_if_null("force_reinstall", force_reinstall),
            "prune": prune,
            # We don't use these flags in mamba
            # "should_retry_solve": should_retry_solve,
        }

    def _early_exit_tasks(self, update_modifier=NULL, force_remove=NULL):
        """
        This reimplements a chunk of code found in the Legacy implementation.

        See https://github.com/conda/conda/blob/9e9461760bbd71a17822/conda/core/solve.py#L239-L256
        """
        # force_remove is a special case where we return early
        if self.specs_to_remove and force_remove:
            if self.specs_to_add:
                # This is not reachable from the CLI, but it is from the Python API
                raise NotImplementedError("Cannot add and remove packages simultaneously.")
            pkg_records = PrefixData(self.prefix).iter_records()
            solution = tuple(pkg_record for pkg_record in pkg_records
                             if not any(spec.match(pkg_record) for spec in self.specs_to_remove))
            return IndexedSet(PrefixGraph(solution).graph)

        # Check if specs are satisfied by current environment. If they are, exit early.
        if (update_modifier == UpdateModifier.SPECS_SATISFIED_SKIP_SOLVE
                and not self.specs_to_remove):
            prefix_data = PrefixData(self.prefix)
            for spec in self.specs_to_add:
                if not next(prefix_data.query(spec), None):
                    break
            else:
                # All specs match a package in the current environment.
                # Return early, with a solution that should just be PrefixData().iter_records()
                return IndexedSet(PrefixGraph(prefix_data.iter_records()).graph)

    def _setup_state(self):
        from mamba.utils import load_channels, get_installed_jsonfile, init_api_context
        from mamba.mamba_api import Pool, Repo, PrefixData as MambaPrefixData

        init_api_context()

        pool = Pool()
        state = {}

        # TODO: Check if this update-related logic is needed here too
        # Maybe conda already handles that beforehand
        # https://github.com/mamba-org/mamba/blob/fe4ecc5061a49c5b400fa7/mamba/mamba.py#L426-L485

        # https://github.com/mamba-org/mamba/blob/89174c0dc06398c99589/src/core/prefix_data.cpp#L13
        # for the C++ implementation of PrefixData
        mamba_prefix_data = MambaPrefixData(self.prefix)
        mamba_prefix_data.load()
        installed_json_f, installed_pkgs = get_installed_jsonfile(self.prefix)
        repos = []
        installed = Repo(pool, "installed", installed_json_f.name, "")
        installed.set_installed()
        repos.append(installed)

        # This function will populate the pool/repos with
        # the current state of the given channels
        # Note load_channels has a `repodata_fn` arg we are NOT using
        # because `current_repodata.json` is not guaranteed to exist in
        # our current implementation; we bypass that and always use the
        # default value: repodata.json
        subdirs = self.subdirs
        if subdirs is NULL or not subdirs:
            subdirs = context.subdirs
        index = load_channels(pool, self._channel_urls(), repos,
                              prepend=False,
                              use_local=context.use_local,
                              platform=subdirs)

        state.update({
            "pool": pool,
            "mamba_prefix_data": mamba_prefix_data,
            "conda_prefix_data": PrefixData(self.prefix),
            "repos": repos,
            "index": index,
            "installed_pkgs": installed_pkgs,
            "history": History(self.prefix),
            "conflicting": TrackedDict(),
            "specs_map": TrackedDict(),
        })

        return state

    def _channel_urls(self):
        """
        TODO: This collection of workarounds should be, ideally,
        handled in libmamba:

        - Escape URLs
        - Handle `local` correctly
        """
        channels = []
        for channel in self._channels:
            if channel == "local":
                # This fixes test_activate_deactivate_modify_path_bash
                # TODO: This can be improved earlier in the call stack
                # Mamba should be able to handle this on its own too,
                # but it fails (at least in the CI docker image).
                subdir_url = Channel("local").urls()[0]
                channel = subdir_url.rstrip("/").rsplit("/", 1)[0]
            if isinstance(channel, Channel):
                channel = channel.base_url or channel.name
            channel = escape_channel_url(channel)
            channels.append(channel)
        return channels

    def _configure_solver(self,
                          state,
                          update_modifier=NULL,
                          deps_modifier=NULL,
                          ignore_pinned=NULL,
                          force_remove=NULL,
                          force_reinstall=NULL,
                          prune=NULL):
        if self.specs_to_remove:
            return self._configure_solver_for_remove(state)
        # ALl other operations are handled as an install operation
        # Namely:
        # - Explicit specs added by user in CLI / API
        # - conda update --all
        # - conda create -n empty
        # Take into account that early exit tasks (force remove, etc)
        # have been handled beforehand if needed
        return self._configure_solver_for_install(state,
                                                  update_modifier=update_modifier,
                                                  deps_modifier=deps_modifier,
                                                  ignore_pinned=ignore_pinned,
                                                  force_remove=force_remove,
                                                  force_reinstall=force_reinstall,
                                                  prune=prune)

    def _configure_solver_for_install(self,
                                      state,
                                      update_modifier=NULL,
                                      deps_modifier=NULL,
                                      ignore_pinned=NULL,
                                      force_remove=NULL,
                                      force_reinstall=NULL,
                                      prune=NULL):
        from mamba import mamba_api as api

        # Set different solver options
        solver_options = [(api.SOLVER_FLAG_ALLOW_DOWNGRADE, 1)]
        if context.channel_priority is ChannelPriority.STRICT:
            solver_options.append((api.SOLVER_FLAG_STRICT_REPO_PRIORITY, 1))
        state["solver"] = solver = api.Solver(state["pool"], solver_options)

        # Configure jobs
        state["specs_map"] = self._compute_specs_map(state,
                                                     update_modifier=update_modifier,
                                                     deps_modifier=deps_modifier,
                                                     ignore_pinned=ignore_pinned,
                                                     force_remove=force_remove,
                                                     force_reinstall=force_reinstall,
                                                     prune=prune)

        # Neuter conflicts if any (modifies specs_map in place)
        specs_map = self._neuter_conflicts(state, ignore_pinned=ignore_pinned)

        tasks = self._specs_map_to_tasks(state, specs_map)

        log.debug(
            "Invoking libsolv with tasks: %s",
            "\n".join([f"{task_str}: {', '.join(specs)}" for (task_str, _), specs in tasks.items()])
        )

        for (_, task_type), specs in tasks.items():
            solver.add_jobs(specs, task_type)

        return solver

    def _configure_solver_for_remove(self, state):
        # First check we are not trying to remove things that are not installed
        installed_names = set(rec.name for rec in state["conda_prefix_data"].iter_records())
        not_installed = set(s for s in self.specs_to_remove if s.name not in installed_names)
        if not_installed:
            raise PackagesNotFoundError(not_installed)

        from mamba import mamba_api as api

        solver_options = [
            (api.SOLVER_FLAG_ALLOW_DOWNGRADE, 1),
            (api.SOLVER_FLAG_ALLOW_UNINSTALL, 1)
        ]
        if context.channel_priority is ChannelPriority.STRICT:
            solver_options.append((api.SOLVER_FLAG_STRICT_REPO_PRIORITY, 1))
        solver = api.Solver(state["pool"], solver_options)

        # pkgs in aggresive_update_packages should be protected too (even if not
        # requested explicitly by the user)
        # see https://github.com/conda/conda/blob/9e9461760bb/tests/core/test_solve.py#L520-L521
        aggresive_updates = [p.conda_build_form() for p in context.aggressive_update_packages
                             if p.name in installed_names]
        solver.add_jobs(
            list(set(chain(self._history_specs(), aggresive_updates))),
            api.SOLVER_USERINSTALLED,
        )
        specs = [s.conda_build_form() for s in self.specs_to_remove]
        solver.add_jobs(specs, api.SOLVER_ERASE | api.SOLVER_CLEANDEPS)

        state["solver"] = solver
        return solver

    def _compute_specs_map(self,
                           state,
                           update_modifier=NULL,
                           deps_modifier=NULL,
                           ignore_pinned=NULL,
                           force_remove=NULL,
                           force_reinstall=NULL,
                           prune=NULL):
        """
        Reimplement the logic found in super()._collect_all_metadata()
        and super()._add_specs(), but simplified.
        """
        # Section 1: Expose the prefix state

        # This will be our `ssc.specs_map`; a dict of names->MatchSpec that
        # will contain the specs passed to the solver (eventually). Mamba
        # expects a MatchSpec.conda_build_form(), but internally we will use
        # the full object to handle things like optionality and targets.
        specs_map = TrackedDict()
        history = state["history"].get_requested_specs_map()
        installed = {p.name: p for p in state["conda_prefix_data"].iter_records()}
        pinned = {p.name: p for p in self._pinned_specs(state, ignore_pinned)}
        conflicting = state["conflicting"]

        # 1.1. Add everything found in history
        log.debug("Adding history pins")
        specs_map.update(history)
        # 1.2. Protect some critical packages from being removed accidentally
        for pkg_name in ('anaconda', 'conda', 'conda-build', 'python.app',
                         'console_shortcut', 'powershell_shortcut'):
            if pkg_name not in specs_map and state["conda_prefix_data"].get(pkg_name, None):
                specs_map[pkg_name] = MatchSpec(pkg_name)

        # 1.3. Add virtual packages so they are taken into account by the solver
        log.debug("Adding virtual packages")
        virtual_pkg_index = {}
        _supplement_index_with_system(virtual_pkg_index)
        for virtual_pkg in virtual_pkg_index.keys():
            if virtual_pkg.name not in specs_map:
                specs_map[virtual_pkg.name] = MatchSpec(virtual_pkg.name)

        # 1.4. Go through the installed packages and...
        log.debug("Relaxing some installed specs")
        for pkg_name, pkg_record in installed.items():
            name_spec = MatchSpec(pkg_name)
            if (    # 1.4.1. History is empty. Add everything (happens with update --all)
                    not history
                    # 1.4.2. Pkg is part of the aggresive update list
                    or name_spec in context.aggressive_update_packages
                    # 1.4.3. it was installed with pip/others; treat it as a historic package
                    or pkg_record.subdir == 'pypi'
                ):
                specs_map[pkg_name] = name_spec

        # Section 2 - Here we technically consider the packages that need to be removed
        # but we are handling that as a separate action right now - TODO?


        # Section 3 - Refine specs implicitly by the prefix state

        # 3.1. If the prefix already contain matching specs for what we have added so far,
        # constrain these whenever possible to reduce the amount of changes
        log.debug("Refining some installed packages...")
        for pkg_name, pkg_spec in specs_map.items():
            matches_for_spec = tuple(prec for prec in installed.values() if pkg_spec.match(prec))
            if not matches_for_spec:
                continue
            if len(matches_for_spec) > 1:
                raise CondaError(
                    "Your prefix contains more than one possible match for the requested spec!\n"
                    f"  pkg_name: {pkg_name}\n"
                    f"  spec: {pkg_spec}\n"
                    f"  matches_for_spec: {matches_for_spec}\n"
                    )
            spec_in_prefix = matches_for_spec[0]
            # 3.1.1: always update
            if MatchSpec(pkg_name) in context.aggressive_update_packages:
                log.debug("Relax due to aggressive_update_packages")
                specs_map[pkg_name] = MatchSpec(pkg_name)
            # 3.1.2: freeze
            elif spec_in_prefix.is_unmanageable:
                log.debug("Freeze because unmanageable")
                # TODO: This is not the complete _should_freeze logic
                specs_map[pkg_name] = spec_in_prefix.to_match_spec()
            elif not history:
                log.debug("Freeze because no history")
                # TODO: This is not the complete _should_freeze logic
                specs_map[pkg_name] = spec_in_prefix.to_match_spec()
            elif pkg_name not in conflicting:
                log.debug("Freeze because not conflicting")
                # TODO: This is not the complete _should_freeze logic
                specs_map[pkg_name] = spec_in_prefix.to_match_spec()
            # 3.1.3: soft-constrain via `target`
            elif pkg_name in history:
                log.debug("Soft-freezing because historic")
                specs_map[pkg_name] = MatchSpec(history[pkg_name], target=spec_in_prefix.dist_str())
            else:
                log.debug("Soft-freezing because it is requested and already installed as a 2nd order dependency")
                specs_map[pkg_name] = MatchSpec(pkg_name, target=spec_in_prefix.dist_str())

        # Section 4: Check pinned packages
        from mamba.repoquery import depends as mamba_depends

        pin_overrides = set()
        explicit_pool = set()
        for spec in self.specs_to_add:
            result = mamba_depends(spec.dist_str(), pool=state["pool"])
            explicit_pool.update([p["name"] for p in result["result"]["pkgs"]])

        specs_to_add_map = {s.name: s for s in self.specs_to_add}
        for name, pin in pinned.items():
            is_installed = name in installed
            is_requested = name in specs_to_add_map
            if is_installed and not is_requested:
                log.debug("Pinning because installed and not requested")
                specs_map[name] = MatchSpec(pin, optional=False)
            elif is_requested:
                log.debug("Pin overrides user-requested spec")
                if specs_to_add_map[name].match(pin):
                    log.debug("pinned spec `%s` despite user-requested spec `%s` being present "
                              "because pin is stricter", pin, specs_to_add_map[name])
                    specs_map[name] = MatchSpec(pin, optional=False)
                    pin_overrides.add(name)
                else:
                    log.warn("pinned spec %s conflicts with explicit specs (%s).  "
                             "Overriding pinned spec.", pin, specs_to_add_map[name])
            elif name in explicit_pool:
                log.debug("Pinning because this spec is part of the explicit pool")
                specs_map[name] = MatchSpec(pin, optional=False)
            # TODO: Not sure what this does
            # elif installed[pin.name] & r._get_package_pool([pin]).get(pin.name, set()):
            #     specs_map[pin.name] = MatchSpec(pin, optional=False)
            #     pin_overrides.add(pin.name)

        # Section 5: freeze everything that is not currently in conflict
        if update_modifier == UpdateModifier.FREEZE_INSTALLED:
            for pkg_name, pkg_record in installed.items():
                if pkg_name not in conflicting:  # TODO
                    log.debug("Freezing because installed and not conflicting")
                    specs_map[pkg_name] = pkg_record.to_match_spec()
                elif not pkg_record.is_unmanageable:
                    log.debug("Unfreezing because conflicting...")
                    specs_map[pkg_name] = MatchSpec(
                        pkg_name, target=pkg_record.to_match_spec(), optional=True)
            # log.debug("specs_map with targets: %s", specs_map)

        # Section 6: Handle UPDATE_ALL
        elif update_modifier == UpdateModifier.UPDATE_ALL:
            new_specs_map = TrackedDict()
            if history:
                for spec in history:
                    matchspec = MatchSpec(spec)
                    if matchspec.name not in pinned:
                        log.debug("Update all: spec is in history but not pinnned")
                        new_specs_map[spec] = matchspec
                    else:
                        log.debug("Update all: spec is in history and pinnned")
                        new_specs_map[matchspec.name] = specs_map[matchspec.name]
                for pkg_name, pkg_record in installed.items():
                    # treat pip-installed stuff as explicitly installed, too.
                    if pkg_record.subdir == 'pypi':
                        log.debug("Update all: spec is pip-installed")
                        new_specs_map[pkg_name] = MatchSpec(pkg_name)
                    elif pkg_name not in new_specs_map:
                        log.debug("Update all: adding spec to list because it was installed")
                        new_specs_map[pkg_name] = MatchSpec(pkg_name)
            else:
                for pkg_name, pkg_record in installed.items():
                    if pkg_name not in pinned:
                        log.debug("Update all: spec is installed but not pinned")
                        new_specs_map[pkg_name] = MatchSpec(pkg_name)
                    else:
                        log.debug("Update all: spec is installed and pinned")
                        new_specs_map[pkg_name] = specs_map[pkg_name]
            # We overwrite the specs map so far!
            specs_map = new_specs_map

        # Section 6 - Handle UPDATE_SPECS  (note: this might be unimportant)
        # Unfreezes the indirect specs that otherwise conflict
        # with the update of the explicitly requested spec
        elif update_modifier == UpdateModifier.UPDATE_SPECS:
            from mamba.repoquery import search as mamba_search
            potential_conflicts = []
            for spec in self.specs_to_add:  # requested by the user
                in_pins = spec.name not in pin_overrides and spec.name in pinned
                in_history = spec.name in history
                if in_pins or in_history:  # skip these
                    continue
                has_update = False
                # Check if this spec has any available updates
                installed_record = installed.get(spec.name)

                if installed_record:
                    # Check the index for available updates
                    installed_version = VersionOrder(installed_record.version)
                    query = mamba_search(f"{spec.name} >={spec.version}", pool=state["pool"])
                    for pkg_record in query["result"]["pkgs"]:
                        if pkg_record["channel"] == "installed":
                            continue
                        found_version = VersionOrder(pkg_record["version"])
                        greater_version =  found_version > installed_version
                        greater_build = (found_version == installed_version and
                                         pkg_record["build_number"] > installed_record.build_number)
                        if greater_version or greater_build:
                            has_update =  True
                            break
                if has_update:
                    potential_conflicts.append(
                        MatchSpec(
                            spec.name,
                            version=pkg_record["version"],
                            build_number=pkg_record["build_number"],
                        )
                    )
                else:
                    potential_conflicts.append(spec)

            # TODO: What shall we do with `potential_conflicts`??

            log.debug("Relax constrains because it caused a conflict")
            for pkg in conflicting.values():
                # neuter the spec due to a conflict
                if pkg.name in specs_map and pkg.name not in pinned:
                    specs_map[pkg.name] = history.get(pkg.name, MatchSpec(pkg.name))

        # Section 7 - Pin Python
        log.debug("Adjust python pinning")
        py_requested_explicitly = any(s.name == "python" for s in self.specs_to_add)
        installed_python = installed.get("python")
        if installed_python and not py_requested_explicitly:
            freeze_installed = update_modifier == UpdateModifier.FREEZE_INSTALLED
            if "python" not in conflicting and freeze_installed:
                specs_map["python"] = installed_python.to_match_spec()
            else:
                # will our prefix record conflict with any explict spec?  If so, don't add
                #     anything here - let python float when it hasn't been explicitly specified
                python_spec = specs_map.get("python", MatchSpec("python"))
                if not python_spec.get('version'):
                    pinned_version = get_major_minor_version(installed_python.version) + '.*'
                    python_spec = MatchSpec(python_spec, version=pinned_version)
                specs_map["python"] = python_spec

        # Section 8 - Make sure aggressive updates are not constrained now
        if not context.offline:
            log.debug("Make sure aggressive updates did not end up pinned again")
            specs_map.update({s.name: s for s in context.aggressive_update_packages
                              if s.name in specs_map})

        # Section 9 - FINALLY we add the explicitly requested specs
        log.debug("Add user specs")
        specs_map.update({s.name: s for s in self.specs_to_add if s.name not in pin_overrides})

        # Section 10 - Make sure `conda` is not downgraded
        if "conda" in specs_map and paths_equal(self.prefix, context.conda_prefix):
            conda_prefix_rec = state["conda_prefix_data"].get("conda")
            if conda_prefix_rec:
                version_req = f">={conda_prefix_rec.version}"
                conda_requested_explicitly = any(s.name == "conda" for s in self.specs_to_add)
                conda_spec = specs_map["conda"]
                conda_in_specs_to_add_version = specs_map.get("conda", {}).get("version")
                if not conda_in_specs_to_add_version:
                    conda_spec = MatchSpec(conda_spec, version=version_req)
                if context.auto_update_conda and not conda_requested_explicitly:
                    conda_spec = MatchSpec("conda", version=version_req, target=None)
                log.debug("Adjust conda spec")
                specs_map["conda"] = conda_spec

        # Section 11 - Mamba/Conda behaviour difference workaround
        # If a spec is installed and has been requested with no constrains,
        # we assume the user wants an update, so we add >{current_version}, but only if no
        # flags have been passed -- otherwise interactions between implicit updates create unneeded
        # conflicts
        log.debug("Make sure specs are upgraded if requested explicitly and not in conflict")
        if (deps_modifier != DepsModifier.ONLY_DEPS and update_modifier == UpdateModifier.UPDATE_SPECS
            and self._command != "recursive_call_for_update_deps"):
            for spec in self.specs_to_add:
                if (spec.name in specs_map and specs_map[spec.name].strictness == 1
                    and spec.name in installed):  # and spec.name not in conflicting):
                    if spec.name == "python" and "python" in conflicting:
                        continue  # do not modify python if it was conflicting
                    specs_map[spec.name] = MatchSpec(name=spec.name, version=f">{installed[spec.name].version}")
        # if (installed_python and py_requested_explicitly
        #         and not specs_map["python"].version and "python" not in conflicting):
        #     specs_map["python"] = MatchSpec(name="python", version=f"!={installed_python.version}")

        return specs_map

    def _neuter_conflicts(self, state, ignore_pinned=False):
        conflicting_specs = state["conflicting"].values()
        specs_map = state["specs_map"]

        # Are all conflicting specs in specs_map? If not, that means they're in
        # track_features_specs or pinned_specs, which we should raise an error on.
        # JRG: This won't probably work because Mamba reports conflicts one at a time...
        specs_set = set(specs_map.values())
        grouped_specs = groupby(lambda s: s in specs_set, conflicting_specs)
        # force optional to true. This is what it is originally in
        # pinned_specs, but we override that in _compute_specs_map to make it
        # non-optional when there's a name match in the explicit package pool
        conflicting_pinned_specs = groupby(lambda s: MatchSpec(s, optional=True)
                                           in self._pinned_specs(state, ignore_pinned), conflicting_specs)

        if conflicting_pinned_specs.get(True):
            in_specs_map = grouped_specs.get(True, ())
            pinned_conflicts = conflicting_pinned_specs.get(True, ())
            in_specs_map_or_specs_to_add = ((set(in_specs_map) | set(self.specs_to_add))
                                            - set(pinned_conflicts))

            raise SpecsConfigurationConflictError(
                sorted(s.__str__() for s in in_specs_map_or_specs_to_add),
                sorted(s.__str__() for s in {s for s in pinned_conflicts}),
                self.prefix
            )

        log.debug("Neutering specs...")
        for spec in conflicting_specs:
            # if spec.name == "python":
            #     continue
            if spec.target and not spec.optional:
                if spec.get('version'):
                    neutered_spec = MatchSpec(spec.name, version=spec.version)
                else:
                    neutered_spec = MatchSpec(spec.name)
                specs_map[spec.name] = neutered_spec
            if spec.name not in specs_map:  # side-effect conflict; add to specs with less restrains
                specs_map[spec.name] = MatchSpec(name=spec.name, target=spec.dist_str())

        return specs_map

    def _specs_map_to_tasks(self, state, specs_map):
        from mamba import mamba_api as api
        tasks = defaultdict(list)
        history = state["history"].get_requested_specs_map()
        specs_map = specs_map.copy()
        installed = {rec.name: rec for rec in state["conda_prefix_data"].iter_records()}

        # Section 11 - deprioritize installed stuff that wasn't requested
        # These packages might not be available in future Python versions, but we don't
        # want them to block a requested Python update
        log.debug("Deprioritizing conflicts:")
        protect_these = set(s.name for s in self.specs_to_add)  # explicitly requested
        protect_these.update(("python", "conda"))
        protect_these.update([pkg_name for pkg_name, pkg_record in installed.items() if pkg_record.is_unmanageable])
        for conflict in state["conflicting"]:
            if conflict in specs_map and conflict not in protect_these:
                spec = specs_map.pop(conflict)
                log.debug("  MOV: %s from specs_map to SOLVER_DISFAVOR", conflict)
                tasks[("api.SOLVER_DISFAVOR", api.SOLVER_DISFAVOR)].append(spec.conda_build_form())
                tasks[("api.SOLVER_ALLOWUNINSTALL", api.SOLVER_ALLOWUNINSTALL)].append(spec.conda_build_form())

        # Wrap up and create tasks for the solver
        for name, spec in specs_map.items():
            if name.startswith("__"):
                continue
            if name in installed:
                if name == "python":
                    key = "api.SOLVER_UPDATE | api.SOLVER_ESSENTIAL", api.SOLVER_UPDATE | api.SOLVER_ESSENTIAL
                else:
                    key = "api.SOLVER_UPDATE", api.SOLVER_UPDATE

                history_spec = history.get(name)
                if history_spec:
                    installed_rec = installed[name]
                    ms = MatchSpec(name=installed_rec.name, version=installed_rec.version, build=installed_rec.build)
                    tasks[("api.SOLVER_USERINSTALLED", api.SOLVER_USERINSTALLED)].append(ms.conda_build_form())
            else:
                key = "api.SOLVER_INSTALL", api.SOLVER_INSTALL
            tasks[key].append(spec.conda_build_form())


        return tasks

    def _pinned_specs(self, state, ignore_pinned=False):
        if ignore_pinned:
            return ()
        pinned_specs = get_pinned_specs(self.prefix)
        pin_these_specs = []
        for pin in pinned_specs:
            installed_pins = state["conda_prefix_data"].query(pin.name) or ()
            for installed in installed_pins:
                if not pin.match(installed):
                    raise SpecsConfigurationConflictError([pin], [installed], self.prefix)
            pin_these_specs.append(pin)
        return tuple(pin_these_specs)

    def _history_specs(self):
        return [s.conda_build_form()
                for s in History(self.prefix).get_requested_specs_map().values()]

    def _run_solver(self, state):
        solver = state["solver"]
        solved = solver.solve()
        if solved:
            # Clear potential conflicts we used to have
            state["conflicting"].clear()
        else:
            # Report problems if any
            # it would be better if we could pass a graph object or something
            # that the exception can actually format if needed
            problems = solver.problems_to_str()
            state["conflicting"] = self._parse_problems(problems, state["conflicting"].copy())

        return solved

    def _export_final_state(self, state):
        from mamba import mamba_api as api
        from mamba.utils import to_package_record_from_subjson

        solver = state["solver"]
        index = state["index"]
        installed_pkgs = state["installed_pkgs"]

        transaction = api.Transaction(
            solver,
            api.MultiPackageCache(context.pkgs_dirs),
            PackageCacheData.first_writable().pkgs_dir,
        )
        (names_to_add, names_to_remove), to_link, to_unlink = transaction.to_conda()

        # What follows below is taken from mamba.utils.to_txn with some patches
        conda_prefix_data = PrefixData(self.prefix)
        final_precs = IndexedSet(conda_prefix_data.iter_records())

        lookup_dict = {}
        for _, entry in index:
            lookup_dict[
                entry["channel"].platform_url(entry["platform"], with_credentials=False)
            ] = entry

        for _, pkg in to_unlink:
            for i_rec in installed_pkgs:
                # Do not try to unlink virtual pkgs, virtual eggs, etc
                if not i_rec.is_unmanageable and i_rec.fn == pkg:
                    final_precs.remove(i_rec)
                    break
            else:
                log.warn("Tried to unlink %s but it is not installed or manageable?", pkg)

        for c, pkg, jsn_s in to_link:
            if c.startswith("file://"):
                # The conda functions (specifically remove_auth) assume the input
                # is a url; a file uri on windows with a drive letter messes them up.
                key = c
            else:
                key = split_anaconda_token(remove_auth(c))[0]
            if key not in lookup_dict:
                raise ValueError("missing key {} in channels: {}".format(key, lookup_dict))
            sdir = lookup_dict[key]
            rec = to_package_record_from_subjson(sdir, pkg, jsn_s)
            final_precs.add(rec)

        # state["old_specs_to_add"] = self.specs_to_add
        # state["old_specs_to_remove"] = self.specs_to_remove
        state["final_prefix_state"] = final_precs
        state["names_to_add"] = [name for name in names_to_add if not name.startswith("__")]
        state["names_to_remove"] = [name for name in names_to_remove if not name.startswith("__")]

        return state

    def _parse_problems(self, problems, previous):
        dashed_specs = []       # e.g. package-1.2.3-h5487548_0
        conda_build_specs = []  # e.g. package 1.2.8.*
        for line in problems.splitlines():
            line = line.strip()
            words = line.split()
            if not line.startswith("- "):
                continue
            if "none of the providers can be installed" in line:
                assert words[1] == "package"
                assert words[3] == "requires"
                dashed_specs.append(words[2])
                end = words.index("but")
                conda_build_specs.append(words[4:end])
            elif "- nothing provides" in line and "needed by" in line:
                dashed_specs.append(words[-1])
            elif "- nothing provides" in line:
                conda_build_specs.append(words[4:])

        conflicts = {}
        for conflict in dashed_specs:
            name, version, build = conflict.rsplit("-", 2)
            conflicts[name] = MatchSpec(name=name, version=version, build=build)
        for conflict in conda_build_specs:
            kwargs = {"name": conflict[0].rstrip(",")}
            if len(conflict) >= 2:
                kwargs["version"] = conflict[1].rstrip(",")
            if len(conflict) == 3:
                kwargs["build"] = conflict[2].rstrip(",")
            conflicts[kwargs["name"]] = MatchSpec(**kwargs)

        previous_set = set(previous.values())
        current_set = set(conflicts.values())

        diff = current_set.difference(previous_set)
        if len(diff) > 1 and "python" in conflicts:
            # Only report python as conflict if it's the only conflict reported
            # This helps us prioritize neutering for other dependencies first
            conflicts.pop("python")

        current_set = set(conflicts.values())
        if (previous and (previous_set == current_set)) or len(diff) >= 10: # or previous_set.issubset(current_set)):
            # We have same or more (up to 10) conflicts now! Abort to avoid recursion.
            self.raise_for_problems(problems)

        # Preserve old conflicts (now neutered as name-only spes) in the
        # new list of conflicts (unless a different variant is now present)
        # This allows us to have a conflict memory for next attempts.
        for spec in previous:
            if spec not in conflicts:
                conflicts[spec] = MatchSpec(name=spec)


        return conflicts

    def _post_solve_tasks(self,
                          state,
                          deps_modifier=NULL,
                          update_modifier=NULL,
                          force_reinstall=NULL,
                          ignore_pinned=NULL,
                          force_remove=NULL,
                          prune=NULL):
        specs_map = state["specs_map"]
        final_prefix_map = TrackedDict({pkg.name: pkg for pkg in state["final_prefix_state"]})
        history_map = state["history"].get_requested_specs_map()
        self.neutered_specs = tuple(pkg_spec for pkg_name, pkg_spec in specs_map.items() if
                                    pkg_name in history_map and
                                    pkg_spec.strictness < history_map[pkg_name].strictness)

        # TODO: We are currently not handling dependencies orphaned after identifying
        # conflicts (stored in `ssc.add_back_map`).

        if deps_modifier == DepsModifier.NO_DEPS:
            # In the NO_DEPS case, we need to start with the original list of packages in the
            # environment, and then only modify packages that match specs_to_add or
            # specs_to_remove.
            #
            # Help information notes that use of NO_DEPS is expected to lead to broken
            # environments.
            _no_deps_solution = IndexedSet(state["conda_prefix_data"].iter_records())
            only_remove_these = set(prec
                                    for name in state["names_to_remove"]
                                    for prec in _no_deps_solution
                                    if MatchSpec(name).match(prec))
            _no_deps_solution -= only_remove_these

            only_add_these = set(prec
                                 for name in state["names_to_add"]
                                 for prec in state["final_prefix_state"]
                                 if MatchSpec(name).match(prec))
            remove_before_adding_back = set(prec.name for prec in only_add_these)
            _no_deps_solution = IndexedSet(prec for prec in _no_deps_solution
                                           if prec.name not in remove_before_adding_back)
            _no_deps_solution |= only_add_these
            final_prefix_map = {p.name: p for p in _no_deps_solution}

        # If ONLY_DEPS is set, we need to make sure the originally requested specs
        # are not part of the result
        elif deps_modifier == DepsModifier.ONLY_DEPS and update_modifier != UpdateModifier.UPDATE_DEPS:
            graph = PrefixGraph(state["final_prefix_state"], self.specs_to_add)
            removed_nodes = graph.remove_youngest_descendant_nodes_with_specs()
            specs_to_add = set(MatchSpec(name) for name in state["names_to_add"])
            for pkg_record in removed_nodes:
                for dependency in pkg_record.depends:
                    dependency = MatchSpec(dependency)
                    if dependency.name not in specs_map:
                        specs_to_add.add(dependency)
            state["names_to_add"] = set(spec.name for spec in specs_to_add)

            # Add back packages that are already in the prefix.
            specs_to_remove_names = set(name for name in state["names_to_remove"])
            add_back = [state["conda_prefix_data"].get(node.name, None) for node in removed_nodes
                        if node.name not in specs_to_remove_names]
            final_prefix_map = {p.name: p for p in concatv(graph.graph, filter(None, add_back))}

        elif update_modifier == UpdateModifier.UPDATE_DEPS:
            # This code below is adapted from the legacy solver logic
            # found in Solver._post_sat_handling()

            # We need a post-solve to find the full chain of dependencies
            # for the requested specs (1) The previous solve gave us
            # the packages that would be installed normally. We take
            # that list and process their dependencies too so we can add
            # those explicitly to the list of packages to be updated.
            # If additionally DEPS_ONLY is set, we need to remove the
            # originally requested specs from the final list of explicit
            # packages.

            # (2) Get the dependency tree for each dependency
            graph = PrefixGraph(state["final_prefix_state"])
            update_names = set()
            for spec in self.specs_to_add:
                node = graph.get_node_by_name(spec.name)
                update_names.update(ancest_rec.name for ancest_rec in graph.all_ancestors(node))
            specs_map = TrackedDict({name: MatchSpec(name) for name in update_names})

            # Remove pinned_specs and any python spec (due to major-minor pinning business rule).
            for spec in self._pinned_specs(state, ignore_pinned):
                specs_map.pop(spec.name, None)
            # TODO: This kind of version constrain patching is done several times in different
            # parts of the code, so it might be a good candidate for a dedicate utility function
            if "python" in specs_map:
                python_rec = state["conda_prefix_data"].get("python")
                py_ver = ".".join(python_rec.version.split(".")[:2]) + ".*"
                specs_map["python"] = MatchSpec(name="python", version=py_ver)

            # Add in the original specs_to_add on top.
            specs_map.update({spec.name: spec for spec in self.specs_to_add})

            with context.override("quiet", True):
                # Create a new solver instance to perform a 2nd solve with deps added
                # We do it like this to avoid overwriting state accidentally. Instead,
                # we will import the needed state bits manually.
                solver2 = self.__class__(self.prefix, self.channels, self.subdirs,
                                         list(specs_map.values()), self.specs_to_remove,
                                         self._repodata_fn, "recursive_call_for_update_deps")
                solved_pkgs = solver2.solve_final_state(
                    update_modifier=UpdateModifier.UPDATE_SPECS,  # avoid recursion!
                    deps_modifier=deps_modifier,
                    ignore_pinned=ignore_pinned,
                    force_remove=force_remove,
                    force_reinstall=force_reinstall,
                    prune=prune)
                final_prefix_map = {p.name: p for p in solved_pkgs}
                # NOTE: We are exporting state back to the class! These are expected by
                # super().solve_for_diff() and super().solve_for_transaction() :/
                self.specs_to_add = solver2.specs_to_add.copy()
                self.specs_to_remove = solver2.specs_to_remove.copy()

            prune = False

        # Prune leftovers
        if prune:
            graph = PrefixGraph(final_prefix_map.values(), specs_map.values())
            graph.prune()
            final_prefix_map = {p.name: p for p in graph.graph}

        # Wrap up and return the final state

        # NOTE: We are exporting state back to the class! These are expected by
        # super().solve_for_diff() and super().solve_for_transaction() :/
        # self.specs_to_add = {MatchSpec(name) for name in state["names_to_add"]
        #                      if not name.startswith("__")}
        # self.specs_to_remove = {MatchSpec(name) for name in state["names_to_remove"]
        #                         if not name.startswith("__")}

        # TODO: Review performance here just in case
        return IndexedSet(PrefixGraph(final_prefix_map.values()).graph)

    def raise_for_problems(self, problems):
        for line in problems.splitlines():
            line = line.strip()
            if line.startswith("- nothing provides requested"):
                packages = line.split()[4:]
                raise PackagesNotFoundError([" ".join(packages)])
        raise RawStrUnsatisfiableError(problems)


class SolverStateContainer(object):
    # A mutable container with defined attributes to help keep method signatures clean
    # and also keep track of important state variables.

    def __init__(self, prefix, update_modifier, deps_modifier, prune, ignore_pinned, force_remove,
                 should_retry_solve):
        # prefix, channels, subdirs, specs_to_add, specs_to_remove
        # self.prefix = prefix
        # self.channels = channels
        # self.subdirs = subdirs
        # self.specs_to_add = specs_to_add
        # self.specs_to_remove = specs_to_remove

        # Group 1. Behavior flags
        self.update_modifier = update_modifier
        self.deps_modifier = deps_modifier
        self.prune = prune
        self.ignore_pinned = ignore_pinned
        self.force_remove = force_remove
        self.should_retry_solve = should_retry_solve

        # Group 2. System state
        self.prefix = prefix
        # self.prefix_data = None
        # self.specs_from_history_map = None
        # self.track_features_specs = None
        # self.pinned_specs = None

        # Group 3. Repository metadata
        self.index = None
        self.r = None

        # Group 4. Mutable working containers
        self.specs_map = odict()
        self.solution_precs = tuple(self.prefix_data.iter_records())
        self.add_back_map = {}  # name: (prec, spec)
        self.final_environment_specs = None

    @memoizedproperty
    def prefix_data(self):
        return PrefixData(self.prefix)

    @memoizedproperty
    def specs_from_history_map(self):
        return History(self.prefix).get_requested_specs_map()

    @memoizedproperty
    def track_features_specs(self):
        return tuple(MatchSpec(x + '@') for x in context.track_features)

    @memoizedproperty
    def pinned_specs(self):
        return () if self.ignore_pinned else get_pinned_specs(self.prefix)

    def set_repository_metadata(self, index, r):
        self.index, self.r = index, r

    def working_state_reset(self):
        self.specs_map = odict()
        self.solution_precs = tuple(self.prefix_data.iter_records())
        self.add_back_map = {}  # name: (prec, spec)
        self.final_environment_specs = None


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


class TrackedDict(dict):
    def __setitem__(self, k, v) -> None:
        if k in self:
            oldv = self[k]
            if v == oldv:
                log.debug("  EQU: %s = %s", k, v)
            else:
                log.debug("  UPD: %s from %s to %s", k, self[k], v)
        else:
            log.debug("  NEW: %s = %s", k, v)
        return super().__setitem__(k, v)

    def __delitem__(self, v) -> None:
        log.debug("  DEL: %s", v)
        return super().__delitem__(v)

    def update(self, *args, **kwargs):
        old = self.copy()
        super().update(*args, **kwargs)
        for k, v in self.items():
            if k in old:
                oldv = old[k]
                if v != oldv:
                    log.debug("  UPD: %s from %s to %s", k, old[k], v)
            else:
                log.debug("  NEW: %s = %s", k, v)
