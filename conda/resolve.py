import re
import sys
import itertools
from collections import defaultdict

import verlib
from utils import iter_pairs, memoized, memoize


class MatchSpec(object):

    def __init__(self, spec):
        self.spec = spec
        parts = spec.split()
        self.strictness = len(parts)
        assert 1 <= self.strictness <= 3
        self.name = parts[0]

        if self.strictness == 2:
            rx = parts[1]
            rx = rx.replace('.', r'\.')
            rx = rx.replace('*', r'.*')
            rx = r'(%s)$' % rx
            self.ver_pat = re.compile(rx)

        elif self.strictness == 3:
            self.ver_build = tuple(parts[1:3])

    def match(self, fn):
        assert fn.endswith('.tar.bz2')
        name, version, build = fn[:-8].rsplit('-', 2)
        if name != self.name:
            return False
        if self.strictness == 2 and self.ver_pat.match(version) is None:
            return False
        if self.strictness == 3 and ((version, build) != self.ver_build):
            return False
        return True

    def __eq__(self, other):
        return self.spec == other.spec

    def __hash__(self):
        return hash(self.spec)

    def __repr__(self):
        return 'MatchSpec(%r)' % (self.spec)


class Package(object):

    def __init__(self, fn, info):
        self.fn = fn
        self.name = info['name']
        self.version = info['version']
        self.build_number = info['build_number']

        v = self.version
        v = v.replace('rc', '.dev99999')
        if v.endswith('.dev'):
            v += '0'
        try:
            self.norm_version = verlib.NormalizedVersion(v)
        except verlib.IrrationalVersionError:
            self.norm_version = self.version

    def __cmp__(self, other):
        if self.name != other.name:
            raise ValueError('cannot compare packages with different '
                             'names: %r %r' % (self.fn, other.fn))
        try:
            return cmp((self.norm_version, self.build_number),
                       (other.norm_version, other.build_number))
        except TypeError:
            return cmp((self.version, self.build_number),
                       (other.version, other.build_number))

    def __repr__(self):
        return '<Package %s>' % self.fn


class Resolve(object):

    def __init__(self, index):
        self.index = index
        self.groups = defaultdict(list) # map name to list of filenames
        for fn, info in index.iteritems():
            self.groups[info['name']].append(fn)
        self.msd_cache = {}

    def find_matches(self, ms):
        for fn in self.groups[ms.name]:
            if ms.match(fn):
                yield fn

    def ms_depends(self, fn):
        try:
            res = self.msd_cache[fn]
        except KeyError:
            res = self.msd_cache[fn] = [MatchSpec(d)
                                        for d in self.index[fn]['depends']]
        return res

    @memoize
    def features(self, fn):
        return set(self.index[fn].get('features', '').split())

    def track_features(self, fn):
        return set(self.index[fn].get('track_features', '').split())

    @memoize
    def get_pkgs(self, ms):
        #print ms, isinstance(ms, collections.Hashable)
        return [Package(fn, self.index[fn]) for fn in self.find_matches(ms)]

    def get_max_dists(self, ms):
        pkgs = self.get_pkgs(ms)
        assert pkgs
        maxpkg = max(pkgs)
        for pkg in pkgs:
            if pkg == maxpkg:
                yield pkg.fn

    def all_deps(self, root_fn):
        res = set()

        def add_dependents(fn1):
            for ms in self.ms_depends(fn1):
                for fn2 in self.get_max_dists(ms):
                    if fn2 in res:
                        continue
                    res.add(fn2)
                    if ms.strictness < 3:
                        add_dependents(fn2)

        add_dependents(root_fn)
        return res

    def solve2(self, root_dists, features, verbose=False, ensure_sat=False):
        dists = set()
        for root_fn in root_dists:
            dists.update(self.all_deps(root_fn))
            dists.add(root_fn)

        l_groups = defaultdict(list) # map name to list of filenames
        for fn in dists:
            l_groups[self.index[fn]['name']].append(fn)

        if not ensure_sat and len(l_groups) == len(dists):
            assert all(len(filenames) == 1
                       for filenames in l_groups.itervalues())
            if verbose:
                print "No duplicate name, no SAT needed."
            return sorted(dists)

        try:
            import pycosat
        except ImportError:
            sys.exit("cannot import pycosat, try: conda install pycosat")

        v = {} # map fn to variable number
        w = {} # map variable number to fn
        for i, fn in enumerate(sorted(dists)):
            v[fn] = i + 1
            w[i + 1] = fn

        clauses = []

        for filenames in l_groups.itervalues():
            # ensure packages with the same name conflict
            for fn1 in filenames:
                v1 = v[fn1]
                for fn2 in filenames:
                    v2 = v[fn2]
                    if v1 < v2:
                        clauses.append([-v1, -v2])

        for fn1 in dists:
            for ms in self.ms_depends(fn1):
                clause = [-v[fn1]]
                for fn2 in self.find_matches(ms):
                    if fn2 in dists:
                        clause.append(v[fn2])

                assert len(clause) > 1, fn1
                clauses.append(clause)

        for root_fn in root_dists:
            clauses.append([v[root_fn]])

        candidates = defaultdict(list)
        for sol in pycosat.itersolve(clauses):
            pkgs = [w[lit] for lit in sol if lit > 0]
            fsd = sum(len(features ^ self.features(fn)) for fn in pkgs)
            key = fsd, len(pkgs)
            #print key, pkgs
            candidates[key].append(pkgs)

        if not candidates:
            print "Error: UNSAT"
            return []

        minkey = min(candidates)

        mc = candidates[minkey]
        if len(mc) != 1:
            print 'WARNING:', len(mc), root_dists, features

        return candidates[minkey][0]

    verscores = {}
    def select_dists_spec(self, spec):
        pkgs = sorted(self.get_pkgs(MatchSpec(spec)))
        vs = 0
        for p1, p2 in iter_pairs(pkgs):
            self.verscores[p1.fn] = vs
            if p2 and p2 > p1:
                vs += 1
        #pprint(self.verscores)
        return [p.fn for p in pkgs]

    @memoize
    def sum_matches(self, fn1, fn2):
        return sum(ms.match(fn2) for ms in self.ms_depends(fn1))

    def select_root_dists(self, specs, features, installed):
        args = [self.select_dists_spec(spec) for spec in specs]

        @memoized
        def installed_matches(fn):
            return sum(self.sum_matches(fn, fn2) for fn2 in installed)

        candidates = defaultdict(list)
        for dists in itertools.product(*args):
            fsd = olx = svs = sim = 0
            for fn1 in dists:
                fsd += len(features ^ self.features(fn1))
                olx += sum(self.sum_matches(fn1, fn2)
                           for fn2 in dists if fn1 != fn2)
                svs += self.verscores[fn1]
                sim += installed_matches(fn1)

            key = -fsd, olx, svs, sim
            #print dists, key
            candidates[key].append(dists)

        maxkey = max(candidates)
        #print 'maxkey:', maxkey

        mc = candidates[maxkey]
        if len(mc) != 1:
            print 'WARNING:', len(mc)
            for c in mc:
                print '\t', c

        return set(candidates[maxkey][0])

    def tracked_features(self, installed):
        res = set()
        for fn in installed:
            try:
                res.update(self.features(fn))
            except KeyError:
                pass
        return res

    def update_with_features(self, fn, features):
        with_features = self.index[fn].get('with_features_depends')
        if with_features is None:
            return
        key = ''
        for fstr in with_features:
            fs = set(fstr.split())
            if fs.issubset(features) and len(fs) > len(set(key.split())):
                key = fstr
        if not key:
            return
        d = {ms.name: ms for ms in self.ms_depends(fn)}
        for spec in with_features[key]:
            ms = MatchSpec(spec)
            d[ms.name] = ms
        self.msd_cache[fn] = d.values()

    def solve(self, specs, installed=None, features=None,
                    verbose=False, ensure_sat=False):
        if installed is None:
            installed = []
        if features is None:
            features = self.tracked_features(installed)
        dists = self.select_root_dists(specs, features, installed)
        for fn in dists:
            features.update(self.track_features(fn))
        if verbose:
            print dists, features
        for fn in dists:
            self.update_with_features(fn, features)
        return self.solve2(dists, features, verbose, ensure_sat)


if __name__ == '__main__':
    import json
    from pprint import pprint
    from optparse import OptionParser

    with open('../tests/index.json') as fi:
        r = Resolve(json.load(fi))

    def arg2spec(arg):
        spec = arg.replace('=', ' ')
        if arg.count('=') == 1:
            spec += '*'
        return spec

    p = OptionParser(usage="usage: %prog [options] SPEC(s)")
    p.add_option("--mkl", action="store_true")
    opts, args = p.parse_args()

    features = set(['mkl']) if opts.mkl else set()
    installed = ['numpy-1.7.1-py27_0.tar.bz2', 'python-2.7.5-0.tar.bz2']
    specs = [arg2spec(arg) for arg in args]
    pprint(r.solve(specs, installed, features,
                   verbose=True, ensure_sat=True))
