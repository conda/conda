from __future__ import print_function, division, absolute_import

import logging
from collections import defaultdict
from itertools import chain

from conda.compat import iterkeys, itervalues, iteritems, string_types
from conda.logic import minimal_unsatisfiable_subset, Clauses
from conda.version import VersionSpec, normalized_version
from conda.console import setup_handlers
from conda import config
from conda.toposort import toposort

log = logging.getLogger(__name__)
dotlog = logging.getLogger('dotupdate')
stdoutlog = logging.getLogger('stdoutlog')
stderrlog = logging.getLogger('stderrlog')
setup_handlers()


def dashlist(iter):
    return ''.join('\n  - ' + str(x) for x in iter)


class Unsatisfiable(RuntimeError):
    '''An exception to report unsatisfiable dependencies.

    Args:
        bad_deps: a list of tuples of objects (likely MatchSpecs).
        chains: (optional) if True, the tuples are interpreted as chains
            of dependencies, from top level to bottom. If False, the tuples
            are interpreted as simple lists of conflicting specs.

    Returns:
        Raises an exception with a formatted message detailing the
        unsatisfiable specifications.
    '''
    def __init__(self, bad_deps, chains=True):
        bad_deps = [map(str, dep) for dep in bad_deps]
        if chains:
            bad_deps = [' -> '.join(dep) for dep in bad_deps]
            msg = '''The following specifications were found to be in conflict:%s
Use "conda info <package>" to see the dependencies for each package.'''
        else:
            bad_deps = [', '.join(sorted(dep)) for dep in bad_deps]
            msg = '''The following specifications were found to be incompatible with the
others, or with the existing package set:%s
Use "conda info <package>" to see the dependencies for each package.'''
        msg = msg % dashlist(bad_deps)
        super(Unsatisfiable, self).__init__(msg)


class NoPackagesFound(RuntimeError):
    '''An exception to report that requested packages are missing.

    Args:
        bad_deps: a list of tuples of MatchSpecs, assumed to be dependency
        chains, from top level to bottom.

    Returns:
        Raises an exception with a formatted message detailing the
        missing packages and/or dependencies.
    '''
    def __init__(self, bad_deps):
        deps = set(q[-1].spec for q in bad_deps)
        if all(len(q) > 1 for q in bad_deps):
            what = "Dependencies" if len(bad_deps) > 1 else "Dependency"
        elif all(len(q) == 1 for q in bad_deps):
            what = "Packages" if len(bad_deps) > 1 else "Package"
        else:
            what = "Packages/dependencies"
        bad_deps = dashlist(' -> '.join(map(str, q)) for q in bad_deps)
        msg = ' % s missing in current %s channels: %s' % (what, config.subdir, bad_deps)
        super(NoPackagesFound, self).__init__(msg)
        self.pkgs = deps


class MatchSpec(object):
    def __new__(cls, spec, target=None, optional=False, negate=False, parent=None):
        if isinstance(spec, cls):
            return spec
        self = object.__new__(cls)
        self.spec = spec
        parts = spec.split()
        self.strictness = len(parts)
        assert 1 <= self.strictness <= 3, repr(spec)
        self.name = parts[0]
        if self.strictness == 2:
            self.vspecs = VersionSpec(parts[1])
        elif self.strictness == 3:
            self.ver_build = tuple(parts[1:3])
        self.target = target
        self.optional = optional
        self.negate = negate
        self.parent = parent
        return self

    def match_fast(self, version, build):
        if self.strictness == 1:
            res = True
        elif self.strictness == 2:
            res = self.vspecs.match(version)
        else:
            res = bool((version, build) == self.ver_build)
        return res != self.negate

    def match(self, info):
        if isinstance(info, string_types):
            name, version, build = info[:-8].rsplit('-', 2)
        else:
            name = info.get('name')
            version = info.get('version')
            build = info.get('build')
        if name != self.name:
            return False
        return self.match_fast(version, build)

    def to_filename(self):
        if self.strictness == 3 and not self.optional and not self.negate and not self.parent:
            return self.name + '-%s-%s.tar.bz2' % self.ver_build
        else:
            return None

    def __eq__(self, other):
        return type(other) is MatchSpec and self.spec == other.spec

    def __hash__(self):
        return hash((self.spec, self.negate))

    def __repr__(self):
        res = 'MatchSpec(' + repr(self.spec)
        if self.target:
            res += ',target=' + repr(self.target)
        if self.optional:
            res += ',optional=True'
        if self.negate:
            res += ',negate=True'
        return res + ')'

    def __str__(self):
        res = self.spec
        if self.target or self.optional or self.parent:
            mods = []
            if self.target:
                mods.append('target='+str(self.target))
            if self.parent:
                mods.append('parent='+str(self.parent))
            if self.optional:
                mods.append('optional')
            if self.negate:
                mods.append('negate')
            res += ' (' + ', '.join(mods) + ')'
        return res


class Package(object):
    """
    The only purpose of this class is to provide package objects which
    are sortable.
    """
    def __init__(self, fn, info):
        self.fn = fn
        self.name = info.get('name')
        self.version = info.get('version')
        self.build = info.get('build')
        self.build_number = info.get('build_number')
        self.channel = info.get('channel')
        try:
            self.norm_version = normalized_version(self.version)
        except ValueError:
            stderrlog.error("\nThe following stack trace is in reference to "
                            "package:\n\n\t%s\n\n" % fn)
            raise
        self.info = info

    def _asdict(self):
        result = self.info.copy()
        result['fn'] = self.fn
        result['norm_version'] = str(self.norm_version)
        return result

    def __lt__(self, other):
        if self.name != other.name:
            raise TypeError('cannot compare packages with different '
                            'names: %r %r' % (self.fn, other.fn))
        return ((self.norm_version, self.build_number, self.build) <
                (other.norm_version, other.build_number, other.build))

    def __eq__(self, other):
        if not isinstance(other, Package):
            return False
        if self.name != other.name:
            return False
        return ((self.norm_version, self.build_number, self.build) ==
                (other.norm_version, other.build_number, other.build))

    def __ne__(self, other):
        return not self == other

    def __gt__(self, other):
        return other < self

    def __le__(self, other):
        return not (other < self)

    def __ge__(self, other):
        return not (self < other)


def build_groups(index):
    groups = {}
    trackers = {}
    for fn, info in iteritems(index):
        groups.setdefault(info['name'], []).append(fn)
        for feat in info.get('track_features', '').split():
            trackers.setdefault(feat, []).append(fn)
    return groups, trackers


class Resolve(object):
    def __init__(self, index):
        self.index = index.copy()
        for fn, info in iteritems(index):
            for fstr in chain(info.get('features', '').split(),
                              info.get('track_features', '').split()):
                fpkg = fstr + '@'
                if fpkg not in self.index:
                    self.index[fpkg] = {
                        'name': fpkg, 'version': '0', 'build_number': 0,
                        'build': '', 'depends': [], 'track_features': fstr}
            for fstr in iterkeys(info.get('with_features_depends', {})):
                fn2 = fn + '[' + fstr + ']'
                self.index[fn2] = info
        self.groups, self.trackers = build_groups(self.index)
        self.find_matches_ = {}
        self.ms_depends_ = {}

    def default_filter(self, features=None, filter=None):
        if filter is None:
            filter = {}
        else:
            filter.clear()
        filter.update({fstr+'@': False for fstr in iterkeys(self.trackers)})
        if features:
            filter.update({fstr+'@': True for fstr in features})
        return filter

    def valid(self, spec, filter):
        """Tests if a package, MatchSpec, or a list of both has satisfiable
        dependencies, assuming cyclic dependencies are always valid.

        Args:
            fn: a package key, a MatchSpec, or an iterable of these.
            filter: a dictionary of (fn,valid) pairs, used to consider a subset
                of dependencies, and to eliminate repeated searches.

        Returns:
            True if the full set of dependencies can be satisfied; False otherwise.
            If filter is supplied and update is True, it will be updated with the
            search results.
        """
        def v_(spec):
            return v_ms_(spec) if isinstance(spec, MatchSpec) else v_fn_(spec)

        def v_ms_(ms):
            return ms.optional or any(v_fn_(fn) for fn in self.find_matches(ms))

        def v_fn_(fn):
            val = filter.get(fn)
            if val is None:
                filter[fn] = True
                val = filter[fn] = all(v_ms_(ms) for ms in self.ms_depends(fn))
            return val

        return v_(spec)

    def touch(self, spec, touched, filter):
        """Determines a conservative set of packages to be considered given a
           package, or a spec, or a list thereof. Cyclic dependencies are not
           solved, so there is no guarantee a solution exists.

        Args:
            fn: a package key or MatchSpec
            touched: a dict into which to accumulate the result. This is
                useful when processing multiple specs.
            filter: a dictionary of (fn,valid) pairs to be used when
                testing for package validity.

        This function works in two passes. First, it verifies that the package has
        satisfiable dependencies from among the filtered packages. If not, then it
        is _not_ touched, nor are its dependencies. If so, then it is marked as
        touched, and any of its valid dependencies are as well.
        """
        def t_fn_(fn):
            val = touched.get(fn)
            if val is None:
                val = touched[fn] = self.valid(fn, filter)
                if val:
                    for ms in self.ms_depends(fn):
                        if ms.name[0] != '@':
                            t_ms_(ms)

        def t_ms_(ms):
            for fn in self.find_matches(ms):
                t_fn_(fn)

        return t_ms_(spec) if isinstance(spec, MatchSpec) else t_fn_(spec)

    def invalid_chains(self, spec, filter):
        """Constructs a set of 'dependency chains' for invalid specs.

        A dependency chain is a tuple of MatchSpec objects, starting with
        the requested spec, proceeding down the dependency tree, ending at
        a specification that cannot be satisfied. Uses self.valid_ as a
        filter, both to prevent chains and to allow other routines to
        prune the list of valid packages with additional criteria.

        Args:
            spec: a package key or MatchSpec
            filter: a dictionary of (fn,valid) pairs to be used when
                testing for package validity.

        Returns:
            A list of tuples, or an empty list if the MatchSpec is valid.
        """
        def chains_(spec, top=None):
            if spec.name == top or self.valid(spec, filter):
                return []
            notfound = set()
            specs = self.find_matches(spec) if isinstance(spec, MatchSpec) else [spec]
            for fn in specs:
                for m2 in self.ms_depends(fn):
                    notfound.update(chains_(m2))
            return [(spec,) + x for x in notfound] if notfound else [(spec,)]
        return chains_(spec)

    def verify_specs(self, specs):
        """Perform a quick verification that specs and dependencies are reasonable.

        Args:
            specs: An iterable of strings or MatchSpec objects to be tested.

        Returns:
            Nothing, but if there is a conflict, an error is thrown.

        Note that this does not attempt to resolve circular dependencies.
        """
        bad_deps = []
        opts = []
        rems = []
        spec2 = []
        feats = set()
        for s in specs:
            ms = MatchSpec(s)
            if ms.name[-1] == '@':
                feats.add(ms.name[:-1])
                continue
            if ms.negate:
                rems.append(MatchSpec(ms.spec))
            if not ms.optional:
                spec2.append(ms)
            elif any(self.find_matches(ms)):
                opts.append(ms)
        for ms in spec2:
            filter = self.default_filter(feats)
            if not self.valid(ms, filter):
                bad_deps.extend(self.invalid_chains(ms, filter))
        if bad_deps:
            raise NoPackagesFound(bad_deps)
        return spec2, rems, opts, feats

    def get_dists(self, specs):
        log.debug('Retrieving packages for: %s' % specs)

        specs, removes, optional, features = self.verify_specs(specs)
        filter = {}
        touched = {}
        snames = set()
        unsat = []

        def filter_group(matches, chains=None):
            # If we are here, then this dependency is mandatory,
            # so add it to the master list. That way it is still
            # participates in the pruning even if one of its
            # parents is pruned away
            match1 = next(ms for ms in matches)
            name = match1.name
            first = name not in snames
            group = self.groups.get(name, [])

            # Prune packages that don't match any of the patterns
            # or which have unsatisfiable dependencies
            nold = 0
            bad_deps = []
            for fn in group:
                if filter.setdefault(fn, True):
                    nold += 1
                    sat = self.match_any(matches, fn)
                    sat = sat and all(any(filter.get(f2, True) for f2 in self.find_matches(ms))
                                      for ms in self.ms_depends(fn) if not ms.optional)
                    filter[fn] = sat
                    if not sat:
                        bad_deps.append(fn)

            # Build dependency chains if we detect unsatisfiability
            nnew = nold - len(bad_deps)
            reduced = nnew < nold
            if reduced:
                log.debug(' % s: pruned from %d -> %d' % (name, nold, nnew))
            if nnew == 0:
                if name in snames:
                    snames.remove(name)
                if not all(ms.optional for ms in matches):
                    bad_deps = [fn for fn in bad_deps if self.match_any(matches, fn)]
                    matches = [(ms,) for ms in matches]
                    chains = [a + b for a in chains for b in matches] if chains else matches
                    if bad_deps:
                        dep2 = set()
                        for fn in bad_deps:
                            for ms in self.ms_depends(fn):
                                if not any(filter.get(f2, True) for f2 in self.find_matches(ms)):
                                    dep2.add(ms)
                        chains = [a + (b,) for a in chains for b in dep2]
                    unsat.extend(chains)
                    return nnew
            if not reduced and not first:
                return False

            # Perform the same filtering steps on any dependencies shared across
            # *all* packages in the group. Even if just one of the packages does
            # not have a particular dependency, it must be ignored in this pass.
            snames.add(name)
            cdeps = defaultdict(list)
            for fn in group:
                if filter[fn]:
                    for m2 in self.ms_depends(fn):
                        if m2.name[0] != '@' and not m2.optional:
                            cdeps[m2.name].append(m2)
            cdeps = {mname: set(deps) for mname, deps in iteritems(cdeps) if len(deps) == nnew}
            if cdeps:
                matches = [(ms,) for ms in matches]
                if chains:
                    matches = [a + b for a in chains for b in matches]
                if sum(filter_group(deps, chains) for deps in itervalues(cdeps)):
                    reduced = True

            return reduced

        # Iterate in the filtering process until no more progress is made
        def full_prune(specs, removes, optional, features):
            self.default_filter(features, filter)
            for ms in removes:
                for fn in self.find_matches(ms):
                    filter[fn] = False
            feats = set(self.trackers.keys())
            snames.clear()
            slist = specs
            for iter in range(10):
                first = True
                while sum(filter_group([s]) for s in slist):
                    slist = list(map(MatchSpec, snames))
                    first = False
                if unsat:
                    return False
                if first and iter:
                    return True
                touched.clear()
                for fstr in features:
                    touched[fstr+'@'] = True
                for spec in chain(specs, optional):
                    self.touch(spec, touched, filter)
                nfeats = set()
                for fn, val in iteritems(touched):
                    if val:
                        nfeats.update(self.track_features(fn))
                if len(nfeats) >= len(feats):
                    return True
                pruned = False
                feats &= nfeats
                for fn, val in iteritems(touched):
                    if val and self.features(fn) - feats:
                        touched[fn] = filter[fn] = False
                        filter[fn] = False
                        pruned = True
                if not pruned:
                    return True

        #
        # In the case of a conflict, look for the minimum satisfiable subset
        #

        if not full_prune(specs, removes, optional, features):
            def minsat_prune(specs):
                return full_prune(specs, removes, [], features)

            save_unsat = set(unsat)
            stderrlog.info('\nError: Unsatisfiable package specifications.\nGenerating hint: \n')
            hint = minimal_unsatisfiable_subset(specs, sat=minsat_prune, log=True)
            save_unsat.update((ms,) for ms in hint if all(ms != c[0] for c in save_unsat))
            raise Unsatisfiable(save_unsat)

        dists = {fn: self.index[fn] for fn, val in iteritems(touched) if val}
        return dists, list(map(MatchSpec, snames - {ms.name for ms in specs}))

    def match_any(self, mss, fn):
        rec = self.index[fn]
        n, v, b = rec['name'], rec['version'], rec['build']
        return any(n == ms.name and ms.match_fast(v, b) for ms in mss)

    def match(self, ms, fn):
        return ms.match(self.index[fn])

    def find_matches_group(self, ms, groups, trackers=None):
        ms = MatchSpec(ms)
        if ms.name[0] == '@' and trackers:
            for fn in trackers.get(ms.name[1:], []):
                yield fn
        else:
            for fn in groups.get(ms.name, []):
                rec = self.index[fn]
                if ms.match_fast(rec['version'], rec['build']):
                    yield fn

    def find_matches(self, ms):
        ms = MatchSpec(ms)
        res = self.find_matches_.get(ms, None)
        if res is None:
            if ms.name[0] == '@':
                res = self.find_matches_[ms] = self.trackers.get(ms.name[1:], [])
            else:
                res = self.find_matches_[ms] = list(self.find_matches_group(ms, self.groups))
        return res

    def ms_depends(self, fn):
        deps = self.ms_depends_.get(fn, None)
        if deps is None:
            if fn[-1] == ']':
                fn2, fstr = fn[:-1].split('[')
                fdeps = {d.name: d for d in self.ms_depends(fn2)}
                for dep in self.index[fn2]['with_features_depends'][fstr]:
                    dep = MatchSpec(dep)
                    fdeps[dep.name] = dep
                deps = list(fdeps.values())
            else:
                deps = [MatchSpec(d) for d in self.index[fn].get('depends', [])]
            deps.extend(MatchSpec('@'+feat) for feat in self.features(fn))
            self.ms_depends_[fn] = deps
        return deps

    def version_key(self, fn, majoronly=False):
        rec = self.index[fn]
        if majoronly:
            return normalized_version(rec['version'])
        else:
            return (normalized_version(rec['version']), rec['build_number'])

    def features(self, fn):
        return set(self.index[fn].get('features', '').split())

    def track_features(self, fn):
        return set(self.index[fn].get('track_features', '').split())

    def package_triple(self, fn):
        if not fn.endswith('.tar.bz2'):
            return self.package_triple(fn + '.tar.bz2')
        rec = self.index.get(fn, None)
        if rec is None:
            return fn[:-8].rsplit('-', 2)
        return (rec['name'], rec['version'], rec['build'])

    def package_name(self, fn):
        return self.package_triple(fn)[0]

    def get_pkgs(self, ms, emptyok=False):
        ms = MatchSpec(ms)
        pkgs = [Package(fn, self.index[fn]) for fn in self.find_matches(ms)]
        if not pkgs and not emptyok:
            raise NoPackagesFound([(ms,)])
        return pkgs

    @staticmethod
    def ms_to_v(ms):
        return '@s@' + ms.spec + ('!' if ms.negate else '')

    @staticmethod
    def feat_to_v(feat):
        return '@s@@' + feat

    def gen_clauses(self, groups, trackers, specs):
        C = Clauses()

        def push_MatchSpec(ms):
            name = self.ms_to_v(ms)
            m = C.from_name(name)
            if m is None:
                m = C.Any(self.find_matches_group(ms, groups, trackers), name=name)
            return m

        # Create package variables
        for group in itervalues(groups):
            for fn in group:
                C.new_var(fn)

        # Create feature variables
        for name in iterkeys(trackers):
            push_MatchSpec(MatchSpec('@' + name))

        # Create spec variables
        for ms in specs:
            push_MatchSpec(ms)

        # Add dependency relationships
        for group in itervalues(groups):
            for fn in group:
                for ms in self.ms_depends(fn):
                    if not ms.optional:
                        C.Require(C.Or, C.Not(fn), push_MatchSpec(ms), polarity=None)
            C.Require(C.AtMostOne, group)

        return C

    def generate_spec_constraints(self, C, specs):
        return [(self.ms_to_v(ms),) for ms in specs if not ms.optional]

    def generate_feature_count(self, C, trackers):
        return {self.feat_to_v(name): 1 for name in iterkeys(trackers)}

    def generate_feature_metric(self, C, groups, specs):
        eq = {}
        for name, group in iteritems(groups):
            nf = [len(self.features(fn)) for fn in group]
            maxf = max(nf)
            if min(nf) == maxf:
                continue
            if not any(ms.name == name for ms in specs if not ms.optional):
                maxf += 1
            eq.update({fn: maxf-fc for fn, fc in zip(group, nf) if fc < maxf})
        return eq

    def generate_removal_count(self, C, specs):
        return {'!'+self.ms_to_v(ms): 1 for ms in specs}

    def generate_version_metric(self, C, groups, specs, majoronly=False):
        eq = {}
        sdict = {}
        for s in specs:
            s = MatchSpec(s)  # needed for testing
            sdict.setdefault(s.name, []).append(s)
        key = lambda x: self.version_key(x, majoronly)
        for name, mss in iteritems(sdict):
            pkgs = [(key(p), p) for p in groups.get(name, [])]
            # If the "target" field in the MatchSpec is supplied, that means we want
            # to minimize the changes to the currently installed package. We prefer
            # any upgrade over any downgrade, but beyond that we want minimal change.
            targets = [ms.target for ms in mss if ms.target]
            if targets:
                v1 = sorted(((key(t), t) for t in targets), reverse=True)
                v2 = sorted((p for p in pkgs if p > v1[0]))
                v3 = sorted((p for p in pkgs if p < v1[0]), reverse=True)
                pkgs = v1 + v2 + v3
            else:
                pkgs = sorted(pkgs, reverse=True)
            i = 0
            prev = None
            for nkey, pkg in pkgs:
                if prev and prev != nkey:
                    i += 1
                if i:
                    eq[pkg] = i
                prev = nkey
        return eq

    def generate_package_count(self, C, groups, specs):
        eq = {}
        snames = {s.name for s in map(MatchSpec, specs)}
        for name, pkgs in iteritems(groups):
            if name in snames:
                continue
            pkg_ver = sorted([(self.version_key(p), p)
                             for p in groups.get(name, [])], reverse=True)
            i = 1
            prev = None
            for nkey, pkg in pkg_ver:
                if prev and prev != nkey:
                    i += 1
                eq[pkg] = i
                prev = nkey
        return eq

    def dependency_sort(self, must_have):
        def lookup(value):
            return set(ms.name for ms in self.ms_depends(value + '.tar.bz2'))
        digraph = {}
        for key, value in iteritems(must_have):
            depends = lookup(value)
            digraph[key] = depends
        sorted_keys = toposort(digraph)
        must_have = must_have.copy()
        # Take all of the items in the sorted keys
        # Don't fail if the key does not exist
        result = [must_have.pop(key) for key in sorted_keys if key in must_have]
        # Take any key that were not sorted
        result.extend(must_have.values())
        return result

    # name deprecated; use dependency_sort instead
    def graph_sort(self, must_have):
        return self.dependency_sort(must_have)

    def explicit(self, specs):
        """
        Given the specifications, return:
          A. if one explicit specification (strictness=3) is given, and
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
            if fn not in self.index:
                return None
            res = [ms2.to_filename() for ms2 in self.ms_depends(fn)]
            res.append(fn)
        else:
            res = [spec.to_filename() for spec in specs if str(spec) != 'conda']

        if None in res:
            return None
        res.sort()
        dotlog.debug('explicit(%r) finished' % specs)
        return res

    def sum_matches(self, fn1, fn2):
        return sum(self.match(ms, fn2) for ms in self.ms_depends(fn1))

    def find_substitute(self, installed, features, fn):
        """
        Find a substitute package for `fn` (given `installed` packages)
        which does *NOT* have `features`.  If found, the substitute will
        have the same package name and version and its dependencies will
        match the installed packages as closely as possible.
        If no substitute is found, None is returned.
        """
        name, version, unused_build = fn.rsplit('-', 2)
        candidates = {}
        for pkg in self.get_pkgs(MatchSpec(name + ' ' + version)):
            fn1 = pkg.fn
            if self.features(fn1).intersection(features):
                continue
            key = sum(self.sum_matches(fn1, fn2) for fn2 in installed)
            candidates[key] = fn1

        if candidates:
            maxkey = max(candidates)
            return candidates[maxkey]
        else:
            return None

    def bad_installed(self, installed):
        if not installed:
            return []
        dists = {fn: self.index[fn] for fn in installed}
        specs = [MatchSpec(' % s %s %s' % (rec['name'], rec['version'], rec['build']))
                 for rec in itervalues(dists)]
        groups, trackers = build_groups(dists)
        C = self.gen_clauses(groups, trackers, specs)
        constraints = self.generate_spec_constraints(C, specs)
        solution = C.sat(constraints)
        if solution:
            return []
        solution = [C.Not(q) for q in range(1, C.m+1)]
        eq_removal_count = self.generate_removal_count(C, specs)
        solution, obj1 = C.minimize(eq_removal_count, solution)
        solution = set(solution)
        return set(s.name for s in specs if C.from_name(self.ms_to_v(s)) not in solution)

    def restore_bad(self, pkgs, preserve):
        if preserve:
            sdict = {self.package_name(pkg): pkg for pkg in pkgs}
            pkgs.extend(p for p in preserve if self.package_name(p) not in sdict)

    def install_specs(self, specs, installed, update_deps=True):
        specs = list(map(MatchSpec, specs))
        snames = {s.name for s in specs}
        log.debug('Checking satisfiability of current install')
        bad_specs = self.bad_installed(installed)
        preserve = []
        for pkg in installed:
            assert pkg in self.index
            name, version, build = self.package_triple(pkg)
            if name in snames:
                continue
            # If update_deps=True, set the target package in MatchSpec so that
            # the solver can minimize the version change. If update_deps=False,
            # fix the version and build so that no change is possible.
            need_help = name in bad_specs
            if need_help:
                preserve.append(pkg)
            if update_deps or need_help:
                spec = MatchSpec(name, target=pkg, optional=need_help)
            else:
                spec = MatchSpec(' % s %s %s' % (name, version, build))
            specs.append(spec)
        return specs, bad_specs

    def install(self, specs, installed=[], update_deps=True, returnall=False):
        len0 = len(specs)
        specs, preserve = self.install_specs(specs, installed, update_deps)
        pkgs = self.solve(specs, len0=len0, returnall=returnall)
        self.restore_bad(pkgs, preserve)
        return pkgs

    def remove_specs(self, specs, installed):
        specs = [MatchSpec(s, optional=True, negate=True) for s in specs]
        snames = {s.name for s in specs}
        bad_specs = self.bad_installed(installed)
        preserve = []
        for pkg in installed:
            assert pkg in self.index
            name, version, build = self.package_triple(pkg)
            if name in bad_specs and name not in snames:
                preserve.append(pkg)
            if name not in snames:
                specs.append(MatchSpec(name, optional=True, target=pkg))
        return specs, preserve

    def remove(self, specs, installed):
        specs, preserve = self.remove_specs(specs, installed)
        pkgs = self.solve(specs)
        self.restore_bad(pkgs, preserve)
        return pkgs

    def solve(self, specs, len0=None, returnall=False):
        try:
            stdoutlog.info("Solving package specifications: ")
            dotlog.debug("Solving for %s" % specs)

            # Find the compliant packages
            specs = list(map(MatchSpec, specs))
            if len0 is None:
                len0 = len(specs)
            dists, new_specs = self.get_dists(specs)
            if not dists:
                return False if dists is None else ([[]] if returnall else [])

            # Clear out our caches to reduce memory usage before the solve
            self.find_matches_.clear()
            self.ms_depends_.clear()

            # Check if satisfiable
            dotlog.debug('Checking satisfiability')
            groups, trackers = build_groups(dists)
            C = self.gen_clauses(groups, trackers, specs)
            constraints = self.generate_spec_constraints(C, specs)
            solution = C.sat(constraints, True)
            if not solution:
                # Find the largest set of specs that are satisfiable, and return
                # the list of specs that are not in that set.
                solution = [C.Not(q) for q in range(1, C.m+1)]
                spec2 = [s for s in specs if not s.optional]
                eq_removal_count = self.generate_removal_count(C, spec2)
                solution, obj1 = C.minimize(eq_removal_count, solution)
                specsol = [(s,) for s in spec2 if C.from_name(self.ms_to_v(s)) not in solution]
                raise Unsatisfiable(specsol, False)

            spec2 = [s for s in specs[:len0] if not s.optional]
            eq_requested_versions = self.generate_version_metric(C, groups, spec2, majoronly=True)
            solution, obj1 = C.minimize(eq_requested_versions, solution)
            dotlog.debug('Requested version metric: %d' % obj1)

            specs = [s for s in chain(specs, new_specs) if not s.optional or
                     any(self.find_matches_group(s, groups, trackers))]
            spec3 = [s for s in specs if s.optional]
            eq_optional_count = self.generate_removal_count(C, spec3)
            solution, obj2 = C.minimize(eq_optional_count, solution)
            dotlog.debug('Optional package removal count: %d' % obj2)

            eq_optional_versions = self.generate_version_metric(C, groups, spec3, majoronly=True)
            solution, obj3 = C.minimize(eq_optional_versions, solution)
            dotlog.debug('Optional package version metric: %d' % obj3)

            eq_feature_count = self.generate_feature_count(C, trackers)
            solution, obj4 = C.minimize(eq_feature_count, solution)
            dotlog.debug('Feature count metric: %d' % obj4)

            eq_feature_metric = self.generate_feature_metric(C, groups, specs)
            solution, obj5 = C.minimize(eq_feature_metric, solution)
            dotlog.debug('Feature package metric: %d' % obj5)

            eq_all_versions = self.generate_version_metric(C, groups, specs, majoronly=False)
            solution, obj6 = C.minimize(eq_all_versions, solution)
            dotlog.debug('Total version metric: %d' % obj6)

            eq_package_count = self.generate_package_count(C, groups, specs)
            solution, obj7 = C.minimize(eq_package_count, solution)
            dotlog.debug('Weak dependency metric: %d' % obj7)

            dotlog.debug('Looking for alternate solutions')

            def clean(sol):
                return [q for q in (C.from_index(s) for s in sol)
                        if q and q[0] != '!' and '@' not in q]

            def renumerate(sol):
                return [C.from_name(q) for q in sol]

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
                    dotlog.debug('Too many solutions; terminating')
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

            if obj6 > 0:
                log.debug("Older versions in the solution(s):")
                for sol in psolutions:
                    log.debug([(i, p) for i, p in iteritems(eq_all_versions) if p in sol])
            stdoutlog.info('\n')
            return list(map(sorted, psolutions)) if returnall else sorted(psolutions[0])
        except:
            stdoutlog.info('\n')
            raise
