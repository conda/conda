import re
import sys
from collections import defaultdict

import verlib
from utils import memoize

try:
    import pycosat
except ImportError:
    sys.exit("cannot import pycosat, try: conda install pycosat")


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


def get_candidate(candidates):
    key = min(candidates)
    #print 'minkey: %r' % key
    mc = candidates[key]
    if len(mc) != 1:
        print 'WARNING:', len(mc)
        for c in mc:
            print '\t', c
    return mc[0]

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
        # the reason we don't use @memoize here is to allow resetting the
        # cache using self.msd_cache = {}, which is used during testing
        try:
            res = self.msd_cache[fn]
        except KeyError:
            res = self.msd_cache[fn] = [MatchSpec(d)
                                        for d in self.index[fn]['depends']]
        return res

    @memoize
    def features(self, fn):
        return set(self.index[fn].get('features', '').split())

    @memoize
    def track_features(self, fn):
        return set(self.index[fn].get('track_features', '').split())

    @memoize
    def get_pkgs(self, ms):
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

    def mk_clauses(self, v, dists, specs, features):
        groups = defaultdict(list) # map name to list of filenames
        for fn in dists:
            groups[self.index[fn]['name']].append(fn)

        res = []
        for filenames in groups.itervalues():
            # ensure packages with the same name conflict
            for fn1 in filenames:
                v1 = v[fn1]
                for fn2 in filenames:
                    v2 = v[fn2]
                    if v1 < v2:
                        res.append([-v1, -v2])

        for fn1 in dists:
            for ms in self.ms_depends(fn1):
                # ensure dependencies are installed
                clause = [-v[fn1]]
                for fn2 in self.find_matches(ms):
                    if fn2 in dists:
                        clause.append(v[fn2])
                assert len(clause) > 1, fn1
                res.append(clause)

                for feat in features:
                    # ensure that a package (with required name) which has
                    # the feature is installed
                    clause = [-v[fn1]]
                    for fn2 in groups[ms.name]:
                         if feat in self.features(fn2):
                             clause.append(v[fn2])
                    if len(clause) > 1:
                        res.append(clause)

        for spec in specs:
            ms = MatchSpec(spec)
            # ensure that a matching package which the feature is installed
            for feat in features:
                clause = [v[fn] for fn in self.find_matches(ms)
                          if fn in dists and feat in self.features(fn)]
                if len(clause) > 0:
                    res.append(clause)

            # finally, ensure a matching package itself is installed
            clause = [v[fn] for fn in self.find_matches(ms)
                      if fn in dists]
            assert len(clause) >= 1
            res.append(clause)

        return res

    def solve2(self, specs, features):
        dists = set()
        for spec in specs:
            for fn in self.get_max_dists(MatchSpec(spec)):
                if fn in dists:
                    continue
                dists.update(self.all_deps(fn))
                dists.add(fn)

        v = {} # map fn to variable number
        w = {} # map variable number to fn
        for i, fn in enumerate(sorted(dists)):
            v[fn] = i + 1
            w[i + 1] = fn

        clauses = self.mk_clauses(v, dists, specs, features)

        candidates = defaultdict(list)
        n = 0
        for sol in pycosat.itersolve(clauses):
            n += 1
            pkgs = [w[lit] for lit in sol if lit > 0]
            candidates[len(pkgs)].append(pkgs)
        #print len(candidates), '     n=%d' % n

        if candidates:
            return get_candidate(candidates)
        else:
            print "Error: UNSAT"
            return []

    @memoize
    def sum_matches(self, fn1, fn2):
        return sum(ms.match(fn2) for ms in self.ms_depends(fn1))

    def find_substitute(self, installed, features, fn):
        """
        Find a substitute package for `fn` (given `installed` packages)
        which does *NOT* have `featues`.  If found, the substitute will
        have the same package namd and version and its dependencies will
        match the installed packages as closely as possible.
        If no substribute is found, None is returned.
        """
        name, version, unused_build = fn.rsplit('-', 2)
        candidates = defaultdict(list)
        for fn1 in self.get_max_dists(MatchSpec(name + ' ' + version)):
            if self.features(fn1).intersection(features):
                continue
            key = -sum(self.sum_matches(fn1, fn2) for fn2 in installed)
            candidates[key].append(fn1)

        if candidates:
            return get_candidate(candidates)
        else:
            return None

    def installed_features(self, installed):
        """
        Return the set of all features of all `installed` packages,
        """
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
            if fs <= features and len(fs) > len(set(key.split())):
                key = fstr
        if not key:
            return
        d = {ms.name: ms for ms in self.ms_depends(fn)}
        for spec in with_features[key]:
            ms = MatchSpec(spec)
            d[ms.name] = ms
        self.msd_cache[fn] = d.values()

    def solve(self, specs, installed=None, features=None, verbose=False):
        #if verbose:
        #    print "Resolve.solve(): installed:", installed

        if installed is None:
            installed = []
        if features is None:
            features = self.installed_features(installed)
        for spec in specs:
            ms = MatchSpec(spec)
            for fn in self.get_max_dists(ms):
                features.update(self.track_features(fn))
        if verbose:
            print specs, features
        for spec in specs:
            for fn in self.get_max_dists(MatchSpec(spec)):
                self.update_with_features(fn, features)
        return self.solve2(specs, features)


if __name__ == '__main__':
    import json
    from pprint import pprint
    from optparse import OptionParser
    from conda.plan import arg2spec

    with open('../tests/index.json') as fi:
        r = Resolve(json.load(fi))

    p = OptionParser(usage="usage: %prog [options] SPEC(s)")
    p.add_option("--mkl", action="store_true")
    opts, args = p.parse_args()

    features = set(['mkl']) if opts.mkl else set()
    specs = [arg2spec(arg) for arg in args]
    pprint(r.solve(specs, [], features, verbose=True))
