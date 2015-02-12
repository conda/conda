from __future__ import print_function, division, absolute_import

import re
import sys
import logging
from itertools import combinations
from collections import defaultdict
from functools import partial

from conda import verlib
from conda.utils import memoize
from conda.compat import itervalues, iteritems
from conda.logic import (false, true, sat, min_sat, generate_constraints,
    bisect_constraints, evaluate_eq, minimal_unsatisfiable_subset)
from conda.console import setup_handlers
from conda import config
from conda.toposort import toposort

log = logging.getLogger(__name__)
dotlog = logging.getLogger('dotupdate')
stdoutlog = logging.getLogger('stdoutlog')
stderrlog = logging.getLogger('stderrlog')
setup_handlers()


def normalized_version(version):
    version = version.replace('rc', '.dev99999')
    try:
        return verlib.NormalizedVersion(version)
    except verlib.IrrationalVersionError:
        suggested_version = verlib.suggest_normalized_version(version)
        if suggested_version:
            return verlib.NormalizedVersion(suggested_version)
        return version


class NoPackagesFound(RuntimeError):
    def __init__(self, msg, pkgs):
        super(NoPackagesFound, self).__init__(msg)
        self.pkgs = pkgs

const_pat = re.compile(r'([=<>!]{1,2})(\S+)$')
def ver_eval(version, constraint):
    """
    return the Boolean result of a comparison between two versions, where the
    second argument includes the comparison operator.  For example,
    ver_eval('1.2', '>=1.1') will return True.
    """
    a = version
    m = const_pat.match(constraint)
    if m is None:
        raise RuntimeError("Did not recognize version specification: %r" %
                           constraint)
    op, b = m.groups()
    na = normalized_version(a)
    nb = normalized_version(b)
    if op == '==':
        try:
            return na == nb
        except TypeError:
            return a == b
    elif op == '>=':
        try:
            return na >= nb
        except TypeError:
            return a >= b
    elif op == '<=':
        try:
            return na <= nb
        except TypeError:
            return a <= b
    elif op == '>':
        try:
            return na > nb
        except TypeError:
            return a > b
    elif op == '<':
        try:
            return na < nb
        except TypeError:
            return a < b
    elif op == '!=':
        try:
            return na != nb
        except TypeError:
            return a != b
    else:
        raise RuntimeError("Did not recognize version comparison operator: %r" %
                           constraint)


class VersionSpec(object):

    def __init__(self, spec):
        assert '|' not in spec
        if spec.startswith(('=', '<', '>', '!')):
            self.regex = False
            self.constraints = spec.split(',')
        else:
            self.regex = True
            rx = spec.replace('.', r'\.')
            rx = rx.replace('*', r'.*')
            rx = r'(%s)$' % rx
            self.pat = re.compile(rx)

    def match(self, version):
        if self.regex:
            return bool(self.pat.match(version))
        else:
            return all(ver_eval(version, c) for c in self.constraints)


class MatchSpec(object):

    def __init__(self, spec):
        self.spec = spec
        parts = spec.split()
        self.strictness = len(parts)
        assert 1 <= self.strictness <= 3, repr(spec)
        self.name = parts[0]
        if self.strictness == 2:
            self.vspecs = [VersionSpec(s) for s in parts[1].split('|')]
        elif self.strictness == 3:
            self.ver_build = tuple(parts[1:3])

    def match(self, fn):
        assert fn.endswith('.tar.bz2')
        name, version, build = fn[:-8].rsplit('-', 2)
        if name != self.name:
            return False
        if self.strictness == 1:
            return True
        elif self.strictness == 2:
            return any(vs.match(version) for vs in self.vspecs)
        elif self.strictness == 3:
            return bool((version, build) == self.ver_build)

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
        self.norm_version = normalized_version(self.version)
        self.info = info

    def _asdict(self):
        result = self.info.copy()
        result['fn'] = self.fn
        result['norm_version'] = str(self.norm_version)
        return result

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


class Resolve(object):

    def __init__(self, index):
        self.index = index
        self.groups = defaultdict(list)  # map name to list of filenames
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
            if not 'depends' in self.index[fn]:
                raise NoPackagesFound('Bad metadata for %s' % fn, [fn])
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
    def get_pkgs(self, ms, max_only=False):
        pkgs = [Package(fn, self.index[fn]) for fn in self.find_matches(ms)]
        if not pkgs:
            raise NoPackagesFound("No packages found in current %s channels matching: %s" % (config.subdir, ms), [ms.spec])
        if max_only:
            maxpkg = max(pkgs)
            ret = []
            for pkg in pkgs:
                try:
                    if (pkg.name, pkg.norm_version, pkg.build_number) == \
                       (maxpkg.name, maxpkg.norm_version, maxpkg.build_number):
                        ret.append(pkg)
                except TypeError:
                    # They are not equal
                    pass
            return ret

        return pkgs

    def get_max_dists(self, ms):
        pkgs = self.get_pkgs(ms, max_only=True)
        if not pkgs:
            raise NoPackagesFound("No packages found in current %s channels matching: %s" % (config.subdir, ms), [ms.spec])
        for pkg in pkgs:
            yield pkg.fn

    def all_deps(self, root_fn, max_only=False):
        res = {}

        def add_dependents(fn1, max_only=False):
            for ms in self.ms_depends(fn1):
                found = False
                notfound = []
                for pkg2 in self.get_pkgs(ms, max_only=max_only):
                    if pkg2.fn in res:
                        found = True
                        continue
                    res[pkg2.fn] = pkg2
                    try:
                        if ms.strictness < 3:
                            add_dependents(pkg2.fn, max_only=max_only)
                    except NoPackagesFound as e:
                        for pkg in e.pkgs:
                            if pkg not in notfound:
                                notfound.append(pkg)
                        if pkg2.fn in res:
                            del res[pkg2.fn]
                    else:
                        found = True

                if not found:
                    raise NoPackagesFound("Could not find some dependencies "
                        "for %s: %s" % (ms, ', '.join(notfound)), notfound)

        add_dependents(root_fn, max_only=max_only)
        return res

    def gen_clauses(self, v, dists, specs, features):
        groups = defaultdict(list)  # map name to list of filenames
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
                        yield (-v1, -v2)

        for fn1 in dists:
            for ms in self.ms_depends(fn1):
                # ensure dependencies are installed
                # e.g. numpy-1.7 IMPLIES (python-2.7.3 OR python-2.7.4 OR ...)
                clause = [-v[fn1]]
                for fn2 in self.find_matches(ms):
                    if fn2 in dists:
                        clause.append(v[fn2])
                assert len(clause) > 1, '%s %r' % (fn1, ms)
                yield tuple(clause)

                for feat in features:
                    # ensure that a package (with required name) which has
                    # the feature is installed
                    # e.g. numpy-1.7 IMPLIES (numpy-1.8[mkl] OR numpy-1.7[mkl])
                    clause = [-v[fn1]]
                    for fn2 in groups[ms.name]:
                         if feat in self.features(fn2):
                             clause.append(v[fn2])
                    if len(clause) > 1:
                        yield tuple(clause)

                # Don't install any package that has a feature that wasn't requested.
                for fn in self.find_matches(ms):
                    if fn in dists and self.features(fn) - features:
                        yield (-v[fn],)

        for spec in specs:
            ms = MatchSpec(spec)
            # ensure that a matching package with the feature is installed
            for feat in features:
                # numpy-1.7[mkl] OR numpy-1.8[mkl]
                clause = [v[fn] for fn in self.find_matches(ms)
                          if fn in dists and feat in self.features(fn)]
                if len(clause) > 0:
                    yield tuple(clause)

            # Don't install any package that has a feature that wasn't requested.
            for fn in self.find_matches(ms):
                if fn in dists and self.features(fn) - features:
                    yield (-v[fn],)

            # finally, ensure a matching package itself is installed
            # numpy-1.7-py27 OR numpy-1.7-py26 OR numpy-1.7-py33 OR
            # numpy-1.7-py27[mkl] OR ...
            clause = [v[fn] for fn in self.find_matches(ms)
                      if fn in dists]
            assert len(clause) >= 1, ms
            yield tuple(clause)

    def generate_version_eq(self, v, dists, include0=False):
        groups = defaultdict(list)  # map name to list of filenames
        for fn in sorted(dists):
            groups[self.index[fn]['name']].append(fn)

        eq = []
        max_rhs = 0
        for filenames in sorted(itervalues(groups)):
            pkgs = sorted(filenames, key=lambda i: dists[i], reverse=True)
            i = 0
            prev = pkgs[0]
            for pkg in pkgs:
                try:
                    if (dists[pkg].name, dists[pkg].norm_version,
                        dists[pkg].build_number) != (dists[prev].name,
                            dists[prev].norm_version, dists[prev].build_number):
                        i += 1
                except TypeError:
                    i += 1
                if i or include0:
                    eq += [(i, v[pkg])]
                prev = pkg
            max_rhs += i

        return eq, max_rhs

    def get_dists(self, specs, max_only=False):
        dists = {}
        for spec in specs:
            found = False
            notfound = []
            for pkg in self.get_pkgs(MatchSpec(spec), max_only=max_only):
                if pkg.fn in dists:
                    found = True
                    continue
                try:
                    dists.update(self.all_deps(pkg.fn, max_only=max_only))
                except NoPackagesFound as e:
                    # Ignore any package that has nonexisting dependencies.
                    for pkg in e.pkgs:
                        if pkg not in notfound:
                            notfound.append(pkg)
                else:
                    dists[pkg.fn] = pkg
                    found = True
            if not found:
                raise NoPackagesFound("Could not find some dependencies for %s: %s" % (spec, ', '.join(notfound)), notfound)

        return dists

    def graph_sort(self, must_have):

        def lookup(value):
            index_data = self.index.get('%s.tar.bz2' % value, {})
            return {item.split(' ', 1)[0] for item in index_data.get('depends', [])}

        digraph = {}

        for key, value in must_have.items():
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

    def solve2(self, specs, features, guess=True, alg='BDD',
        returnall=False, minimal_hint=False, unsat_only=False):

        log.debug("Solving for %s" % str(specs))

        # First try doing it the "old way", i.e., just look at the most recent
        # version of each package from the specs. This doesn't handle the more
        # complicated cases that the pseudo-boolean solver does, but it's also
        # much faster when it does work.

        try:
            dists = self.get_dists(specs, max_only=True)
        except NoPackagesFound:
            # Handle packages that are not included because some dependencies
            # couldn't be found.
            pass
        else:
            v = {}  # map fn to variable number
            w = {}  # map variable number to fn
            i = -1  # in case the loop doesn't run
            for i, fn in enumerate(sorted(dists)):
                v[fn] = i + 1
                w[i + 1] = fn
            m = i + 1

            dotlog.debug("Solving using max dists only")
            clauses = set(self.gen_clauses(v, dists, specs, features))
            solutions = min_sat(clauses)

            if len(solutions) == 1:
                ret = [w[lit] for lit in solutions.pop(0) if 0 < lit <= m]
                if returnall:
                    return [ret]
                return ret

        dists = self.get_dists(specs)

        v = {}  # map fn to variable number
        w = {}  # map variable number to fn
        i = -1  # in case the loop doesn't run
        for i, fn in enumerate(sorted(dists)):
            v[fn] = i + 1
            w[i + 1] = fn
        m = i + 1

        clauses = set(self.gen_clauses(v, dists, specs, features))
        if not clauses:
            if returnall:
                return [[]]
            return []
        eq, max_rhs = self.generate_version_eq(v, dists)


        # Second common case, check if it's unsatisfiable
        dotlog.debug("Checking for unsatisfiability")
        solution = sat(clauses)

        if not solution:
            if guess:
                if minimal_hint:
                    stderrlog.info('\nError: Unsatisfiable package '
                        'specifications.\nGenerating hint: \n')
                    sys.exit(self.minimal_unsatisfiable_subset(clauses, v,
            w))
                else:
                    if len(specs) <= 10: # TODO: Add a way to override this
                        stderrlog.info('\nError: Unsatisfiable package '
                            'specifications.\nGenerating hint: \n')
                        sys.exit(self.guess_bad_solve(specs, features))
            raise RuntimeError("Unsatisfiable package specifications")

        if unsat_only:
            return True

        log.debug("Using alg %s" % alg)

        def version_constraints(lo, hi):
            return set(generate_constraints(eq, m, [lo, hi], alg=alg))

        log.debug("Bisecting the version constraint")
        evaluate_func = partial(evaluate_eq, eq)
        constraints = bisect_constraints(0, max_rhs, clauses,
            version_constraints, evaluate_func=evaluate_func)

        # Only relevant for build_BDD
        if constraints and false in constraints:
            # XXX: This should *never* happen. build_BDD only returns false
            # when the linear constraint is unsatisfiable, but any linear
            # constraint can equal 0, by setting all the variables to 0.
            solution = []
        else:
            if constraints and true in constraints:
                constraints = set([])

        dotlog.debug("Finding the minimal solution")
        solutions = min_sat(clauses | constraints, N=m + 1)
        assert solutions, (specs, features)

        if len(solutions) > 1:
            stdoutlog.info('Warning: %s possible package resolutions:' % len(solutions))
            for sol in solutions:
                stdoutlog.info('\t' + str([w[lit] for lit in sol if 0 < lit <= m]))

        if returnall:
            return [[w[lit] for lit in sol if 0 < lit <= m] for sol in solutions]
        return [w[lit] for lit in solutions.pop(0) if 0 < lit <= m]

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

    def guess_bad_solve(self, specs, features):
        # TODO: Check features as well
        from conda.console import setup_verbose_handlers
        setup_verbose_handlers()
        # Don't show the dots in normal mode but do show the dotlog messages
        # with --debug
        dotlog.setLevel(logging.WARN)
        hint = []
        # Try to find the largest satisfiable subset
        found = False
        if len(specs) > 10:
            stderrlog.info("WARNING: This could take a while. Type Ctrl-C to exit.\n")

        for i in range(len(specs), 0, -1):
            if found:
                logging.getLogger('progress.stop').info(None)
                break

            # Too lazy to compute closed form expression
            ncombs = len(list(combinations(specs, i)))
            logging.getLogger('progress.start').info(ncombs)
            for j, comb in enumerate(combinations(specs, i), 1):
                try:
                    logging.getLogger('progress.update').info(('%s/%s' % (j,
                        ncombs), j))
                    self.solve2(comb, features, guess=False, unsat_only=True)
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
            return ("\nHint: %s has a conflict with the remaining packages" %
                    hint[0])
        return ("""
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
            if fn not in self.index:
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

    def find_substitute(self, installed, features, fn, max_only=False):
        """
        Find a substitute package for `fn` (given `installed` packages)
        which does *NOT* have `features`.  If found, the substitute will
        have the same package name and version and its dependencies will
        match the installed packages as closely as possible.
        If no substitute is found, None is returned.
        """
        name, version, unused_build = fn.rsplit('-', 2)
        candidates = {}
        for pkg in self.get_pkgs(MatchSpec(name + ' ' + version), max_only=max_only):
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

    def solve(self, specs, installed=None, features=None, max_only=False,
              minimal_hint=False):
        if installed is None:
            installed = []
        if features is None:
            features = self.installed_features(installed)
        for spec in specs:
            ms = MatchSpec(spec)
            for pkg in self.get_pkgs(ms, max_only=max_only):
                fn = pkg.fn
                features.update(self.track_features(fn))
        log.debug('specs=%r  features=%r' % (specs, features))
        for spec in specs:
            for pkg in self.get_pkgs(MatchSpec(spec), max_only=max_only):
                fn = pkg.fn
                self.update_with_features(fn, features)

        stdoutlog.info("Solving package specifications: ")
        try:
            return self.explicit(specs) or self.solve2(specs, features,
                                                       minimal_hint=minimal_hint)
        except RuntimeError:
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

    features = set(['mkl']) if opts.mkl else set()
    specs = [arg2spec(arg) for arg in args]
    pprint(r.solve(specs, [], features))
