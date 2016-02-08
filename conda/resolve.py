from __future__ import print_function, division, absolute_import

import sys
import logging
from collections import defaultdict
from itertools import chain

from conda.compat import iterkeys, itervalues, iteritems, string_types
from conda.logic import sat, optimize, minimal_unsatisfiable_subset, evaluate_eq
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


class NoPackagesFound(RuntimeError):
    def __init__(self, msg, pkgs):
        super(NoPackagesFound, self).__init__(msg)
        if isinstance(pkgs, MatchSpec):
            self.pkgs = [pkgs.spec]
        else:
            self.pkgs = [x.spec for x in pkgs]


_specs = {}
class MatchSpec(object):

    def __new__(cls, spec, target=None, optional=False, parent=None):
        if isinstance(spec, cls):
            return spec
        self = _specs.get((spec,target,optional,parent))
        if self:
            return self
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
        self.parent = parent
        return self

    def match_fast(self, version, build):
        if self.strictness == 1:
            return True
        elif self.strictness == 2:
            return self.vspecs.match(version)
        else:
            return bool((version, build) == self.ver_build)

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
        if self.strictness == 3:
            return self.name + '-%s-%s.tar.bz2' % self.ver_build
        else:
            return None

    def __eq__(self, other):
        return type(other) is MatchSpec and self.spec == other.spec

    def __hash__(self):
        return hash(self.spec)

    def __repr__(self):
        res = 'MatchSpec(' + self.spec
        if self.target:
            res += ',target=' + self.target
        if self.optional:
            res += ',optional'
        return res + ')'

    def __str__(self):
        res = self.spec
        if res[-1] == '@' and self.strictness == 1:
            res = 'feature "%s"'%res[1:]
        if self.target or self.optional or self.parent:
            mods = []
            if self.target:
                mods.append('target='+self.target)
            if self.parent:
                mods.append('parent='+self.parent)
            if self.optional:
                mods.append('optional')
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
    feats = {}
    for fn, info in iteritems(index):
        if fn[-1] == '@':
            assert info['name'] == fn and info.get('track_features','') == fn[:-1]
            feats[fn] = info
        else:
            groups.setdefault(info['name'],[]).append(fn)
            for feat in info.get('track_features','').split():
                groups.setdefault(feat + '@',[]).append(fn)
    for fn, info in iteritems(feats):
        groups.setdefault(fn,[]).append(fn)
    return groups

class Resolve(object):

    def add_feature(self, feat, group=True):
        if feat not in self.feats:
            fpkg = feat + '@'
            self.feats.add(feat)
            self.index[fpkg] = {
                'name':fpkg, 'version':'1.0',
                'build':'0', 'build_number':0,
                'depends':[], 'track_features':feat
            }
            if group:
                self.groups[fpkg].append(fpkg)

    def __init__(self, index):
        self.index = index.copy()
        self.feats = set()
        for fn, info in iteritems(index):
            for fstr in info.get('track_features','').split():
                self.add_feature(fstr, False)
            for fstr in iterkeys(info.get('with_features_depends',{})):
                fn2 = fn + '[' + fstr + ']'
                self.index[fn2] = info
        self.groups = build_groups(self.index)
        self.find_matches_ = {}
        self.ms_depends_ = {}

    def get_dists(self, specs, sat_only=False):
        log.debug('Beginning the pruning process')

        specs = list(map(MatchSpec, specs))
        active = self.feats.copy()
        len0 = len(specs)
        bad_deps = []
        valid = {}
        unsat = []

        def filter_group(matches, top):
            # If no packages exist with this name, it's a fatal error
            match1 = next(x for x in matches)
            name = match1.name
            group = self.groups.get(name,[])
            if not group:
                bad_deps.append((matches,top))
                return False

            # If we are here, then this dependency is mandatory,
            # so add it to the master list. That way it is still
            # participates in the pruning even if one of its
            # parents is pruned away
            if all(name != ms.name for ms in specs):
                specs.append(MatchSpec(name, parent=str(top)))

            # Prune packages that don't match any of the patterns
            # or which may be missing dependencies
            nold = nnew = 0
            first = False
            notfound = set()
            for fn in group:
                sat = valid.get(fn, None)
                if sat is None:
                    first = sat = valid[fn] = True
                nold += sat
                if sat:
                    if name[-1] == '@':
                        sat = name[:-1] in self.track_features(fn)
                    else:
                        sat = self.match_any(matches, fn)
                if sat:
                    sat = all(any(valid.get(f2, True)
                                  for f2 in self.find_matches(ms))
                              for ms in self.ms_depends(fn) if not ms.optional)
                    if not sat:
                        notfound.update(ms for ms in self.ms_depends(fn) if ms.name not in self.groups)
                nnew += sat
                valid[fn] = sat

            reduced = nnew < nold
            if reduced:
                log.debug('%s: pruned from %d -> %d' % (name, nold, nnew))
                if nnew == 0:
                    if notfound:
                        bad_deps.append((notfound,matches))
                    unsat.extend(matches)
                    return True
            elif not first:
                return False

            # Perform the same filtering steps on any dependencies shared across
            # *all* packages in the group. Even if just one of the packages does
            # not have a particular dependency, it must be ignored in this pass.
            cdeps = defaultdict(list)
            for fn in group:
                if valid[fn]:
                    for m2 in self.ms_depends(fn):
                        cdeps[m2.name].append(m2)
            if top is None:
                top = match1
            cdeps = {mname:set(deps) for mname,deps in iteritems(cdeps) if len(deps)==nnew}
            if cdeps:
                top = top if top else match1
                if sum(filter_group(deps, top) for deps in itervalues(cdeps)):
                    reduced = True
            return reduced

        # Look through all of the non-optional specs (which at this point
        # should include the installed packages) for any features which *might*
        # be installed. Prune away any packages that depend on features other
        # than this subset.
        def prune_features():
            feats = set()
            for ms in specs:
                for fn in self.groups.get(ms.name, []):
                    if valid.get(fn, True):
                        feats.update(self.track_features(fn))
            pruned = False
            for feat in active - feats:
                active.remove(feat)
                for fn in self.groups[feat+'@']:
                    if valid.get(fn,True):
                        valid[fn] = False
                        pruned = True
            for name, group in iteritems(self.groups):
                nold =  npruned = 0
                for fn in group:
                    if valid.get(fn, True):
                        nold += 1
                        if self.features(fn) - feats:
                            valid[fn] = False
                            npruned += 1
                if npruned:
                    pruned = True
                    log.debug('%s: pruned from %d -> %d for missing features'%(name,nold,nold-npruned))
                    if npruned == nold:
                        for ms in specs:
                            if ms.name == name and not ms.optional:
                                bad_deps.append((ms,name+'@'))
            return pruned

        # Initial scan to add tracked features and rule out missing packages
        for feat in self.feats:
            valid[feat + '@'] = False
        for ms in specs:
            if ms.name[-1] == '@':
                feat = ms.name[:-1]
                self.add_feature(feat)
                valid[feat + '@'] = True
            elif not ms.optional:
                if not any(True for _ in self.find_matches(ms)):
                    bad_deps.append(ms)
        if bad_deps:
            raise NoPackagesFound(
                "No packages found in current %s channels matching: %s" %
                (config.subdir, ' '.join(map(str,bad_deps))), bad_deps)

        # Iterate in the filtering process until no more progress is made
        pruned = True
        while pruned:
            pruned = False
            for s in list(specs):
                if not s.optional:
                    pruned += filter_group([s], None)
                    if unsat and sat_only:
                        return False
            pruned += prune_features()
        log.debug('Potential feature set: %r'%(active,))

        # Touch all packages
        touched = {}
        def is_valid(fn, notfound=None):
            val = valid.get(fn)
            if val is None or (notfound and not val):
                valid[fn] = True # ensure cycles terminate
                val = valid[fn] = all(any(is_valid(f2)
                                          for f2 in self.find_matches(ms))
                                      for ms in self.ms_depends(fn))
            if notfound and not val:
                notfound.append(ms)
            return val
        def touch(fn, notfound=None):
            val = touched.get(fn)
            if val is None or (notfound is not None and not val):
                val = touched[fn] = is_valid(fn, notfound)
                if val:
                    for ms in self.ms_depends(fn):
                        for f2 in self.find_matches(ms):
                            touch(f2, notfound)
            return val
        for ms in specs[:len0]:
            notfound = []
            if sum(touch(fn, notfound) for fn in self.find_matches(ms)) == 0 and not ms.optional and notfound:
                bad_deps.extend((notfound,(ms)))

        if bad_deps:
            res = []
            specs = set()
            for spec, src in bad_deps:
                specs.update(spec)
                res.append('  - %s: %s' % ('|'.join(map(str,src)),', '.join(map(str,spec))))
            raise NoPackagesFound('\n'.join([
                    "Could not find some dependencies for one or more packages:"]
                    + res), specs)

        # Throw an error for missing packages or dependencies
        if sat_only and (unsat or bad_deps):
            return False

        # For weak dependency conflicts, generate a hint
        if unsat:
            def mysat(specs):
                self.get_dists(specs, sat_only=True)
            stderrlog.info('\nError: Unsatisfiable package specifications.\nGenerating hint: \n')
            hint = minimal_unsatisfiable_subset(specs, sat=mysat, log=True)
            hint = ['  - %s'%str(x) for x in set(chain(unsat, hint))]
            hint = (['The following specifications were found to be in conflict:'] + hint
                + ['Use "conda info <package>" to see the dependencies for each package.'])
            sys.exit('\n'.join(hint))

        dists = {fn:info for fn,info in iteritems(self.index) if touched.get(fn)}
        return dists, specs

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
        res = self.find_matches_.get(ms,None)
        if res is None:
            res = self.find_matches_[ms] = tuple(self.find_matches_group(ms, self.groups))
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
            deps.extend(MatchSpec(feat + '@') for feat in self.features(fn))
            self.ms_depends_[fn] = deps
        return deps

    def version_key(self, fn, majoronly=False):
        rec = self.index[fn]
        if majoronly:
            return VersionOrder(rec['version'])
        else:
            return (VersionOrder(rec['version']), len(self.features(fn)), rec['build_number'])

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
        pkgs = [Package(fn, self.index[fn]) for fn in self.find_matches(ms) if '@' not in fn]
        if not pkgs and not emptyok:
            raise NoPackagesFound("No packages found in current %s channels matching: %s" %
                (config.subdir, ms), ms)
        return pkgs

    def gen_clauses(self, v, groups, specs):
        specs = list(map(MatchSpec, specs))
        for name, group in iteritems(groups):
            if name[-1] == '@':
                # feat@ == fn1 OR fn2 OR fn3 OR fn4)
                # If the track feature is active, at least one of its
                # packages must be installed
                yield tuple([-v[name]] + [v[fn] for fn in group])
                # If the track feature is not installed, none of its
                # packages may be installed
                for fn in group:
                    yield (v[name],-v[fn])
                continue
            for k, fn1 in enumerate(group):
                # Ensure two package with the same name are not installed
                # e.g. for three packages fn1, fn2, f3:
                # NOT fn1 OR NOT fn2, NOT fn1 OR NOT fn3, NOT fn2 OR NOT fn3
                nval = -v[fn1]
                for fn2 in group[k+1:]:
                    yield (nval,-v[fn2])
                # Ensure each dependency is installed
                # e.g. numpy-1.7 IMPLIES (python-2.7.3 OR python-2.7.4 OR ...)
                for ms in self.ms_depends(fn1):
                    if ms.name[-1] == '@':
                        yield (nval, v[ms.name])
                    else:
                        clause = [v[fn2] for fn2 in self.find_matches_group(ms, groups)]
                        assert clause, '%s %r' % (fn1, ms)
                        yield tuple([nval] + clause)

        # Ensure that at least one package is installed matching each spec
        # fn1 OR fn2 OR fn3 OR ... OR fnN
        for ms in specs:
            if not ms.optional:
                clause = [v[fn] for fn in self.find_matches_group(ms, groups)]
                assert len(clause) >= 1, ms
                yield tuple(clause)

    def generate_feature_eq(self, v, groups, specs):
        feats = {s.name for s in specs if s.name[-1] == '@' and not s.optional}
        return [(1,v[name]) for name in iterkeys(groups) if name[-1] == '@' and name not in feats], len(feats)

    def generate_version_eq(self, v, groups, specs, majoronly=False, include0=False):
        eq = []
        sdict = {}
        for s in specs:
            s = MatchSpec(s) # needed for testing
            sdict.setdefault(s.name,[]).append(s)
        key = lambda x: self.version_key(x,majoronly)
        for name, mss in iteritems(sdict):
            if name[-1] == '@' or all(ms.optional for ms in mss):
                continue
            pkgs = [(key(p),p) for p in groups[name]]
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
                if i or include0:
                    eq += [(i, v[pkg])]
                prev = nkey
        return eq

    def generate_package_count(self, v, groups, specs):
        eq = []
        snames = {s.name for s in map(MatchSpec, specs)}
        for name, pkgs in iteritems(groups):
            if name[-1] != '@' and name not in snames:
                pkg_ver = sorted([(self.version_key(p),p) for p in groups[name]], reverse=True)
                i = 1
                prev = None
                for nkey, pkg in pkg_ver:
                    if prev and prev != nkey:
                        i += 1
                    eq += [(i, v[pkg])]
                    prev = nkey
                    if name == 'pytz':
                        print(pkg,i)
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

    def build_vw(self, groups):
        v = {}  # map fn to variable number
        w = {}  # map variable number to fn
        i = -1  # in case the loop doesn't run
        for name, group in iteritems(groups):
            if name[-1] == '@':
                i += 1
                v[name] = i + 1
                w[i + 1] = name
            else:
                for fn in group:
                    i += 1
                    v[fn] = i + 1
                    w[i + 1] = fn.rsplit('[',1)[0]
        m = i + 1
        return m, v, w

    @staticmethod
    def clause_pkg_name(i, w):
        if i > 0:
            ret = w[i]
        else:
            ret = 'not ' + w[-i]
        return ret.rsplit('.tar.bz2', 1)[0]

    def minimal_unsatisfiable_subset(self, clauses, v, w):
        clauses = minimal_unsatisfiable_subset(clauses, log=True)

        pretty_clauses = []
        for clause in clauses:
            if clause[0] < 0 and len(clause) > 1:
                pretty_clauses.append('%s => %s' %
                    (self.clause_pkg_name(-clause[0], w), ' or '.join([self.clause_pkg_name(j, w) for j in clause[1:]])))
            else:
                pretty_clauses.append(' or '.join([self.clause_pkg_name(j, w) for j in clause]))
        return "The following set of clauses is unsatisfiable:\n\n%s" % '\n'.join(pretty_clauses)

    def guess_bad_solve(self, specs):
        # TODO: Check features as well
        from conda.console import setup_verbose_handlers
        setup_verbose_handlers()

        def mysat(specs):
            dists = self.get_dists(specs)
            groups = build_groups(dists)
            m, v, w = self.build_vw(groups)
            clauses = set(self.gen_clauses(v, groups, specs))
            return sat(clauses)

        # Don't show the dots from solve2 in normal mode but do show the
        # dotlog messages with --debug
        dotlog.setLevel(logging.INFO)
        specs = [s for s in specs if not s.optional]
        hint = minimal_unsatisfiable_subset(specs, sat=mysat, log=True)
        if not hint:
            return ''
        hint = list(map(str, hint))
        if len(hint) == 1:
            # TODO: Generate a hint from the dependencies.
            ret = (("\nHint: '{0}' has unsatisfiable dependencies (see 'conda "
                "info {0}')").format(hint[0].split()[0]))
        else:
            ret = """
Hint: the following packages conflict with each other:
  - %s

Use 'conda info %s' etc. to see the dependencies for each package.""" % ('\n  - '.join(hint), hint[0].split()[0])
        return ret

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

    def solve(self, specs, installed=[], update_deps=True, returnall=False,
              guess=True, minimal_hint=False):
        try:
            stdoutlog.info("Solving package specifications: ")
            res = self.explicit(specs)
            if res is not None:
                return res

            # If update_deps=True, set the target package in MatchSpec so that
            # the solver can minimize the version change. If update_deps=False,
            # fix the version and build so that no change is possible.
            len0 = len(specs)
            specs = list(map(MatchSpec, specs))
            snames = {s.name for s in specs}
            for pkg in installed:
                name, version, build = self.package_triple(pkg)
                if pkg not in self.index:
                    self.index[pkg] = {
                        'name':name, 'version':version,
                        'build':build, 'build_number':0
                    }
                    self.groups.setdefault(name,[]).append(pkg)
                if name in snames:
                    continue
                if update_deps:
                    spec = MatchSpec(name, target=pkg)
                else:
                    spec = MatchSpec('%s %s %s'%(name,version,build))
                specs.append(spec)
                snames.add(spec)
            dotlog.debug("Solving for %s" % specs)

            try:
                dists, specs = self.get_dists(specs)
            except NoPackagesFound:
                raise

            # Clear out our caches to reduce memory usage before the solve
            self.find_matches_.clear()
            self.ms_depends_.clear()

            # Check if satisfiable
            dotlog.debug('Checking satisfiability')
            groups = build_groups(dists)
            m, v, w = self.build_vw(groups)
            clauses = list(self.gen_clauses(v, groups, specs))
            solution = sat(clauses)
            if not solution:
                if guess:
                    if minimal_hint:
                        stderrlog.info('\nError: Unsatisfiable package '
                            'specifications.\nGenerating minimal hint: \n')
                        sys.exit(self.minimal_unsatisfiable_subset(clauses, v, w))
                    else:
                        stderrlog.info('\nError: Unsatisfiable package '
                            'specifications.\nGenerating hint: \n')
                        sys.exit(self.guess_bad_solve(specs))
                raise RuntimeError("Unsatisfiable package specifications")

            eq_version = self.generate_version_eq(v, groups, specs[:len0], majoronly=True)
            clauses, solution, obj1 = optimize(eq_version, clauses, solution)
            dotlog.debug('Requested version metric: %d'%obj1)

            eq_features, n0 = self.generate_feature_eq(v, groups, specs)
            clauses, solution, obj = optimize(eq_features, clauses, solution)
            dotlog.debug('Feature count metric: %d'%(obj+n0))

            eq_version2 = self.generate_version_eq(v, groups, specs, majoronly=False)
            clauses, solution, obj2 = optimize(eq_version2, clauses, solution)
            dotlog.debug('Total version metric: %d'%obj2)

            eq_version3 = self.generate_package_count(v, groups, specs)
            clauses, solution, obj3 = optimize(eq_version3, clauses, solution)
            dotlog.debug('Weak dependency metric: %d'%obj3)

            dotlog.debug('Final metrics: (%d,%d,%d,%d)'%(
                (n0+evaluate_eq(eq_features,solution),
                    evaluate_eq(eq_version,solution),
                    evaluate_eq(eq_version2,solution),
                    evaluate_eq(eq_version3,solution))))

            solution = [s for s in solution if 0 < s <= m]

            dotlog.debug('Looking for alternate solutions')
            solutions = [solution]
            nsol = 1
            while True:
                nclause = tuple(-q for q in solution if 0 < q <= m)
                clauses.append(nclause)
                solution = sat(clauses)
                if solution is None:
                    break
                solution = [s for s in solution if 0 < s <= m]
                nsol += 1
                if nsol > 10:
                    dotlog.debug('Too many solutions; terminating')
                    break
                solutions.append(solution)

            psolutions = [set(w[lit] for lit in sol if 0 < lit <= m and '@' not in w[lit]) for sol in solutions]
            if nsol > 1:
                stdoutlog.info(
                    '\nWarning: %s possible package resolutions (only showing differing packages):\n' %
                    ('>10' if nsol > 10 else nsol))
                common  = set.intersection(*psolutions)
                for sol in psolutions:
                    stdoutlog.info('\t%s,\n' % sorted(sol - common))

            if obj1 > 0 or obj2 > 0 or (obj3 > 0 and any(i>1 for i,_ in eq_version3)):
                log.debug("Older versions in the solution(s):")
                for sol in solutions:
                    v = ([(i, w[j]) for i, j in eq_version if j in sol] +
                         [(i, w[j]) for i, j in eq_version2 if j in sol] +
                         [(i, w[j]) for i, j in eq_version3 if i>1 and j in sol])
                    log.debug(v)
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
