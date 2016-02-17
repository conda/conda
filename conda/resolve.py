from __future__ import print_function, division, absolute_import

import sys
import logging
from collections import defaultdict
from itertools import chain

from conda.compat import iterkeys, itervalues, iteritems, string_types
from conda.logic import sat, optimize, minimal_unsatisfiable_subset
from conda.version import VersionOrder, VersionSpec
from conda.console import setup_handlers
from conda import config
from conda.toposort import toposort

log = logging.getLogger(__name__)
dotlog = logging.getLogger('dotupdate')
stdoutlog = logging.getLogger('stdoutlog')
stderrlog = logging.getLogger('stderrlog')
setup_handlers()

# normalized_version() is needed by conda-env
# We could just import it from resolve but pyflakes would complain
def normalized_version(version):
    return VersionOrder(version)

def dashlist(iter):
    return ''.join('\n  - ' + str(x) for x in iter)

class Unsatisfiable(RuntimeError):
    def __init__(self, bad_deps):
        bad_deps = dashlist([' -> '.join(map(str,c)) for c in bad_deps])
        msg = '''The following specifications were found to be in conflict:%s
Use "conda info <package>" to see the dependencies for each package.'''%bad_deps
        super(Unsatisfiable, self).__init__(msg)

class NoPackagesFound(RuntimeError):
    def __init__(self, bad_deps):
        deps = set(q[-1].spec for q in bad_deps)
        if all(len(q) > 1 for q in bad_deps):
            what = "Dependencies" if len(bad_deps)>1 else "Dependency"
        elif all(len(q) == 1 for q in bad_deps):
            what = "Packages" if len(bad_deps)>1 else "Package"
        else:
            what = "Packages/dependencies"
        bad_deps = dashlist(' -> '.join(map(str,q)) for q in bad_deps)
        msg ='%s missing in current %s channels: %s'%(what, config.subdir, bad_deps)
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
            name, version, build = info[:-8].rsplit('-',2)
        else:
            if isinstance(info, Package):
                info = info.info
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
        return hash((self.spec,self.negate))

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
        if res[-1] == '@' and self.strictness == 1:
            res = 'feature "%s"'%res[1:]
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
            res += ' (' + ','.join(mods) + ')'
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
        if not (self.name and self.version and self.build):
            self.name, self.version, self.build = fn.rsplit('-',2)
        self.build_number = info.get('build_number')
        self.channel = info.get('channel')
        self.norm_version = VersionOrder(self.version)
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

    def __repr__(self):
        return '<Package %s>' % self.fn

def build_groups(index):
    groups = {}
    trackers = {}
    for fn, info in iteritems(index):
        groups.setdefault(info['name'],[]).append(fn)
        for feat in info.get('track_features','').split():
            trackers.setdefault(feat,[]).append(fn)
    return groups, trackers

class Resolve(object):

    def __init__(self, index):
        self.index = index.copy()
        for fn, info in iteritems(index):
            for fstr in chain(info.get('features','').split(),info.get('track_features','').split()):
                fpkg = fstr + '@'
                if fpkg not in self.index:
                    self.index[fpkg] = {
                        'name':fpkg, 'version':'0', 'build_number':0,
                        'build':'', 'depends':[], 'track_features':fstr }
            for fstr in iterkeys(info.get('with_features_depends',{})):
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
        filter.update({fstr+'@':False for fstr in iterkeys(self.trackers)})
        if features:
            filter.update({fstr+'@':True for fstr in features})
        return filter

    def valid(self, spec, filter=None, features=None):
        """Tests if a package, MatchSpec, or a list of both has satisfiable 
        dependencies, assuming cyclic dependencies are always valid.

        Args:
            fn: a package key, a MatchSpec, or an iterable of these.
            features (optional): an iterable of active track_feature strings.
            filter (optional): a dictionary of (fn,valid) pairs. If supplied, this
                filter will be used to consider only a subset of dependencies. It
                also supercedes the features argument, as it will be assumed that
                the filter already includes the active feature information.

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
        if filter is None:
            filter = self.default_filter(features)
        return v_(spec)

    def touch(self, spec, touched, filter=None, features=None):
        """Determines a conservative set of packages to be considered given a
           package, or a spec, or a list thereof. Cyclic dependencies are not
           solved, so there is no guarantee a solution exists.

        Args:
            fn: a package key or MatchSpec
            touched: a dict into which to accumulate the result. This is
                useful when processing multiple specs.
            filter (optional): a dictionary of (fn,valid) pairs to be used when
                testing for package validity. This can be prepopulated with values
                from a pruning process. If not supplied, a default filter is created.
            features (optional): a list of features to assume are activated, 
                regardless of the track_features touched by the packages. This is
                ignored if filter is supplied, because it is assumed that any
                hardcoded features are already built into the filter.

        This function works in two passes. First, it verifies that the package has
        satisfiable dependencies from among the filtered packages. If not, then it
        is _not_ touched, nor are its dependencies. If so, then it is marked as 
        touched, and any of its valid dependencies are as well.
        """
        def t_fn_(fn):
            val = touched.get(fn)
            if val is None:
                val = touched[fn] = self.valid(fn, filter=filter)
                if val:
                    for ms in self.ms_depends(fn):
                        if ms.name[0] != '@':
                            t_ms_(ms)
        def t_ms_(ms):
            for fn in self.find_matches(ms):
                t_fn_(fn)
        if filter is None:
            filter = self.default_filter(features)
        return t_ms_(spec) if isinstance(spec, MatchSpec) else t_fn_(spec)

    def invalid_chains(self, spec, filter=None, features=None):
        """Constructs a set of 'dependency chains' for invalid specs.

        A dependency chain is a tuple of MatchSpec objects, starting with
        the requested spec, proceeding down the dependency tree, ending at
        a specification that cannot be satisfied. Uses self.valid_ as a
        filter, both to prevent chains and to allow other routines to
        prune the list of valid packages with additional criteria.

        Args:
            spec: a package key or MatchSpec
            filter (optional): a dictionary of (fn,valid) pairs to be used when
                testing for package validity. This can be prepopulated with values
                from a pruning process. If not supplied, a blank dictionary is used.
                If it is supplied, the features argument is ignored, because it is
                assumed that the filter has already been populated with them.
            features (optional): an iterable of active track_features.

        Returns:
            A list of tuples, or an empty list if the MatchSpec is valid.
        """
        if filter is None:
            filter = self.default_filter(features)
        def chains_(spec, top=None):
            if spec.name==top or self.valid(spec, filter=filter):
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
            bad_deps.extend(self.invalid_chains(ms, features=feats))
        if bad_deps:
            raise NoPackagesFound(bad_deps)
        return spec2, rems, opts, feats

    def verify_consistency(self, installed):
        """Verifies that the given install list is consistent; that is, that
        the dependencies are satisfied for all packages.

        Args:
            installed: An iterable of package keys.

        Returns:
            True if the packages are consistent with the dependencies, and
            False if they are not.
        """
        r = Resolve({fn:self.index[fn] for fn in installed if fn in self.index})
        return r.valid_specs(r.groups.keys())

    def get_dists(self, specs, sat_only=False):
        log.debug('Retrieving packages for: %s'%specs)

        try:
            specs, removes, optional, features = self.verify_specs(specs)
        except:
            if sat_only:
                return None, None
            raise
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
                log.debug('%s: pruned from %d -> %d' % (name, nold, nnew))
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
            cdeps = {mname:set(deps) for mname,deps in iteritems(cdeps) if len(deps)==nnew}
            if cdeps:
                matches = [(ms,) for ms in matches]
                if chains:
                    matches = [a + b for a in chains for b in matches]
                if sum(filter_group(deps, chains) for deps in itervalues(cdeps)):
                    reduced = True

            return reduced

        # Iterate in the filtering process until no more progress is made
        def full_prune(specs, removes, optional, features):
            self.default_filter(features, filter=filter)
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
                    self.touch(spec, touched, filter=filter)
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

        res = full_prune(specs, removes, optional, features)
        if sat_only:
            return res
        if not res:
            save_unsat = set(unsat)
            def minsat_prune(specs):
                return full_prune(specs, removes, [], features)
            stderrlog.info('\nError: Unsatisfiable package specifications.\nGenerating hint: \n')
            hint = minimal_unsatisfiable_subset(specs, sat=minsat_prune, log=True)
            save_unsat.update((ms,) for ms in hint if all(ms != c[0] for c in save_unsat))
            raise Unsatisfiable(save_unsat)

        dists = {fn:self.index[fn] for fn, val in iteritems(touched) if val}
        return dists, list(map(MatchSpec,snames - {ms.name for ms in specs}))

    def match_any(self, mss, fn):
        rec = self.index[fn]
        n, v, b = rec['name'], rec['version'], rec['build']
        return any(n == ms.name and ms.match_fast(v, b) for ms in mss)

    def match(self, ms, fn):
        if fn[-1] == ']':
            fn = fn.rsplit('[',1)[0]
        if ms.name[-1] == '@':
            return ms.name[:-1] in self.track_features(fn)
        return ms.match(self.index[fn])

    def find_matches_group(self, ms, groups):
        ms = MatchSpec(ms)
        for fn in groups.get(ms.name, []):
            rec = self.index[fn]
            if ms.match_fast(rec['version'], rec['build']):
                yield fn

    def find_matches(self, ms):
        ms = MatchSpec(ms)
        res = self.find_matches_.get(ms, None)
        if res is None:
            if ms.name[0] == '@':
                res = self.find_matches_[ms] = self.trackers.get(ms.name[1:],[])
            else:
                res = self.find_matches_[ms] = list(self.find_matches_group(ms, self.groups))
        return res

    def ms_depends(self, fn):
        deps = self.ms_depends_.get(fn,None)
        if deps is None:
            if fn[-1] == ']':
                fn2, fstr = fn[:-1].split('[')
                fdeps = {d.name:d for d in self.ms_depends(fn2)}
                for dep in self.index[fn2]['with_features_depends'][fstr]:
                    dep = MatchSpec(dep)
                    fdeps[dep.name] = dep
                deps = list(fdeps.values())
            else:
                deps = [MatchSpec(d) for d in self.index[fn].get('depends',[])]
            deps.extend(MatchSpec('@'+feat) for feat in self.features(fn))
            self.ms_depends_[fn] = deps
        return deps

    def version_key(self, fn, majoronly=False):
        rec = self.index[fn]
        if majoronly:
            return VersionOrder(rec['version'])
        else:
            return (VersionOrder(rec['version']), rec['build_number'])

    def features(self, fn):
        return set(self.index[fn].get('features', '').split())

    def track_features(self, fn):
        return set(self.index[fn].get('track_features', '').split())

    def package_triple(self, fn):
        if not fn.endswith('.tar.bz2'):
            return self.package_triple(fn + '.tar.bz2')
        rec = self.index.get(fn, None)
        if rec is not None:
            return (rec['name'], rec['version'], rec['build'])
        return fn[:-8].rsplit('-',2)

    def package_name(self, fn):
        return self.package_triple(fn)[0]

    def get_pkgs(self, ms, emptyok=False):
        ms = MatchSpec(ms)
        pkgs = [Package(fn, self.index[fn]) for fn in self.find_matches(ms)]
        if not pkgs and not emptyok:
            raise NoPackagesFound([(ms,)])
        return pkgs

    def gen_clauses(self, v, groups, features, specs, relax=False):
        # Hardcoded features are always true
        for name, group in iteritems(features):
            name = '@' + name
            # feat@ == fn1 OR fn2 OR fn3 OR fn4)
            # If the track feature is active, at least one of its
            # packages must be installed
            yield tuple([-v[name]] + [v[fn] for fn in group])
            # If the track feature is not installed, none of its
            # packages may be installed
            for fn in group:
                yield (v[name],-v[fn])

        for name, group in iteritems(groups):
            gval = v['@@' + name]
            yield tuple([-gval] + [v[fn] for fn in group])
            for k, fn1 in enumerate(group):
                # Ensure two package with the same name are not installed
                # e.g. for three packages fn1, fn2, f3:
                # NOT fn1 OR NOT fn2, NOT fn1 OR NOT fn3, NOT fn2 OR NOT fn3
                nval = -v[fn1]
                yield (gval, nval)
                for fn2 in group[k+1:]:
                    yield (nval,-v[fn2])
                # Ensure each dependency is installed
                # e.g. numpy-1.7 IMPLIES (python-2.7.3 OR python-2.7.4 OR ...)
                for ms in self.ms_depends(fn1):
                    if ms.name[0] == '@':
                        assert ms.name in v, '%s %r' % (fn1, ms)
                        yield (nval, v[ms.name])
                    else:
                        clause = [v[fn2] for fn2 in self.find_matches_group(ms, groups)]
                        assert relax or clause, '%s %r' % (fn1, ms)
                        yield tuple([nval] + clause)

        # Ensure that at least one package is installed matching each spec
        # fn1 OR fn2 OR fn3 OR ... OR fnN
        for ms in specs:
            ms = MatchSpec(ms)
            if not ms.optional:
                clause = [v[fn] for fn in self.find_matches_group(ms, groups)]
                assert relax or len(clause) >= 1, ms
                yield tuple(clause)

    def generate_feature_count(self, v, groups, specs):
        feats = {s.name for s in specs if s.name[-1] == '@' and not s.optional}
        return [(1,v[name]) for name in iterkeys(groups) if name[-1] == '@' and name not in feats], len(feats)

    def generate_feature_metric(self, v, groups, specs):
        eq = []
        for name, group in iteritems(groups):
            nf = [len(self.features(fn)) for fn in group]
            maxf = max(nf)
            if min(nf) == maxf:
                continue
            if not any(ms.name == name for ms in specs if not ms.optional):
                maxf += 1
            eq.extend((maxf-fc,v[fn]) for fn, fc in zip(group, nf) if fc < maxf)
        return eq

    def generate_optional_count(self, v, groups, specs):
        eq = []
        max_rhs = 0
        for s in specs:
            if not s.optional or s.name[0] == '@' or s.name not in groups:
                continue
            group = groups[s.name]
            fgroup = [(1,v[fn]) for fn in self.find_matches_group(s, groups)]
            if len(fgroup) == 0:
                continue
            elif len(fgroup) == len(group):
                eq.append((1,v['@@'+s.name]))
            else:
                eq.extend(fgroup)
            max_rhs += 1
        return eq, max_rhs

    def generate_version_metric(self, v, groups, specs, majoronly=False):
        eq = []
        sdict = {}
        for s in specs:
            s = MatchSpec(s) # needed for testing
            sdict.setdefault(s.name,[]).append(s)
        key = lambda x: self.version_key(x,majoronly)
        for name, mss in iteritems(sdict):
            pkgs = [(key(p),p) for p in groups.get(name, [])]
            # If the "target" field in the MatchSpec is supplied, that means we want
            # to minimize the changes to the currently installed package. We prefer
            # any upgrade over any downgrade, but beyond that we want minimal change.
            targets = [ms.target for ms in mss if ms.target]
            if targets:
                v1 = sorted(((key(t),t) for t in targets), reverse=True)
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
                    eq += [(i, v[pkg])]
                prev = nkey
        return eq

    def generate_package_count(self, v, groups, specs):
        eq = []
        snames = {s.name for s in map(MatchSpec, specs)}
        for name, pkgs in iteritems(groups):
            if name in snames:
                continue
            pkg_ver = sorted([(self.version_key(p),p) for p in groups.get(name, [])], reverse=True)
            i = 1
            prev = None
            for nkey, pkg in pkg_ver:
                if prev and prev != nkey:
                    i += 1
                eq += [(i, v[pkg])]
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

    def build_vw(self, groups, features):
        v = {}  # map fn to variable number
        w = {}  # map variable number to fn
        i = -1  # in case the loop doesn't run
        for name, group in iteritems(groups):
            for fn in group:
                i += 1
                v[fn] = i + 1
                w[i + 1] = fn.rsplit('[',1)[0]
            name = '@@' + name
            i += 1
            v[name] = i + 1
            w[i + 1] = name
        for name in iterkeys(features):
            name = '@' + name
            i += 1
            v[name] = i + 1
            w[i + 1] = name
        m = i + 1
        return m, v, w

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
        dists = {fn:self.index[fn] for fn in installed}
        groups, trackers = build_groups(dists)
        if len(groups) < len(installed):
            return False
        specs = [MatchSpec('%s %s %s'%(rec['name'],rec['version'],rec['build'])) for rec in itervalues(dists)]
        m, v, w = self.build_vw(groups, trackers)
        def minsat(specs):
            return sat(self.gen_clauses(v, groups, trackers, specs, relax=True))
        if minsat(specs):
            return []
        hint = minimal_unsatisfiable_subset(specs, sat=minsat, log=False)
        return set(ms.name for ms in hint)

    def install_specs(self, specs, installed, update_deps=True):
        specs = list(map(MatchSpec, specs))
        if not installed:
            return specs, True
        snames = {s.name for s in specs}
        log.debug('Checking satisfiability of current install')
        bad_specs = self.bad_installed(installed)
        if bad_specs:
            log.debug('Current install is *not* satisfiable')
        for pkg in installed:
            assert pkg in self.index
            name, version, build = self.package_triple(pkg)
            if name in snames:
                continue
            # If update_deps=True, set the target package in MatchSpec so that
            # the solver can minimize the version change. If update_deps=False,
            # fix the version and build so that no change is possible.
            need_help = name in bad_specs
            if update_deps or need_help:
                spec = MatchSpec(name, target=pkg, optional=need_help)
            else:
                spec = MatchSpec('%s %s %s'%(name,version,build))
            specs.append(spec)
            snames.add(spec)
        return specs, not need_help

    def install(self, specs, installed=[], update_deps=True, returnall=False):
        len0 = len(specs)
        specs, isgood = self.install_specs(specs, installed, update_deps)
        pkgs = self.solve(specs, len0=len0, returnall=returnall)
        if not isgood:
            sdict = {self.package_name(pkg):pkg for pkg in installed}
            sdict.update({self.package_name(pkg):pkg for pkg in pkgs})
            pkgs = sdict.values()
        return pkgs

    def remove_specs(self, specs, installed):
        specs = [MatchSpec(s, optional=True, negate=True) for s in specs]
        snames = {s.name for s in specs}
        for pkg in installed:
            assert pkg in self.index
            name, version, build = self.package_triple(pkg)
            if name not in snames:
                specs.append(MatchSpec(name, optional=True, target=pkg))
        return specs

    def remove(self, specs, installed):
        specs = self.remove_specs(specs, installed)
        return self.solve(specs)

    def solve(self, specs, len0=None, returnall=False, sat_only=False):
        try:
            stdoutlog.info("Solving package specifications: ")
            dotlog.debug("Solving for %s" % specs)

            # Find the compliant packages
            specs = list(map(MatchSpec, specs))
            if len0 is None:
                len0 = len(specs)
            dists, new_specs = self.get_dists(specs, sat_only=sat_only)
            if not dists:
                return False if dists is None else ([[]] if returnall else [])

            # Clear out our caches to reduce memory usage before the solve
            self.find_matches_.clear()
            self.ms_depends_.clear()

            # Check if satisfiable
            dotlog.debug('Checking satisfiability')
            groups, feats = build_groups(dists)
            m, v, w = self.build_vw(groups, feats)
            clauses = list(self.gen_clauses(v, groups, feats, specs))
            solution = sat(clauses,m)
            if sat_only:
                return bool(solution)
            if not solution:
                def mysat(specs):
                    return sat(self.gen_clauses(v, groups, feats, specs))
                stderrlog.info('\nError: Unsatisfiable package specifications.\nGenerating hint: \n')
                hint = minimal_unsatisfiable_subset(specs, sat=mysat, log=True)
                sys.exit('%s%s\n%s' % (
                    'The following specifications were found to be in conflict:',
                    dashlist(hint),
                    'Use "conda info <package>" to see the dependencies for each package.'))

            specs += new_specs
            spec2 = [s for s in specs[:len0] if not s.optional]
            eq_requested_versions = self.generate_version_metric(v, groups, spec2, majoronly=True)
            clauses, solution, obj1 = optimize(eq_requested_versions, clauses, solution)
            dotlog.debug('Requested version metric: %d'%obj1)

            spec3 = [s for s in specs if s.optional and (not s.negate or self.find_matches_group(s, groups))]
            eq_optional_count, max_rhs = self.generate_optional_count(v, groups, spec3)
            clauses, solution, obj2 = optimize(eq_optional_count, clauses, solution, maximize=True, maxval=max_rhs)
            dotlog.debug('Optional package count: %d'%obj2)

            eq_optional_versions = self.generate_version_metric(v, groups, spec3, majoronly=True)
            clauses, solution, obj3 = optimize(eq_optional_versions, clauses, solution)
            dotlog.debug('Optional package version metric: %d'%obj3)

            eq_feature_count, n0 = self.generate_feature_count(v, groups, specs)
            clauses, solution, obj4 = optimize(eq_feature_count, clauses, solution)
            dotlog.debug('Feature count metric: %d'%(obj4+n0))

            eq_feature_metric = self.generate_feature_metric(v, groups, specs)
            clauses, solution, obj5 = optimize(eq_feature_metric, clauses, solution)
            dotlog.debug('Feature package metric: %d'%obj5)

            eq_all_versions = self.generate_version_metric(v, groups, specs, majoronly=False)
            clauses, solution, obj6 = optimize(eq_all_versions, clauses, solution)
            dotlog.debug('Total version metric: %d'%obj6)

            eq_package_count = self.generate_package_count(v, groups, specs)
            clauses, solution, obj7 = optimize(eq_package_count, clauses, solution)
            dotlog.debug('Weak dependency metric: %d'%obj7)

            dotlog.debug('Looking for alternate solutions')
            def clean(solution):
                return [s for s in solution if 0 < s <= m and '@' not in w[s]]
            nsol = 1
            solutions = [clean(solution)]
            while True:
                nclause = tuple(-q for q in solution)
                clauses.append(nclause)
                solution = sat(clauses,m)
                if solution is None:
                    break
                nsol += 1
                if nsol > 10:
                    dotlog.debug('Too many solutions; terminating')
                    break
                solution = clean(solution)
                solutions.append(solution)

            psolutions = [set(w[lit] for lit in sol) for sol in solutions]
            if nsol > 1:
                stdoutlog.info(
                    '\nWarning: %s possible package resolutions (only showing differing packages):\n' %
                    ('>10' if nsol > 10 else nsol))
                common  = set.intersection(*psolutions)
                for sol in psolutions:
                    stdoutlog.info('\t%s,\n' % sorted(sol - common))

            if obj6 > 0:
                log.debug("Older versions in the solution(s):")
                for sol in solutions:
                    log.debug([(i, w[j]) for i, j in eq_all_versions if j in sol])
            stdoutlog.info('\n')
            return list(map(sorted, psolutions)) if returnall else sorted(psolutions[0])
        except:
            stdoutlog.info('\n')
            raise


if __name__ == '__main__':
    import json
    from pprint import pprint
    from optparse import OptionParser
    from conda.cli.common import arg2spec

    with open('../tests/index.json') as fi:
        r = Resolve(json.load(fi))

    p = OptionParser(usage="usage: %prog [options] SPEC(s)")
    p.add_option("--mkl", action="store_true")
    opts, args = p.parse_args()

    specs = [arg2spec(arg) for arg in args]
    if opts.mkl:
        specs += 'mkl@'
    pprint(r.solve(specs, []))
