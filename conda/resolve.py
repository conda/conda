from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import re

from .base.constants import DEFAULTS_CHANNEL_NAME, MAX_CHANNEL_PRIORITY
from .base.context import context
from .common.compat import iteritems, iterkeys, itervalues, string_types
from .console import setup_handlers
from .exceptions import CondaValueError, NoPackagesFoundError, UnsatisfiableError
from .logic import Clauses, minimal_unsatisfiable_subset
from .models.dist import Dist
from .toposort import toposort
from .version import VersionSpec, normalized_version

log = logging.getLogger(__name__)
dotlog = logging.getLogger('dotupdate')
stdoutlog = logging.getLogger('stdoutlog')
stderrlog = logging.getLogger('stderrlog')
setup_handlers()


# used in conda build
Unsatisfiable = UnsatisfiableError
NoPackagesFound = NoPackagesFoundError

def dashlist(iter):
    return ''.join('\n  - ' + str(x) for x in iter)


class MatchSpec(object):
    def __new__(cls, spec, target=Ellipsis, optional=Ellipsis, normalize=False):
        if isinstance(spec, cls):
            if target is Ellipsis and optional is Ellipsis and not normalize:
                return spec
            target = spec.target if target is Ellipsis else target
            optional = spec.optional if optional is Ellipsis else optional
            spec = spec.spec
        self = object.__new__(cls)
        self.target = None if target is Ellipsis else target
        self.optional = False if optional is Ellipsis else bool(optional)
        spec, _, oparts = spec.partition('(')
        if oparts:
            if oparts.strip()[-1] != ')':
                raise CondaValueError("Invalid MatchSpec: %s" % spec)
            for opart in oparts.strip()[:-1].split(','):
                if opart == 'optional':
                    self.optional = True
                elif opart.startswith('target='):
                    self.target = opart.split('=')[1].strip()
                else:
                    raise CondaValueError("Invalid MatchSpec: %s" % spec)
        spec = self.spec = spec.strip()
        parts = spec.split()
        nparts = len(parts)
        assert 1 <= nparts <= 3, repr(spec)
        self.name = parts[0]
        if nparts == 1:
            self.match_fast = self._match_any
            self.strictness = 1
            return self
        self.strictness = 2
        vspec = VersionSpec(parts[1])
        if vspec.is_exact():
            if nparts > 2 and '*' not in parts[2]:
                self.version, self.build = parts[1:]
                self.match_fast = self._match_exact
                self.strictness = 3
                return self
            if normalize and not parts[1].endswith('*'):
                parts[1] += '*'
                vspec = VersionSpec(parts[1])
                self.spec = ' '.join(parts)
        self.version = vspec
        if nparts == 2:
            self.match_fast = self._match_version
        else:
            rx = r'^(?:%s)$' % parts[2].replace('*', r'.*')
            self.build = re.compile(rx)
            self.match_fast = self._match_full
        return self

    def is_exact(self):
        return self.match_fast == self._match_exact

    def is_simple(self):
        return self.match_fast == self._match_any

    def _match_any(self, verison, build):
        return True

    def _match_version(self, version, build):
        return self.version.match(version)

    def _match_exact(self, version, build):
        return build == self.build and self.version == version

    def _match_full(self, version, build):
        return self.build.match(build) and self.version.match(version)

    def match(self, dist):
        # type: (Dist) -> bool
        name, version, build, _ = dist.quad
        if name != self.name:
            return False
        result = self.match_fast(version, build)
        return result

    def to_filename(self):
        if self.is_exact() and not self.optional:
            return self.name + '-%s-%s.tar.bz2' % (self.version, self.build)
        else:
            return None

    def __eq__(self, other):
        return (type(other) is MatchSpec and
                (self.spec, self.optional, self.target) ==
                (other.spec, other.optional, other.target))

    def __hash__(self):
        return hash(self.spec)

    def __repr__(self):
        return "MatchSpec('%s')" % self.__str__()

    def __str__(self):
        res = self.spec
        if self.optional or self.target:
            args = []
            if self.optional:
                args.append('optional')
            if self.target:
                args.append('target='+self.target)
            res = '%s (%s)' % (res, ','.join(args))
        return res


class Resolve(object):

    def __init__(self, index, sort=False, processed=False):
        self.index = index

        groups = {}
        trackers = {}

        for dist, info in iteritems(index):
            groups.setdefault(info['name'], []).append(dist)
            for feat in info.get('track_features', '').split():
                trackers.setdefault(feat, []).append(dist)

        self.groups = groups  # Dict[package_name, List[Dist]]
        self.trackers = trackers  # Dict[track_feature, List[Dist]]
        self.find_matches_ = {}  # Dict[MatchSpec, List[Dist]]
        self.ms_depends_ = {}  # Dict[Dist, List[MatchSpec]]

        if sort:
            for name, group in iteritems(groups):
                groups[name] = sorted(group, key=self.version_key, reverse=True)

    @property
    def installed(self):
        # type: () -> Set[Dist]
        installed = set()
        for dist, info in iteritems(self.index):
            if 'link' in info:
                installed.add(dist)
        return installed

    def default_filter(self, features=None, filter=None):
        if filter is None:
            filter = {}
        else:
            filter.clear()
        filter.update({Dist(fstr+'@'): False for fstr in iterkeys(self.trackers)})
        if features:
            filter.update({Dist(fstr+'@'): True for fstr in features})
        return filter

    def valid(self, spec_or_dist, filter):
        """Tests if a package, MatchSpec, or a list of both has satisfiable
        dependencies, assuming cyclic dependencies are always valid.

        Args:
            spec_or_dist: a package key, a MatchSpec, or an iterable of these.
            filter: a dictionary of (fkey,valid) pairs, used to consider a subset
                of dependencies, and to eliminate repeated searches.

        Returns:
            True if the full set of dependencies can be satisfied; False otherwise.
            If filter is supplied and update is True, it will be updated with the
            search results.
        """
        def v_(spec):
            return v_ms_(spec) if isinstance(spec, MatchSpec) else v_fkey_(spec)

        def v_ms_(ms):
            return ms.optional or any(v_fkey_(fkey) for fkey in self.find_matches(ms))

        def v_fkey_(dist):
            val = filter.get(dist)
            if val is None:
                filter[dist] = True
                val = filter[dist] = all(v_ms_(ms) for ms in self.ms_depends(dist))
            return val

        result = v_(spec_or_dist)
        return result

    def invalid_chains(self, spec, filter):
        """Constructs a set of 'dependency chains' for invalid specs.

        A dependency chain is a tuple of MatchSpec objects, starting with
        the requested spec, proceeding down the dependency tree, ending at
        a specification that cannot be satisfied. Uses self.valid_ as a
        filter, both to prevent chains and to allow other routines to
        prune the list of valid packages with additional criteria.

        Args:
            spec: a package key or MatchSpec
            filter: a dictionary of (dist, valid) pairs to be used when
                testing for package validity.

        Returns:
            A generator of tuples, empty if the MatchSpec is valid.
        """
        def chains_(spec, names):
            if spec.name in names:
                return
            names.add(spec.name)
            if self.valid(spec, filter):
                return
            dists = self.find_matches(spec) if isinstance(spec, MatchSpec) else [Dist(spec)]
            found = False
            for dist in dists:
                for m2 in self.ms_depends(dist):
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
            if ms.name[-1] == '@':
                feats.add(ms.name[:-1])
            else:
                spec2.append(ms)
        for ms in spec2:
            filter = self.default_filter(feats)
            bad_deps.extend(self.invalid_chains(ms, filter))
        if bad_deps:
            raise NoPackagesFoundError(bad_deps)
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
                    # Mark this package's "unique" dependencies as invali
                    for fkey in v - commkeys[mn]:
                        filter[fkey] = False
            # Find the dependencies that lead to those invalid choices
            ndeps = set(self.invalid_chains(ms, filter))
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
        log.debug('Retrieving packages for: %s', specs)

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
            if reduced or name not in snames:
                snames.add(name)
                cdeps = {}
                for fkey in group:
                    if filter.get(fkey, True):
                        for m2 in self.ms_depends(fkey):
                            if m2.name[0] != '@' and not m2.optional:
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
            dist = Dist(fstr + '@')
            reduced_index[dist] = self.index[dist]
        while slist:
            this_spec = slist.pop()
            for dist in self.find_matches(this_spec):
                if reduced_index.get(dist) is None and self.valid(dist, filter):
                    reduced_index[dist] = self.index[dist]
                    for ms in self.ms_depends(dist):
                        if ms.name[0] != '@':
                            slist.append(ms)
        return reduced_index

    def match_any(self, mss, fkey):
        rec = self.index[fkey]
        n, v, b = rec['name'], rec['version'], rec['build']
        return any(n == ms.name and ms.match_fast(v, b) for ms in mss)

    def match(self, ms, fkey):
        # type: (MatchSpec, Dist) -> bool
        rec = self.index[fkey]
        ms = MatchSpec(ms)
        return (ms.name == rec['name'] and
                ms.match_fast(rec['version'], rec['build']))

    def match_fast(self, ms, fkey):
        rec = self.index[fkey]
        return ms.match_fast(rec['version'], rec['build'])

    def find_matches(self, ms):
        # type: (MatchSpec) -> List[Dist]
        assert isinstance(ms, MatchSpec)
        res = self.find_matches_.get(ms, None)
        if res is None:
            if ms.name[0] == '@':
                res = self.trackers.get(ms.name[1:], [])
            else:
                res = self.groups.get(ms.name, [])
            res = [p for p in res if self.match_fast(ms, p)]
            self.find_matches_[ms] = res
        return res

    def ms_depends(self, dist):
        # type: (Dist) -> List[MatchSpec]
        deps = self.ms_depends_.get(dist, None)
        if deps is None:
            rec = self.index[dist]
            deps = [MatchSpec(d) for d in rec.get('depends', [])]
            deps.extend(MatchSpec('@'+feat) for feat in self.features(dist))
            self.ms_depends_[dist] = deps
        return deps

    def depends_on(self, spec, target):
        touched = set()
        if isinstance(target, string_types):
            target = (target,)

        def depends_on_(spec):
            if spec.name in target:
                return True
            if spec.name in touched:
                return False
            touched.add(spec.name)
            return any(depends_on_(ms)
                       for fn in self.find_matches(spec)
                       for ms in self.ms_depends(fn))
        return depends_on_(MatchSpec(spec))

    def version_key(self, dist, vtype=None):
        rec = self.index[dist]
        cpri = rec.get('priority', 1)
        valid = 1 if cpri < MAX_CHANNEL_PRIORITY else 0
        ver = normalized_version(rec.get('version', ''))
        bld = rec.get('build_number', 0)
        bs = rec.get('build_string')
        return ((valid, -cpri, ver, bld, bs) if context.channel_priority else
                (valid, ver, -cpri, bld, bs))

    def features(self, dist):
        return set(self.index[dist].get('features', '').split())

    def track_features(self, dist):
        return set(self.index[dist].get('track_features', '').split())

    def package_quad(self, dist):
        rec = self.index.get(dist, None)
        if rec is None:
            return dist.quad
        else:
            return (rec['name'], rec['version'], rec['build'],
                    rec.get('schannel', DEFAULTS_CHANNEL_NAME))

    def package_name(self, dist):
        return self.package_quad(dist)[0]

    def get_pkgs(self, ms, emptyok=False):
        # legacy method for conda-build
        # TODO: remove in conda 4.4
        return self.get_dists_for_spec(ms, emptyok)

    def get_dists_for_spec(self, ms, emptyok=False):
        ms = MatchSpec(ms)
        dists = self.find_matches(ms)
        if not dists and not emptyok:
            raise NoPackagesFoundError([(ms,)])
        return sorted(dists, key=self.version_key)

    @staticmethod
    def ms_to_v(ms):
        ms = MatchSpec(ms)
        return '@s@' + ms.spec + ('?' if ms.optional else '')

    def push_MatchSpec(self, C, ms):
        ms = MatchSpec(ms)
        name = self.ms_to_v(ms)
        m = C.from_name(name)
        if m is not None:
            return name
        tgroup = libs = (self.trackers.get(ms.name[1:], []) if ms.name[0] == '@'
                         else self.groups.get(ms.name, []))
        if not ms.is_simple():
            libs = [fkey for fkey in tgroup if self.match_fast(ms, fkey)]
        if len(libs) == len(tgroup):
            if ms.optional:
                m = True
            elif not ms.is_simple():
                m = C.from_name(self.push_MatchSpec(C, ms.name))
        if m is None:
            libs = [dist.full_name for dist in libs]
            if ms.optional:
                libs.append('!@s@'+ms.name)
            m = C.Any(libs)
        C.name_var(m, name)
        return name

    def gen_clauses(self):
        C = Clauses()
        for name, group in iteritems(self.groups):
            group = [dist.full_name for dist in group]
            # Create one variable for each package
            for fkey in group:
                C.new_var(fkey)
            # Create one variable for the group
            m = C.new_var(self.ms_to_v(name))
            # Exactly one of the package variables, OR
            # the negation of the group variable, is true
            C.Require(C.ExactlyOne, group + [C.Not(m)])
        # If a package is installed, its dependencies must be as well
        for dist in iterkeys(self.index):
            nkey = C.Not(dist.full_name)
            for ms in self.ms_depends(dist):
                C.Require(C.Or, nkey, self.push_MatchSpec(C, ms))

        return C

    def generate_spec_constraints(self, C, specs):
        return [(self.push_MatchSpec(C, ms),) for ms in specs]

    def generate_feature_count(self, C):
        return {self.push_MatchSpec(C, '@'+name): 1 for name in iterkeys(self.trackers)}

    def generate_update_count(self, C, specs):
        return {'!'+ms.target: 1 for ms in specs if ms.target and C.from_name(ms.target)}

    def generate_feature_metric(self, C):
        eq = {}  # a C.minimize() objective: Dict[varname, coeff]
        total = 0
        for name, group in iteritems(self.groups):
            nf = [len(self.features(dist)) for dist in group]
            maxf = max(nf)
            eq.update({dist.full_name: maxf-fc for dist, fc in zip(group, nf) if fc < maxf})
            total += maxf
        return eq, total

    def generate_removal_count(self, C, specs):
        return {'!'+self.push_MatchSpec(C, ms.name): 1 for ms in specs}

    def generate_package_count(self, C, missing):
        return {self.push_MatchSpec(C, nm): 1 for nm in missing}

    def generate_version_metrics(self, C, specs, include0=False):
        eqv = {}  # a C.minimize() objective: Dict[varname, coeff]
        eqb = {}  # a C.minimize() objective: Dict[varname, coeff]
        sdict = {}  # Dict[package_name, Dist]

        for s in specs:
            s = MatchSpec(s)  # needed for testing
            rec = sdict.setdefault(s.name, [])
            if s.target:
                dist = Dist(s.target)
                if dist in self.index:
                    if self.index[dist].get('priority', 0) < MAX_CHANNEL_PRIORITY:
                        rec.append(dist)

        for name, targets in iteritems(sdict):
            pkgs = [(self.version_key(p), p) for p in self.groups.get(name, [])]
            pkey = None
            for version_key, dist in pkgs:
                if targets and any(dist == t for t in targets):
                    continue
                if pkey is None:
                    iv = ib = 0
                elif any(pk != vk for pk, vk in zip(pkey[:3], version_key[:3])):
                    iv += 1
                    ib = 0
                elif pkey[3] != version_key[3]:
                    ib += 1

                if iv or include0:
                    eqv[dist.full_name] = iv
                if ib or include0:
                    eqb[dist.full_name] = ib
                pkey = version_key

        return eqv, eqb

    def dependency_sort(self, must_have):
        # type: (Dict[package_name, Dist]) -> List[Dist]
        assert isinstance(must_have, dict)

        digraph = {}
        for key, dist in iteritems(must_have):
            if dist in self.index:
                depends = set(ms.name for ms in self.ms_depends(dist))
                digraph[key] = depends
        sorted_keys = toposort(digraph)
        must_have = must_have.copy()
        # Take all of the items in the sorted keys
        # Don't fail if the key does not exist
        result = [must_have.pop(key) for key in sorted_keys if key in must_have]
        # Take any key that were not sorted
        result.extend(must_have.values())
        return result

    def explicit(self, specs):
        """
        Given the specifications, return:
          A. if one explicit specification is given, and
             all dependencies of this package are explicit as well ->
             return the filenames of those dependencies (as well as the
             explicit specification)
          B. if not one explicit specifications are given ->
             return the filenames of those (not thier dependencies)
          C. None in all other cases
        """
        specs = list(map(MatchSpec, specs))
        if len(specs) == 1:
            ms = MatchSpec(specs[0])
            fn = ms.to_filename()
            if fn is None:
                return None
            fkey = Dist(fn)
            if fkey not in self.index:
                return None
            res = [ms2.to_filename() for ms2 in self.ms_depends(fkey)]
            res.append(fn)
        else:
            res = [spec.to_filename() for spec in specs if str(spec) != 'conda']

        if None in res:
            return None
        res = [Dist(f) for f in sorted(res)]
        log.debug('explicit(%r) finished', specs)
        return res

    def sum_matches(self, fn1, fn2):
        assert isinstance(fn1, Dist)
        assert isinstance(fn2, Dist)
        return sum(self.match(ms, fn2) for ms in self.ms_depends(fn1))

    def bad_installed(self, installed, new_specs):
        log.debug('Checking if the current environment is consistent')
        if not installed:
            return None, []
        dists = {}  # Dict[Dist, Record]
        specs = []
        for dist in installed:
            dist = Dist(dist)
            rec = self.index[dist]
            dists[dist] = rec
            specs.append(MatchSpec(' '.join(self.package_quad(dist)[:3])))
        r2 = Resolve(dists, True, True)
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
            snames.update(dists[Dist(q)]['name']
                          for q in (C.from_index(s) for s in solution)
                          if q and q[0] != '!' and '@' not in q)
            # Existing behavior: keep all specs and their dependencies
            for spec in new_specs:
                get_(MatchSpec(spec).name, snames)
            if len(snames) < len(dists):
                limit = snames
                xtra = [dist for dist, rec in iteritems(dists) if rec['name'] not in snames]
                log.debug('Limiting solver to the following packages: %s', ', '.join(limit))
        if xtra:
            log.debug('Packages to be preserved: %s', xtra)
        return limit, xtra

    def restore_bad(self, pkgs, preserve):
        if preserve:
            sdict = {self.package_name(pkg): pkg for pkg in pkgs}
            pkgs.extend(p for p in preserve if self.package_name(p) not in sdict)

    def install_specs(self, specs, installed, update_deps=True):
        specs = list(map(MatchSpec, specs))
        snames = {s.name for s in specs}
        log.debug('Checking satisfiability of current install')
        limit, preserve = self.bad_installed(installed, specs)
        for pkg in installed:
            if pkg not in self.index:
                continue
            name, version, build, schannel = self.package_quad(pkg)
            if name in snames or limit is not None and name not in limit:
                continue
            # If update_deps=True, set the target package in MatchSpec so that
            # the solver can minimize the version change. If update_deps=False,
            # fix the version and build so that no change is possible.
            if update_deps:
                spec = MatchSpec('%s (target=%s)' % (name, pkg))
            else:
                spec = MatchSpec('%s %s %s' % (name, version, build))
            specs.append(spec)
        return specs, preserve

    def install(self, specs, installed=None, update_deps=True, returnall=False):
        # type: (List[str], Option[?], bool, bool) -> List[Dist]
        specs, preserve = self.install_specs(specs, installed or [], update_deps)
        pkgs = self.solve(specs, returnall=returnall)
        self.restore_bad(pkgs, preserve)
        return pkgs

    def remove_specs(self, specs, installed):
        # Adding ' @ @' to the MatchSpec forces its removal
        specs = [s if ' ' in s else s + ' @ @' for s in specs]
        specs = [MatchSpec(s, optional=True) for s in specs]
        snames = {s.name for s in specs}
        limit, _ = self.bad_installed(installed, specs)
        preserve = []
        for dist in installed:
            nm, ver, build, schannel = self.package_quad(dist)
            if nm in snames:
                continue
            elif limit is not None:
                preserve.append(dist)
            elif ver:
                specs.append(MatchSpec('%s >=%s' % (nm, ver), optional=True,
                                       target=dist.full_name))
            else:
                specs.append(MatchSpec(nm, optional=True, target=dist.full_name))
        return specs, preserve

    def remove(self, specs, installed):
        specs, preserve = self.remove_specs(specs, installed)
        pkgs = self.solve(specs)
        self.restore_bad(pkgs, preserve)
        return pkgs

    def solve(self, specs, returnall=False):
        # type: (List[str], bool) -> List[Dist]
        try:
            stdoutlog.info("Solving package specifications: ")
            log.debug("Solving for %s", specs)

            # Find the compliant packages
            len0 = len(specs)
            specs = list(map(MatchSpec, specs))
            reduced_index = self.get_reduced_index(specs)
            if not reduced_index:
                return False if reduced_index is None else ([[]] if returnall else [])

            # Check if satisfiable
            def mysat(specs, add_if=False):
                constraints = r2.generate_spec_constraints(C, specs)
                return C.sat(constraints, add_if)

            dotlog.debug('Checking satisfiability')
            r2 = Resolve(reduced_index, True, True)
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
            eq_optional_c = r2.generate_removal_count(C, speco)
            solution, obj7 = C.minimize(eq_optional_c, solution)
            log.debug('Package removal metric: %d', obj7)

            # Requested packages: maximize versions
            eq_req_v, eq_req_b = r2.generate_version_metrics(C, specr)
            solution, obj3 = C.minimize(eq_req_v, solution)
            log.debug('Initial package version metric: %d', obj3)

            # Track features: minimize feature count
            eq_feature_count = r2.generate_feature_count(C)
            solution, obj1 = C.minimize(eq_feature_count, solution)
            log.debug('Track feature count: %d', obj1)

            # Featured packages: maximize featured package count
            eq_feature_metric, ftotal = r2.generate_feature_metric(C)
            solution, obj2 = C.minimize(eq_feature_metric, solution)
            obj2 = ftotal - obj2
            log.debug('Package feature count: %d', obj2)

            # Requested packages: maximize builds
            solution, obj4 = C.minimize(eq_req_b, solution)
            log.debug('Initial package build metric: %d', obj4)

            # Dependencies: minimize the number of packages that need upgrading
            eq_u = r2.generate_update_count(C, speca)
            solution, obj50 = C.minimize(eq_u, solution)
            log.debug('Dependency update count: %d', obj50)

            # Remaining packages: maximize versions, then builds
            eq_v, eq_b = r2.generate_version_metrics(C, speca)
            solution, obj5 = C.minimize(eq_v, solution)
            solution, obj6 = C.minimize(eq_b, solution)
            log.debug('Additional package version/build metrics: %d/%d', obj5, obj6)

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
                stdoutlog.info(
                    '\nWarning: %s possible package resolutions '
                    '(only showing differing packages):%s%s' %
                    ('>10' if nsol > 10 else nsol,
                     dashlist(', '.join(diff) for diff in diffs),
                     '\n  ... and others' if nsol > 10 else ''))

            def stripfeat(sol):
                return sol.split('[')[0]
            stdoutlog.info('\n')

            if returnall:
                return [sorted(Dist(stripfeat(dname)) for dname in psol) for psol in psolutions]
            else:
                return sorted(Dist(stripfeat(dname)) for dname in psolutions[0])

        except:
            stdoutlog.info('\n')
            raise
