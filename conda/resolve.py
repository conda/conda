from __future__ import print_function, division, absolute_import

import re
import sys
import logging
from itertools import islice, combinations
from collections import defaultdict

from conda import verlib
from conda.utils import memoize
from conda.compat import itervalues, iteritems
from conda.logic import Clauses, Linear, false, true

log = logging.getLogger(__name__)


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

    def to_filename(self):
        if self.strictness == 3:
            return self.name + '-%s-%s.tar.bz2' % self.ver_build
        else:
            return None

    def __eq__(self, other):
        return self.spec == other.spec

    def __hash__(self):
        return hash(self.spec)

    def __repr__(self):
        return 'MatchSpec(%r)' % (self.spec)

    def __str__(self):
        return self.spec


class Package(object):
    """
    The only purpose of this class is to provide package objects which
    are sortable.
    """

    def __init__(self, fn, info):
        self.fn = fn
        self.name = info['name']
        self.version = info['version']
        self.build_number = info['build_number']
        self.build = info['build']
        self.channel = info.get('channel')

        v = self.version
        v = v.replace('rc', '.dev99999')
        if v.endswith('.dev'):
            v += '0'
        try:
            self.norm_version = verlib.NormalizedVersion(v)
        except verlib.IrrationalVersionError:
            self.norm_version = self.version

    # http://python3porting.com/problems.html#unorderable-types-cmp-and-cmp
#     def __cmp__(self, other):
#         if self.name != other.name:
#             raise ValueError('cannot compare packages with different '
#                              'names: %r %r' % (self.fn, other.fn))
#         try:
#             return cmp((self.norm_version, self.build_number),
#                       (other.norm_version, other.build_number))
#         except TypeError:
#             return cmp((self.version, self.build_number),
#                       (other.version, other.build_number))

    def __lt__(self, other):
        if self.name != other.name:
            raise TypeError('cannot compare packages with different '
                             'names: %r %r' % (self.fn, other.fn))
        try:
            return ((self.norm_version, self.build_number, other.build) <
                    (other.norm_version, other.build_number, self.build))
        except TypeError:
            return ((self.version, self.build_number) <
                    (other.version, other.build_number))

    def __eq__(self, other):
        if not isinstance(other, Package):
            return False
        if self.name != other.name:
            return False
        try:
            return ((self.norm_version, self.build_number, self.build) ==
                    (other.norm_version, other.build_number, other.build))
        except TypeError:
            return ((self.version, self.build_number, self.build) ==
                    (other.version, other.build_number, other.build))

    def __gt__(self, other):
        return not (self.__lt__(other) or self.__eq__(other))

    def __le__(self, other):
        return self < other or self == other

    def __ge__(self, other):
        return self > other or self == other

    def __repr__(self):
        return '<Package %s>' % self.fn


def min_sat(clauses, max_n=1000):
    """
    Calculate the SAT solutions for the `clauses` for which the number of
    true literals is minimal.  Returned is the list of those solutions.
    When the clauses are unsatisfiable, an empty list is returned.

    This function could be implemented using a Pseudo-Boolean SAT solver,
    which would avoid looping over the SAT solutions, and would therefore
    be much more efficient.  However, for our purpose the current
    implementation is good enough.
    """
    try:
        import pycosat
    except ImportError:
        sys.exit('Error: could not import pycosat (required for dependency '
                 'resolving)')

    min_tl, solutions = sys.maxsize, []
    for sol in islice(pycosat.itersolve(clauses), max_n):
        tl = sum(lit > 0 for lit in sol) # number of true literals
        if tl < min_tl:
            min_tl, solutions = tl, [sol]
        elif tl == min_tl:
            solutions.append(sol)

    return solutions


class Resolve(object):

    def __init__(self, index):
        self.index = index
        self.groups = defaultdict(list) # map name to list of filenames
        for fn, info in iteritems(index):
            self.groups[info['name']].append(fn)
        self.msd_cache = {}

    def find_matches(self, ms):
        for fn in sorted(self.groups[ms.name]):
            if ms.match(fn):
                yield fn

    def ms_depends(self, fn):
        # the reason we don't use @memoize here is to allow resetting the
        # cache using self.msd_cache = {}, which is used during testing
        try:
            res = self.msd_cache[fn]
        except KeyError:
            depends = self.index[fn]['depends']
            res = self.msd_cache[fn] = [MatchSpec(d) for d in depends]
        return res

    @memoize
    def features(self, fn):
        return set(self.index[fn].get('features', '').split())

    @memoize
    def track_features(self, fn):
        return set(self.index[fn].get('track_features', '').split())

    @memoize
    def get_pkgs(self, ms):
        pkgs = [Package(fn, self.index[fn]) for fn in self.find_matches(ms)]
        if not pkgs:
            raise RuntimeError("No packages found matching: %s" % ms)
        return pkgs

    def get_max_dists(self, ms):
        pkgs = self.get_pkgs(ms)

        if not pkgs:
            raise RuntimeError("No packages found matching: %s" % ms)
        maxpkg = max(pkgs)
        for pkg in pkgs:
            if pkg == maxpkg:
                yield pkg.fn

    def all_deps(self, root_fn):
        res = {}

        def add_dependents(fn1):
            for ms in self.ms_depends(fn1):
                for pkg2 in self.get_pkgs(ms):
                    if pkg2.fn in res:
                        continue
                    res[pkg2.fn] = pkg2
                    if ms.strictness < 3:
                        add_dependents(pkg2.fn)

        add_dependents(root_fn)
        return res

    def gen_clauses(self, v, dists, specs, features):
        groups = defaultdict(list) # map name to list of filenames
        for fn in dists:
            groups[self.index[fn]['name']].append(fn)

        for filenames in itervalues(groups):
            # ensure packages with the same name conflict
            for fn1 in filenames:
                v1 = v[fn1]
                for fn2 in filenames:
                    v2 = v[fn2]
                    if v1 < v2:
                        # NOT (fn1 AND fn2)
                        # e.g. NOT (numpy-1.6 AND numpy-1.7)
                        yield [-v1, -v2]

        for fn1 in dists:
            for ms in self.ms_depends(fn1):
                # ensure dependencies are installed
                # e.g. numpy-1.7 IMPLIES (python-2.7.3 OR python-2.7.4 OR ...)
                clause = [-v[fn1]]
                for fn2 in self.find_matches(ms):
                    if fn2 in dists:
                        clause.append(v[fn2])
                assert len(clause) > 1, '%s %r' % (fn1, ms)
                yield clause

                for feat in features:
                    # ensure that a package (with required name) which has
                    # the feature is installed
                    # e.g. numpy-1.7 IMPLIES (numpy-1.8[mkl] OR numpy-1.7[mkl])
                    clause = [-v[fn1]]
                    for fn2 in groups[ms.name]:
                         if feat in self.features(fn2):
                             clause.append(v[fn2])
                    if len(clause) > 1:
                        yield clause

        for spec in specs:
            ms = MatchSpec(spec)
            # ensure that a matching package with the feature is installed
            for feat in features:
                # numpy-1.7[mkl] OR numpy-1.8[mkl]
                clause = [v[fn] for fn in self.find_matches(ms)
                          if fn in dists and feat in self.features(fn)]
                if len(clause) > 0:
                    yield clause

            # finally, ensure a matching package itself is installed
            # numpy-1.7-py27 OR numpy-1.7-py26 OR numpy-1.7-py33 OR
            # numpy-1.7-py27[mkl] OR ...
            clause = [v[fn] for fn in self.find_matches(ms)
                      if fn in dists]
            assert len(clause) >= 1, ms
            yield clause

    def generate_version_constraints(self, eq, v, rhs):
        l = Linear(eq, rhs)
        m = max(v.values()) if v else 0
        C = Clauses(m)
        yield [C.build_BDD(l)]
        for clause in C.clauses:
            yield list(clause)

    def generate_eq(self, v, dists, include0=False):
        groups = defaultdict(list) # map name to list of filenames
        for fn in sorted(dists):
            groups[self.index[fn]['name']].append(fn)

        eq = []
        max_rhs = 0
        for filenames in sorted(itervalues(groups)):
            pkgs = sorted(filenames, key=lambda i: dists[i], reverse=True)
            i = 0
            prev = pkgs[0]
            for pkg in pkgs:
                # > compares build strings but == does not
                if (dists[pkg].name, dists[pkg].norm_version,
                    dists[pkg].build_number) != (dists[prev].name,
                        dists[prev].norm_version, dists[prev].build_number):
                    i += 1
                if i or include0:
                    eq += [(i, v[pkg])]
                prev = pkg
            max_rhs += i

        return eq, max_rhs

    def get_dists(self, specs):
        dists = {}
        for spec in specs:
            for pkg in self.get_pkgs(MatchSpec(spec)):
                if pkg.fn in dists:
                    continue
                dists.update(self.all_deps(pkg.fn))
                dists[pkg.fn] = pkg

        return dists

    def solve2(self, specs, features, guess=True):
        dists = self.get_dists(specs)

        v = {} # map fn to variable number
        w = {} # map variable number to fn
        i = -1 # in case the loop doesn't run
        for i, fn in enumerate(sorted(dists)):
            v[fn] = i + 1
            w[i + 1] = fn
        m = i + 1

        clauses = list(self.gen_clauses(v, dists, specs, features))
        eq, max_rhs = self.generate_eq(v, dists)

        # Check the common case first
        log.debug("Building the constraint with rhs: [0, 0]")
        constraints = list(self.generate_version_constraints(eq, v, [0, 0]))
        if constraints[0] == [false]:
            # XXX: This should *never* happen. build_BDD only returns false
            # when the linear constraint is unsatisfiable, but any linear
            # constraint can equal 0, by setting all the variables to 0.
            solutions = []
        else:
            if constraints[0] == [true]:
                constraints = []

            log.debug("Checking for solutions with rhs:  [0, 0]")
            solutions = min_sat(clauses + constraints)

        # XXX: Should we check the other common case of unsatisfiable specs?
        # It could make a difference for the hint check.

        # We bisect the solution space. It's actually not that much faster
        # than a linear search, because a single term rhs generates fewer
        # clauses. The npSolver paper also indicates that a binary
        # search is not more effective than a top-down search. But bisecting
        # allows us to exit sooner on unsatisfiable specs.
        if not solutions:
            lo, hi = [0, max_rhs]
            while True:
                mid = (lo + hi)//2
                rhs = [lo, mid]
                log.debug("Building the constraint with rhs: %s" % rhs)
                constraints = list(self.generate_version_constraints(eq, v, rhs))
                if constraints[0] == [false]: # build_BDD returns false if the rhs is
                    solutions = []            # too big to be satisfied. XXX: This
                    break                     # probably indicates a bug.
                if constraints[0] == [true]:
                    constraints = []
                log.debug("Checking for solutions with rhs:  %s" % rhs)
                solutions = min_sat(clauses + constraints)
                if lo >= hi:
                    break
                if solutions:
                    if lo == mid:
                        break
                    # bisect good
                    hi = mid
                else:
                    # bisect bad
                    lo = mid+1

        if len(solutions) == 0:
            if guess:
                raise RuntimeError("Unsatisfiable package specifications\n" +
                                   self.guess_bad_solve(specs, features))
            raise RuntimeError("Unsatisfiable package specifications")

        if len(solutions) > 1:
            print('Warning:', len(solutions), "possible package resolutions:")
            for sol in solutions:
                print('\t', [w[lit] for lit in sol if 0 < lit <= m])

        return [w[lit] for lit in solutions.pop(0) if 0 < lit <= m]


    def guess_bad_solve(self, specs, features):
        # TODO: Check features as well
        hint = []
        # Try to find the largest satisfiable subset
        found = False
        for i in range(len(specs), 0, -1):
            if found:
                break
            for comb in combinations(specs, i):
                try:
                    self.solve2(comb, features, guess=False)
                except RuntimeError:
                    pass
                else:
                    rem = set(specs) - set(comb)
                    rem.discard('conda')
                    if len(rem) == 1:
                        hint.append("%s" % rem.pop())
                    else:
                        hint.append("%s" % ' and '.join(rem))

                    found = True
        if not hint:
            return ''
        if len(hint) == 1:
            return ("Hint: %s has a conflict with the remaining packages" %
                    hint[0])
        return ("""\
Hint: the following combinations of packages create a conflict with the
remaining packages:
  - %s""" % '\n  - '.join(hint))

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
        if len(specs) == 1:
            ms = MatchSpec(specs[0])
            fn = ms.to_filename()
            if fn is None:
                return None
            res = [ms2.to_filename() for ms2 in self.ms_depends(fn)]
            res.append(fn)
        else:
            res = [MatchSpec(spec).to_filename() for spec in specs
                   if spec != 'conda']

        if None in res:
            return None
        res.sort()
        log.debug('explicit(%r) finished' % specs)
        return res

    @memoize
    def sum_matches(self, fn1, fn2):
        return sum(ms.match(fn2) for ms in self.ms_depends(fn1))

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
        for fn1 in self.get_max_dists(MatchSpec(name + ' ' + version)):
            if self.features(fn1).intersection(features):
                continue
            key = sum(self.sum_matches(fn1, fn2) for fn2 in installed)
            candidates[key] = fn1

        if candidates:
            maxkey = max(candidates)
            return candidates[maxkey]
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

    def solve(self, specs, installed=None, features=None):
        if installed is None:
            installed = []
        if features is None:
            features = self.installed_features(installed)
        for spec in specs:
            ms = MatchSpec(spec)
            for fn in self.get_max_dists(ms):
                features.update(self.track_features(fn))
        log.debug('specs=%r  features=%r' % (specs, features))
        for spec in specs:
            for fn in self.get_max_dists(MatchSpec(spec)):
                self.update_with_features(fn, features)

        return self.explicit(specs) or self.solve2(specs, features)

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

    features = set(['mkl']) if opts.mkl else set()
    specs = [arg2spec(arg) for arg in args]
    pprint(r.solve(specs, [], features))
