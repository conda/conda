# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import defaultdict
from itertools import chain
from logging import DEBUG, getLogger

from .base.constants import MAX_CHANNEL_PRIORITY
from .base.context import context
from .common.compat import iteritems, iterkeys, itervalues, odict, on_win, text_type
from .common.io import time_recorder
from .common.logic import Clauses, minimal_unsatisfiable_subset
from .common.toposort import toposort
from .exceptions import ResolvePackageNotFound, UnsatisfiableError
from .models.channel import Channel, MultiChannel
from .models.enums import NoarchType
from .models.match_spec import MatchSpec
from .models.records import PackageRecord
from .models.version import VersionOrder

try:
    from cytoolz.itertoolz import concat, groupby
except ImportError:  # pragma: no cover
    from ._vendor.toolz.itertoolz import concat, groupby  # NOQA

log = getLogger(__name__)
stdoutlog = getLogger('conda.stdoutlog')

# used in conda build
Unsatisfiable = UnsatisfiableError
ResolvePackageNotFound = ResolvePackageNotFound


def dashlist(iterable, indent=2):
    return ''.join('\n' + ' ' * indent + '- ' + str(x) for x in iterable)


class Resolve(object):

    def __init__(self, index, sort=False, processed=False, channels=()):
        self.index = index

        self.channels = channels
        self._channel_priorities_map = self._make_channel_priorities(channels) if channels else {}

        groups = {}
        trackers = defaultdict(list)

        for _, info in iteritems(index):
            groups.setdefault(info['name'], []).append(info)
            for feature_name in info.get('track_features') or ():
                trackers[feature_name].append(info)

        self.groups = groups  # Dict[package_name, List[PackageRecord]]
        self.trackers = trackers  # Dict[track_feature, List[PackageRecord]]
        self.find_matches_ = {}  # Dict[MatchSpec, List[PackageRecord]]
        self.ms_depends_ = {}  # Dict[PackageRecord, List[MatchSpec]]
        self._reduced_index_cache = {}

        if sort:
            for name, group in iteritems(groups):
                groups[name] = sorted(group, key=self.version_key, reverse=True)

    def default_filter(self, features=None, filter=None):
        # TODO: fix this import; this is bad
        from .core.subdir_data import make_feature_record

        if filter is None:
            filter = {}
        else:
            filter.clear()

        filter.update({make_feature_record(fstr): False for fstr in iterkeys(self.trackers)})
        if features:
            filter.update({make_feature_record(fstr): True for fstr in features})
        return filter

    def valid(self, spec_or_prec, filter, optional=True):
        """Tests if a package, MatchSpec, or a list of both has satisfiable
        dependencies, assuming cyclic dependencies are always valid.

        Args:
            spec_or_prec: a package record, a MatchSpec, or an iterable of these.
            filter: a dictionary of (fkey,valid) pairs, used to consider a subset
                of dependencies, and to eliminate repeated searches.
            optional: if True (default), do not enforce optional specifications
                when considering validity. If False, enforce them.

        Returns:
            True if the full set of dependencies can be satisfied; False otherwise.
            If filter is supplied and update is True, it will be updated with the
            search results.
        """
        def v_(spec):
            return v_ms_(spec) if isinstance(spec, MatchSpec) else v_fkey_(spec)

        def v_ms_(ms):
            return ((optional and ms.optional) or
                    any(v_fkey_(fkey) for fkey in self.find_matches(ms)))

        def v_fkey_(prec):
            val = filter.get(prec)
            if val is None:
                filter[prec] = True
                val = filter[prec] = all(v_ms_(ms) for ms in self.ms_depends(prec))
            return val

        result = v_(spec_or_prec)
        return result

    def invalid_chains(self, spec, filter, optional=True):
        """Constructs a set of 'dependency chains' for invalid specs.

        A dependency chain is a tuple of MatchSpec objects, starting with
        the requested spec, proceeding down the dependency tree, ending at
        a specification that cannot be satisfied. Uses self.valid_ as a
        filter, both to prevent chains and to allow other routines to
        prune the list of valid packages with additional criteria.

        Args:
            spec: a package key or MatchSpec
            filter: a dictionary of (prec, valid) pairs to be used when
                testing for package validity.
            optional: if True (default), do not enforce optional specifications
                when considering validity. If False, enforce them.

        Returns:
            A generator of tuples, empty if the MatchSpec is valid.
        """
        def chains_(spec, names):
            if spec.name in names:
                return
            names.add(spec.name)
            if self.valid(spec, filter, optional):
                return
            precs = self.find_matches(spec)
            found = False
            for prec in precs:
                for m2 in self.ms_depends(prec):
                    for x in chains_(m2, names):
                        found = True
                        yield (spec,) + x
            if not found:
                yield (spec,)
        return chains_(spec, set())

    def verify_specs(self, specs):
        """Perform a quick verification that specs and dependencies are reasonable.

        Args:
            specs: An iterable of strings or MatchSpec objects to be tested.

        Returns:
            Nothing, but if there is a conflict, an error is thrown.

        Note that this does not attempt to resolve circular dependencies.
        """
        spec2 = []
        bad_deps = []
        feats = set()
        for s in specs:
            ms = MatchSpec(s)
            if ms.get_exact_value('track_features'):
                feature_names = ms.get_exact_value('track_features')
                feats.update(feature_names)
            elif ms.name[-1] == '@':
                # TODO: remove
                feats.add(ms.name[:-1])
            else:
                spec2.append(ms)
        for ms in spec2:
            filter = self.default_filter(feats)
            # type: Map[PackageRecord, bool]
            bad_deps.extend(self.invalid_chains(ms, filter))
        if bad_deps:
            raise ResolvePackageNotFound(bad_deps)
        return spec2, feats

    def find_conflicts(self, specs):
        """Perform a deeper analysis on conflicting specifications, by attempting
        to find the common dependencies that might be the cause of conflicts.

        Args:
            specs: An iterable of strings or MatchSpec objects to be tested.
            It is assumed that the specs conflict.

        Returns:
            Nothing, because it always raises an UnsatisfiableError.

        Strategy:
            If we're here, we know that the specs conflict. This could be because:
            - One spec conflicts with another; e.g.
                  ['numpy 1.5*', 'numpy >=1.6']
            - One spec conflicts with a dependency of another; e.g.
                  ['numpy 1.5*', 'scipy 0.12.0b1']
            - Each spec depends on *the same package* but in a different way; e.g.,
                  ['A', 'B'] where A depends on numpy 1.5, and B on numpy 1.6.
            Technically, all three of these cases can be boiled down to the last
            one if we treat the spec itself as one of the "dependencies". There
            might be more complex reasons for a conflict, but this code only
            considers the ones above.

            The purpose of this code, then, is to identify packages (like numpy
            above) that all of the specs depend on *but in different ways*. We
            then identify the dependency chains that lead to those packages.
        """
        sdeps = {}
        # For each spec, assemble a dictionary of dependencies, with package
        # name as key, and all of the matching packages as values.
        for ms in specs:
            rec = sdeps.setdefault(ms, {})
            slist = [ms]
            while slist:
                ms2 = slist.pop()
                deps = rec.setdefault(ms2.name, set())
                for fkey in self.find_matches(ms2):
                    if fkey not in deps:
                        deps.add(fkey)
                        slist.extend(ms3 for ms3 in self.ms_depends(fkey) if ms3.name != ms.name)

        # Find the list of dependencies they have in common. And for each of
        # *those*, find the individual packages that they all share. Those need
        # to be removed as conflict candidates.
        commkeys = set.intersection(*(set(s.keys()) for s in sdeps.values()))
        commkeys = {k: set.intersection(*(v[k] for v in sdeps.values())) for k in commkeys}

        # and find the dependency chains that lead to them.
        bad_deps = []
        for ms, sdep in iteritems(sdeps):
            filter = {}
            for mn, v in sdep.items():
                if mn != ms.name and mn in commkeys:
                    # Mark this package's "unique" dependencies as invalid
                    for fkey in v - commkeys[mn]:
                        filter[fkey] = False
            # Find the dependencies that lead to those invalid choices
            ndeps = set(self.invalid_chains(ms, filter, False))
            # This may produce some additional invalid chains that we
            # don't care about. Select only those that terminate in our
            # predetermined set of "common" keys.
            ndeps = [nd for nd in ndeps if nd[-1].name in commkeys]
            if ndeps:
                bad_deps.extend(ndeps)
            else:
                # This means the package *itself* was the common conflict.
                bad_deps.append((ms,))

        raise UnsatisfiableError(bad_deps)

    def get_reduced_index(self, specs):
        # TODO: fix this import; this is bad
        from .core.subdir_data import make_feature_record

        cache_key = frozenset(specs)
        if cache_key in self._reduced_index_cache:
            return self._reduced_index_cache[cache_key]

        if log.isEnabledFor(DEBUG):
            log.debug('Retrieving packages for: %s', dashlist(sorted(text_type(s) for s in specs)))

        specs, features = self.verify_specs(specs)
        filter = self.default_filter(features)
        snames = set()

        def filter_group(matches):
            match1 = next(ms for ms in matches)
            name = match1.name
            group = self.groups.get(name, [])

            # Prune packages that don't match any of the patterns
            # or which have unsatisfiable dependencies
            nold = nnew = 0
            for fkey in group:
                if filter.setdefault(fkey, True):
                    nold += 1
                    sat = (self.match_any(matches, fkey) and
                           all(any(filter.get(f2, True) for f2 in self.find_matches(ms))
                               for ms in self.ms_depends(fkey)))
                    filter[fkey] = sat
                    nnew += sat

            reduced = nnew < nold
            if reduced:
                log.debug('%s: pruned from %d -> %d' % (name, nold, nnew))
            if any(ms.optional for ms in matches):
                return reduced
            elif nnew == 0:
                # Indicates that a conflict was found; we can exit early
                return None

            # Perform the same filtering steps on any dependencies shared across
            # *all* packages in the group. Even if just one of the packages does
            # not have a particular dependency, it must be ignored in this pass.
            # Otherwise, we might do more filtering than we should---and it is
            # better to have extra packages here than missing ones.
            if reduced or name not in snames:
                snames.add(name)
                cdeps = {}
                for fkey in group:
                    if filter.get(fkey, True):
                        for m2 in self.ms_depends(fkey):
                            if m2.get_exact_value('name') and not m2.optional:
                                cdeps.setdefault(m2.name, []).append(m2)
                for deps in itervalues(cdeps):
                    if len(deps) >= nnew:
                        res = filter_group(set(deps))
                        if res:
                            reduced = True
                        elif res is None:
                            # Indicates that a conflict was found; we can exit early
                            return None

            return reduced

        # Iterate on pruning until no progress is made. We've implemented
        # what amounts to "double-elimination" here; packages get one additional
        # chance after their first "False" reduction. This catches more instances
        # where one package's filter affects another. But we don't have to be
        # perfect about this, so performance matters.
        for iter in range(2):
            snames.clear()
            slist = list(specs)
            found = False
            while slist:
                s = slist.pop()
                found = filter_group([s])
                if found:
                    slist.append(s)
                elif found is None:
                    break
            if found is None:
                filter = self.default_filter(features)
                break

        # Determine all valid packages in the dependency graph
        reduced_index = {}
        slist = list(specs)
        for fstr in features:
            prec = make_feature_record(fstr)
            reduced_index[prec] = prec
        while slist:
            this_spec = slist.pop()
            for prec in self.find_matches(this_spec):
                if reduced_index.get(prec) is None and self.valid(prec, filter):
                    reduced_index[prec] = prec
                    for ms in self.ms_depends(prec):
                        # We do not pull packages into the reduced index due
                        # to a track_features dependency. Remember, a feature
                        # specifies a "soft" dependency: it must be in the
                        # environment, but it is not _pulled_ in. The SAT
                        # logic doesn't do a perfect job of capturing this
                        # behavior, but keeping these packags out of the
                        # reduced index helps. Of course, if _another_
                        # package pulls it in by dependency, that's fine.
                        if 'track_features' not in ms:
                            slist.append(ms)
        self._reduced_index_cache[cache_key] = reduced_index
        return reduced_index

    def match_any(self, mss, prec):
        return any(ms.match(prec) for ms in mss)

    def match(self, ms, prec):
        # type: (MatchSpec, PackageRecord) -> bool
        return MatchSpec(ms).match(prec)

    def find_matches(self, ms):
        # type: (MatchSpec) -> List[PackageRecord]
        res = self.find_matches_.get(ms, None)
        if res is None:
            if ms.get_exact_value('name'):
                res = self.groups.get(ms.name, [])
            elif ms.get_exact_value('track_features'):
                feature_names = ms.get_exact_value('track_features')
                res = list(chain.from_iterable(self.trackers[feature_name]
                                               for feature_name in feature_names
                                               if feature_name in self.trackers))
            else:
                res = self.index.values()
            res = [p for p in res if self.match(ms, p)]
            self.find_matches_[ms] = res
        return res

    def ms_depends(self, prec):
        # type: (PackageRecord) -> List[MatchSpec]
        deps = self.ms_depends_.get(prec)
        if deps is None:
            deps = [MatchSpec(d) for d in prec.combined_depends]
            deps.extend(MatchSpec(track_features=feat) for feat in prec.features)
            self.ms_depends_[prec] = deps
        return deps

    def version_key(self, prec, vtype=None):
        channel = prec.channel
        channel_priority = self._channel_priorities_map.get(channel.name, 1)  # TODO: ask @mcg1969 why the default value is 1 here  # NOQA
        valid = 1 if channel_priority < MAX_CHANNEL_PRIORITY else 0
        version_comparator = VersionOrder(prec.get('version', ''))
        build_number = prec.get('build_number', 0)
        build_string = prec.get('build')
        ts = prec.get('timestamp', 0)
        if context.channel_priority:
            return valid, -channel_priority, version_comparator, build_number, ts, build_string
        else:
            return valid, version_comparator, -channel_priority, build_number, ts, build_string

    @staticmethod
    def _make_channel_priorities(channels):
        priorities_map = odict()
        for priority_counter, chn in enumerate(concat(
            (Channel(cc) for cc in c._channels) if isinstance(c, MultiChannel) else (c,)
            for c in (Channel(c) for c in channels)
        )):
            channel_name = chn.name
            if channel_name in priorities_map:
                continue
            priorities_map[channel_name] = min(priority_counter, MAX_CHANNEL_PRIORITY - 1)
        return priorities_map

    def get_pkgs(self, ms, emptyok=False):  # pragma: no cover
        # legacy method for conda-build
        ms = MatchSpec(ms)
        precs = self.find_matches(ms)
        if not precs and not emptyok:
            raise ResolvePackageNotFound([(ms,)])
        return sorted(precs, key=self.version_key)

    @staticmethod
    def to_sat_name(val):
        # val can be a PackageRef or MatchSpec
        if isinstance(val, PackageRecord):
            return val.dist_str()
        elif isinstance(val, MatchSpec):
            return '@s@' + text_type(val) + ('?' if val.optional else '')
        else:
            raise NotImplementedError()

    @staticmethod
    def to_feature_metric_id(prec_dist_str, feat):
        return '@fm@%s@%s' % (prec_dist_str, feat)

    def push_MatchSpec(self, C, spec):
        spec = MatchSpec(spec)
        sat_name = self.to_sat_name(spec)
        m = C.from_name(sat_name)
        if m is not None:
            # the spec has already been pushed onto the clauses stack
            return sat_name

        simple = spec._is_single()
        nm = spec.get_exact_value('name')
        tf = frozenset(_tf for _tf in (
            f.strip() for f in spec.get_exact_value('track_features') or ()
        ) if _tf)

        if nm:
            tgroup = libs = self.groups.get(nm, [])
        elif tf:
            assert len(tf) == 1
            k = next(iter(tf))
            tgroup = libs = self.trackers.get(k, [])
        else:
            tgroup = libs = self.index.keys()
            simple = False
        if not simple:
            libs = [fkey for fkey in tgroup if self.match(spec, fkey)]
        if len(libs) == len(tgroup):
            if spec.optional:
                m = True
            elif not simple:
                ms2 = MatchSpec(track_features=tf) if tf else MatchSpec(nm)
                m = C.from_name(self.push_MatchSpec(C, ms2))
        if m is None:
            sat_names = [self.to_sat_name(prec) for prec in libs]
            if spec.optional:
                ms2 = MatchSpec(track_features=tf) if tf else MatchSpec(nm)
                sat_names.append('!' + self.to_sat_name(ms2))
            m = C.Any(sat_names)
        C.name_var(m, sat_name)
        return sat_name

    def gen_clauses(self):
        C = Clauses()
        for name, group in iteritems(self.groups):
            group = [self.to_sat_name(prec) for prec in group]
            # Create one variable for each package
            for sat_name in group:
                C.new_var(sat_name)
            # Create one variable for the group
            m = C.new_var(self.to_sat_name(MatchSpec(name)))

            # Exactly one of the package variables, OR
            # the negation of the group variable, is true
            C.Require(C.ExactlyOne, group + [C.Not(m)])

        # If a package is installed, its dependencies must be as well
        for prec in itervalues(self.index):
            nkey = C.Not(self.to_sat_name(prec))
            for ms in self.ms_depends(prec):
                C.Require(C.Or, nkey, self.push_MatchSpec(C, ms))

        log.debug("gen_clauses returning with clause count: %s", len(C.clauses))
        return C

    def generate_spec_constraints(self, C, specs):
        result = [(self.push_MatchSpec(C, ms),) for ms in specs]
        log.debug("generate_spec_constraints returning with clause count: %s", len(C.clauses))
        return result

    def generate_feature_count(self, C):
        result = {self.push_MatchSpec(C, MatchSpec(track_features=name)): 1
                  for name in iterkeys(self.trackers)}
        log.debug("generate_feature_count returning with clause count: %s", len(C.clauses))
        return result

    def generate_update_count(self, C, specs):
        return {'!'+ms.target: 1 for ms in specs if ms.target and C.from_name(ms.target)}

    def generate_feature_metric(self, C):
        eq = {}  # a C.minimize() objective: Dict[varname, coeff]
        # Given a pair (prec, feature), assign a "1" score IF:
        # - The prec is installed
        # - The prec does NOT require the feature
        # - At least one package in the group DOES require the feature
        # - A package that tracks the feature is installed
        for name, group in iteritems(self.groups):
            prec_feats = {self.to_sat_name(prec): set(prec.features) for prec in group}
            active_feats = set.union(*prec_feats.values()).intersection(self.trackers)
            for feat in active_feats:
                clause_id_for_feature = self.push_MatchSpec(C, MatchSpec(track_features=feat))
                for prec_sat_name, features in prec_feats.items():
                    if feat not in features:
                        feature_metric_id = self.to_feature_metric_id(prec_sat_name, feat)
                        C.name_var(C.And(prec_sat_name, clause_id_for_feature), feature_metric_id)
                        eq[feature_metric_id] = 1
        return eq

    def generate_removal_count(self, C, specs):
        return {'!'+self.push_MatchSpec(C, ms.name): 1 for ms in specs}

    def generate_install_count(self, C, specs):
        return {self.push_MatchSpec(C, ms.name): 1 for ms in specs if ms.optional}

    def generate_package_count(self, C, missing):
        return {self.push_MatchSpec(C, nm): 1 for nm in missing}

    def generate_version_metrics(self, C, specs, include0=False):
        # each of these are weights saying how well packages match the specs
        #    format for each: a C.minimize() objective: Dict[varname, coeff]
        eqc = {}  # channel
        eqv = {}  # version
        eqb = {}  # build number
        eqt = {}  # timestamp

        sdict = {}  # Dict[package_name, PackageRecord]

        for s in specs:
            s = MatchSpec(s)  # needed for testing
            sdict.setdefault(s.name, [])
            # # TODO: this block is important! can't leave it commented out
            # rec = sdict.setdefault(s.name, [])
            # if s.target:
            #     dist = Dist(s.target)
            #     if dist in self.index:
            #         if self.index[dist].get('priority', 0) < MAX_CHANNEL_PRIORITY:
            #             rec.append(dist)

        for name, targets in iteritems(sdict):
            pkgs = [(self.version_key(p), p) for p in self.groups.get(name, [])]
            pkey = None
            # keep in mind that pkgs is already sorted according to version_key (a tuple,
            #    so composite sort key).  Later entries in the list are, by definition,
            #    greater in some way, so simply comparing with != suffices.
            for version_key, prec in pkgs:
                if targets and any(prec == t for t in targets):
                    continue
                if pkey is None:
                    ic = iv = ib = it = 0
                # valid package, channel priority
                elif pkey[0] != version_key[0] or pkey[1] != version_key[1]:
                    ic += 1
                    iv = ib = it = 0
                # version
                elif pkey[2] != version_key[2]:
                    iv += 1
                    ib = it = 0
                # build number
                elif pkey[3] != version_key[3]:
                    ib += 1
                    it = 0
                elif pkey[4] != version_key[4]:
                    it += 1

                prec_sat_name = self.to_sat_name(prec)
                if ic or include0:
                    eqc[prec_sat_name] = ic
                if iv or include0:
                    eqv[prec_sat_name] = iv
                if ib or include0:
                    eqb[prec_sat_name] = ib
                if it or include0:
                    eqt[prec_sat_name] = it
                pkey = version_key

        return eqc, eqv, eqb, eqt

    def dependency_sort(self, must_have):
        # type: (Dict[package_name, PackageRecord]) -> List[PackageRecord]
        assert isinstance(must_have, dict)

        digraph = {}  # Dict[package_name, Set[dependent_package_names]]
        for package_name, prec in iteritems(must_have):
            if prec in self.index:
                digraph[package_name] = set(ms.name for ms in self.ms_depends(prec))

        # There are currently at least three special cases to be aware of.
        # 1. The `toposort()` function, called below, contains special case code to remove
        #    any circular dependency between python and pip.
        # 2. conda/plan.py has special case code for menuinst
        #       Always link/unlink menuinst first/last on windows in case a subsequent
        #       package tries to import it to create/remove a shortcut
        # 3. On windows, python noarch packages need an implicit dependency on conda added, if
        #    conda is in the list of packages for the environment.  Python noarch packages
        #    that have entry points use conda's own conda.exe python entry point binary. If conda
        #    is going to be updated during an operation, the unlink / link order matters.
        #    See issue #6057.

        if on_win and 'conda' in digraph:
            for package_name, dist in iteritems(must_have):
                record = self.index.get(prec)
                if hasattr(record, 'noarch') and record.noarch == NoarchType.python:
                    digraph[package_name].add('conda')

        sorted_keys = toposort(digraph)
        must_have = must_have.copy()
        # Take all of the items in the sorted keys
        # Don't fail if the key does not exist
        result = [must_have.pop(key) for key in sorted_keys if key in must_have]
        # Take any key that were not sorted
        result.extend(must_have.values())
        return result

    def environment_is_consistent(self, installed):
        log.debug('Checking if the current environment is consistent')
        if not installed:
            return None, []
        sat_name_map = {}  # Dict[sat_name, PackageRecord]
        specs = []
        for prec in installed:
            sat_name_map[self.to_sat_name(prec)] = prec
            specs.append(MatchSpec('%s %s %s' % (prec.name, prec.version, prec.build)))
        r2 = Resolve({prec: prec for prec in installed}, True, True, channels=self.channels)
        C = r2.gen_clauses()
        constraints = r2.generate_spec_constraints(C, specs)
        solution = C.sat(constraints)
        return bool(solution)

    def get_conflicting_specs(self, specs):
        if not specs:
            return ()
        reduced_index = self.get_reduced_index(specs)

        # Check if satisfiable
        def mysat(specs, add_if=False):
            constraints = r2.generate_spec_constraints(C, specs)
            return C.sat(constraints, add_if)

        r2 = Resolve(reduced_index, True, True, channels=self.channels)
        C = r2.gen_clauses()
        solution = mysat(specs, True)
        if solution:
            return ()
        else:
            specs = minimal_unsatisfiable_subset(specs, sat=mysat)
            return specs

    def bad_installed(self, installed, new_specs):
        log.debug('Checking if the current environment is consistent')
        if not installed:
            return None, []
        sat_name_map = {}  # Dict[sat_name, PackageRecord]
        specs = []
        for prec in installed:
            sat_name_map[self.to_sat_name(prec)] = prec
            specs.append(MatchSpec('%s %s %s' % (prec.name, prec.version, prec.build)))
        new_index = {prec: prec for prec in itervalues(sat_name_map)}
        r2 = Resolve(new_index, True, True, channels=self.channels)
        C = r2.gen_clauses()
        constraints = r2.generate_spec_constraints(C, specs)
        solution = C.sat(constraints)
        limit = xtra = None
        if not solution or xtra:
            def get_(name, snames):
                if name not in snames:
                    snames.add(name)
                    for fn in self.groups.get(name, []):
                        for ms in self.ms_depends(fn):
                            get_(ms.name, snames)
            # New addition: find the largest set of installed packages that
            # are consistent with each other, and include those in the
            # list of packages to maintain consistency with
            snames = set()
            eq_optional_c = r2.generate_removal_count(C, specs)
            solution, _ = C.minimize(eq_optional_c, C.sat())
            snames.update(sat_name_map[sat_name]['name']
                          for sat_name in (C.from_index(s) for s in solution)
                          if sat_name and sat_name[0] != '!' and '@' not in sat_name)
            # Existing behavior: keep all specs and their dependencies
            for spec in new_specs:
                get_(MatchSpec(spec).name, snames)
            if len(snames) < len(sat_name_map):
                limit = snames
                xtra = [rec for sat_name, rec in iteritems(sat_name_map)
                        if rec['name'] not in snames]
                log.debug('Limiting solver to the following packages: %s', ', '.join(limit))
        if xtra:
            log.debug('Packages to be preserved: %s', xtra)
        return limit, xtra

    def restore_bad(self, pkgs, preserve):
        if preserve:
            sdict = {prec.name: prec for prec in pkgs}
            pkgs.extend(p for p in preserve if p.name not in sdict)

    def install_specs(self, specs, installed, update_deps=True):
        specs = list(map(MatchSpec, specs))
        snames = {s.name for s in specs}
        log.debug('Checking satisfiability of current install')
        limit, preserve = self.bad_installed(installed, specs)
        for prec in installed:
            if prec not in self.index:
                continue
            name, version, build = prec.name, prec.version, prec.build
            schannel = prec.channel.canonical_name
            if name in snames or limit is not None and name not in limit:
                continue
            # If update_deps=True, set the target package in MatchSpec so that
            # the solver can minimize the version change. If update_deps=False,
            # fix the version and build so that no change is possible.
            if update_deps:
                # TODO: fix target here
                spec = MatchSpec(name=name, target=prec.dist_str())
            else:
                spec = MatchSpec(name=name, version=version,
                                 build=build, channel=schannel)
            specs.append(spec)
        return specs, preserve

    def install(self, specs, installed=None, update_deps=True, returnall=False):
        specs, preserve = self.install_specs(specs, installed or [], update_deps)
        pkgs = self.solve(specs, returnall=returnall, _remove=False)
        self.restore_bad(pkgs, preserve)
        return pkgs

    def remove_specs(self, specs, installed):
        nspecs = []
        # There's an imperfect thing happening here. "specs" nominally contains
        # a list of package names or track_feature values to be removed. But
        # because of add_defaults_to_specs it may also contain version contraints
        # like "python 2.7*", which are *not* asking for python to be removed.
        # We need to separate these two kinds of specs here.
        for s in map(MatchSpec, specs):
            # Since '@' is an illegal version number, this ensures that all of
            # these matches will never match an actual package. Combined with
            # optional=True, this has the effect of forcing their removal.
            if s._is_single():
                nspecs.append(MatchSpec(s, version='@', optional=True))
            else:
                nspecs.append(MatchSpec(s, optional=True))
        snames = set(s.name for s in nspecs if s.name)
        limit, _ = self.bad_installed(installed, nspecs)
        preserve = []
        for prec in installed:
            nm, ver = prec.name, prec.version
            if nm in snames:
                continue
            elif limit is not None:
                preserve.append(prec)
            else:
                # TODO: fix target here
                nspecs.append(MatchSpec(name=nm,
                                        version='>='+ver if ver else None,
                                        optional=True,
                                        target=prec.dist_str()))
        return nspecs, preserve

    def remove(self, specs, installed):
        specs, preserve = self.remove_specs(specs, installed)
        pkgs = self.solve(specs, _remove=True)
        self.restore_bad(pkgs, preserve)
        return pkgs

    @time_recorder("resolve_solve")
    def solve(self, specs, returnall=False, _remove=False):
        # type: (List[str], bool) -> List[PackageRecord]
        if log.isEnabledFor(DEBUG):
            log.debug('Solving for: %s', dashlist(sorted(text_type(s) for s in specs)))

        # Find the compliant packages
        len0 = len(specs)
        specs = tuple(map(MatchSpec, specs))
        reduced_index = self.get_reduced_index(specs)
        if not reduced_index:
            return False if reduced_index is None else ([[]] if returnall else [])

        # Check if satisfiable
        def mysat(specs, add_if=False):
            constraints = r2.generate_spec_constraints(C, specs)
            return C.sat(constraints, add_if)

        r2 = Resolve(reduced_index, True, True, channels=self.channels)
        C = r2.gen_clauses()
        solution = mysat(specs, True)
        if not solution:
            specs = minimal_unsatisfiable_subset(specs, sat=mysat)
            self.find_conflicts(specs)

        speco = []  # optional packages
        specr = []  # requested packages
        speca = []  # all other packages
        specm = set(r2.groups)  # missing from specs
        for k, s in enumerate(specs):
            if s.name in specm:
                specm.remove(s.name)
            if not s.optional:
                (speca if s.target or k >= len0 else specr).append(s)
            elif any(r2.find_matches(s)):
                s = MatchSpec(s.name, optional=True, target=s.target)
                speco.append(s)
                speca.append(s)
        speca.extend(MatchSpec(s) for s in specm)

        # Removed packages: minimize count
        if _remove:
            eq_optional_c = r2.generate_removal_count(C, speco)
            solution, obj7 = C.minimize(eq_optional_c, solution)
            log.debug('Package removal metric: %d', obj7)

        # Requested packages: maximize versions
        eq_req_c, eq_req_v, eq_req_b, eq_req_t = r2.generate_version_metrics(C, specr)
        solution, obj3a = C.minimize(eq_req_c, solution)
        solution, obj3 = C.minimize(eq_req_v, solution)
        log.debug('Initial package channel/version metric: %d/%d', obj3a, obj3)

        # Track features: minimize feature count
        eq_feature_count = r2.generate_feature_count(C)
        solution, obj1 = C.minimize(eq_feature_count, solution)
        log.debug('Track feature count: %d', obj1)

        # Featured packages: minimize number of featureless packages
        # installed when a featured alternative is feasible.
        # For example, package name foo exists with two built packages. One with
        # 'track_features: 'feat1', and one with 'track_features': 'feat2'.
        # The previous "Track features" minimization pass has chosen 'feat1' for the
        # environment, but not 'feat2'. In this case, the 'feat2' version of foo is
        # considered "featureless."
        eq_feature_metric = r2.generate_feature_metric(C)
        solution, obj2 = C.minimize(eq_feature_metric, solution)
        log.debug('Package misfeature count: %d', obj2)

        # Requested packages: maximize builds
        solution, obj4 = C.minimize(eq_req_b, solution)
        log.debug('Initial package build metric: %d', obj4)

        # Optional installations: minimize count
        if not _remove:
            eq_optional_install = r2.generate_install_count(C, speco)
            solution, obj49 = C.minimize(eq_optional_install, solution)
            log.debug('Optional package install metric: %d', obj49)

        # Dependencies: minimize the number of packages that need upgrading
        eq_u = r2.generate_update_count(C, speca)
        solution, obj50 = C.minimize(eq_u, solution)
        log.debug('Dependency update count: %d', obj50)

        # Remaining packages: maximize versions, then builds
        eq_c, eq_v, eq_b, eq_t = r2.generate_version_metrics(C, speca)
        solution, obj5a = C.minimize(eq_c, solution)
        solution, obj5 = C.minimize(eq_v, solution)
        solution, obj6 = C.minimize(eq_b, solution)
        log.debug('Additional package channel/version/build metrics: %d/%d/%d',
                  obj5a, obj5, obj6)

        # Maximize timestamps
        eq_t.update(eq_req_t)
        solution, obj6t = C.minimize(eq_t, solution)
        log.debug('Timestamp metric: %d', obj6t)

        # Prune unnecessary packages
        eq_c = r2.generate_package_count(C, specm)
        solution, obj7 = C.minimize(eq_c, solution, trymax=True)
        log.debug('Weak dependency count: %d', obj7)

        def clean(sol):
            return [q for q in (C.from_index(s) for s in sol)
                    if q and q[0] != '!' and '@' not in q]
        log.debug('Looking for alternate solutions')
        nsol = 1
        psolutions = []
        psolution = clean(solution)
        psolutions.append(psolution)
        while True:
            nclause = tuple(C.Not(C.from_name(q)) for q in psolution)
            solution = C.sat((nclause,), True)
            if solution is None:
                break
            nsol += 1
            if nsol > 10:
                log.debug('Too many solutions; terminating')
                break
            psolution = clean(solution)
            psolutions.append(psolution)

        if nsol > 1:
            psols2 = list(map(set, psolutions))
            common = set.intersection(*psols2)
            diffs = [sorted(set(sol) - common) for sol in psols2]
            if not context.json:
                stdoutlog.info(
                    '\nWarning: %s possible package resolutions '
                    '(only showing differing packages):%s%s' %
                    ('>10' if nsol > 10 else nsol,
                     dashlist(', '.join(diff) for diff in diffs),
                     '\n  ... and others' if nsol > 10 else ''))

        def stripfeat(sol):
            return sol.split('[')[0]

        new_index = {self.to_sat_name(prec): prec for prec in itervalues(self.index)}

        if returnall:
            if len(psolutions) > 1:
                raise RuntimeError()
            # TODO: clean up this mess
            # return [sorted(Dist(stripfeat(dname)) for dname in psol) for psol in psolutions]
            # return [sorted((new_index[sat_name] for sat_name in psol), key=lambda x: x.name)
            #         for psol in psolutions]

            # return sorted(Dist(stripfeat(dname)) for dname in psolutions[0])
        return sorted((new_index[sat_name] for sat_name in psolutions[0]), key=lambda x: x.name)
