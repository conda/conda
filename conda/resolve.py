from __future__ import print_function, division, absolute_import

import re
import sys
import logging
from collections import defaultdict
from functools import partial

from conda.utils import memoize
from conda.compat import itervalues, iteritems, string_types, zip_longest
from conda.logic import (false, true, sat, min_sat, generate_constraints,
    bisect_constraints, evaluate_eq, minimal_unsatisfiable_subset,
    MaximumIterationsError)
from conda.console import setup_handlers
from conda import config
from conda.toposort import toposort

log = logging.getLogger(__name__)
dotlog = logging.getLogger('dotupdate')
stdoutlog = logging.getLogger('stdoutlog')
stderrlog = logging.getLogger('stderrlog')
setup_handlers()

    # normalized_version() is needed by conda-env
def normalized_version(version):
    return VersionOrder(version)

version_check_re = re.compile(r'^[\*\.\+!_0-9a-z]+$')
version_split_re = re.compile('([0-9]+|[^0-9]+)')
class VersionOrder(object):
    '''
    This class implements an order relation between version strings.
    Version strings can contain the usual alphanumeric characters
    (A-Za-z0-9), separated into components by dots and underscores. Empty
    segments (i.e. two consecutive dots, a leading/trailing underscore)
    are not permitted. An optional epoch number - an integer
    followed by '!' - can preceed the actual version string
    (this is useful to indicate a change in the versioning
    scheme itself). Version comparison is case-insensitive.

    Conda supports six types of version strings:

    * Release versions contain only integers, e.g. '1.0', '2.3.5'.
    * Pre-release versions use additional letters such as 'a' or 'rc',
      for example '1.0a1', '1.2.beta3', '2.3.5rc3'.
    * Development versions are indicated by the string 'dev',
      for example '1.0dev42', '2.3.5.dev12'.
    * Post-release versions are indicated by the string 'post',
      for example '1.0post1', '2.3.5.post2'.
    * Tagged versions have a suffix that specifies a particular
      property of interest, e.g. '1.1.parallel'. Tags can be added
      to any of the preceding four types. As far as sorting is concerned,
      tags are treated like strings in pre-release versions.
    * An optional local version string separated by '+' can be appended
      to the main (upstream) version string. It is only considered
      in comparisons when the main versions are equal, but otherwise
      handled in exactly the same manner.

    To obtain a predictable version ordering, it is crucial to keep the
    version number scheme of a given package consistent over time.
    Specifically,

    * version strings should always have the same number of components
      (except for an optional tag suffix or local version string),
    * letters/strings indicating non-release versions should always
      occur at the same position.

    Before comparison, version strings are parsed as follows:

    * They are first split into epoch, version number, and local version
      number at '!' and '+' respectively. If there is no '!', the epoch is
      set to 0. If there is no '+', the local version is empty.
    * The version part is then split into components at '.' and '_'.
    * Each component is split again into runs of numerals and non-numerals
    * Subcomponents containing only numerals are converted to integers.
    * Strings are converted to lower case, with special treatment for 'dev'
      and 'post'.
    * When a component starts with a letter, the fillvalue 0 is inserted
      to keep numbers and strings in phase, resulting in '1.1.a1' == 1.1.0a1'.
    * The same is repeated for the local version part.

    Examples:

        1.2g.beta15.rc  =>  [[0], [1], [2, 'g'], [0, 'beta', 15], [0, 'rc']]
        1!2.15.1_ALPHA  =>  [[1], [2], [15], [1, '_alpha']]

    The resulting lists are compared lexicographically, where the following
    rules are applied to each pair of corresponding subcomponents:

    * integers are compared numerically
    * strings are compared lexicographically, case-insensitive
    * strings are smaller than integers, except
    * 'dev' versions are smaller than all corresponding versions of other types
    * 'post' versions are greater than all corresponding versions of other types
    * if a subcomponent has no correspondent, the missing correspondent is
      treated as integer 0 to ensure '1.1' == '1.1.0'.

    The resulting order is:

           0.4
         < 0.4.0
         < 0.4.1.rc
        == 0.4.1.RC   # case-insensitive comparison
         < 0.4.1
         < 0.5a1
         < 0.5b3
         < 0.5C1      # case-insensitive comparison
         < 0.5
         < 0.9.6
         < 0.960923
         < 1.0
         < 1.1dev1    # special case 'dev'
         < 1.1a1
         < 1.1.0dev1  # special case 'dev'
        == 1.1.dev1   # 0 is inserted before string
         < 1.1.a1
         < 1.1.0rc1
         < 1.1.0
        == 1.1
         < 1.1.0post1 # special case 'post'
        == 1.1.post1  # 0 is inserted before string
         < 1.1post1   # special case 'post'
         < 1996.07.12
         < 1!0.4.1    # epoch increased
         < 1!3.1.1.6
         < 2!0.4.1    # epoch increased again

    Some packages (most notably openssl) have incompatible version conventions.
    In particular, openssl interprets letters as version counters rather than
    pre-release identifiers. For openssl, the relation

      1.0.1 < 1.0.1a   =>   True   # for openssl

    holds, whereas conda packages use the opposite ordering. You can work-around
    this problem by appending a dash to plain version numbers:

      1.0.1a  =>  1.0.1post.a      # ensure correct ordering for openssl
    '''
    def __init__(self, version):
        # when fillvalue ==  0  =>  1.1 == 1.1.0
        # when fillvalue == -1  =>  1.1  < 1.1.0
        self.fillvalue = 0

        message = "Malformed version string '%s': " % version
        # version comparison is case-insensitive
        version = version.strip().rstrip().lower()
        # basic validity checks
        if version == '':
            raise ValueError("Empty version string.")
        if not version_check_re.match(version):
            raise ValueError(message + "invalid character(s).")
        self.norm_version = version

        # find epoch
        version = version.split('!')
        if len(version) == 1:
            # epoch not given => set it to '0'
            epoch = ['0']
        elif len(version) == 2:
            # epoch given, must be an integer
            if not version[0].isdigit():
                raise ValueError(message + "epoch must be an integer.")
            epoch = [version[0]]
        else:
            raise ValueError(message + "duplicated epoch separator '!'.")

        # find local version string
        version = version[-1].split('+')
        if len(version) == 1:
            # no local version
            self.local = ['0']
        elif len(version) == 2:
            # local version given
            self.local = version[1].replace('_', '.').split('.')
        else:
            raise ValueError(message + "duplicated local version separator '+'.")

        # split version
        self.version = epoch + version[0].replace('_', '.').split('.')

        # split components into runs of numerals and non-numerals,
        # convert numerals to int, handle special strings
        for v in (self.version, self.local):
            for k in range(len(v)):
                c = version_split_re.findall(v[k])
                if not c:
                    raise ValueError(message + "empty version component.")
                for j in range(len(c)):
                    if c[j].isdigit():
                        c[j] = int(c[j])
                    elif c[j] == 'post':
                        # ensure number < 'post' == infinity
                        c[j] = float('inf')
                    elif c[j] == 'dev':
                        # ensure '*' < 'DEV' < '_' < 'a' < number
                        # by upper-casing (all other strings are lower case)
                        c[j] = 'DEV'
                if v[k][0].isdigit():
                    v[k] = c
                else:
                    # components shall start with a number to keep numbers and
                    # strings in phase => prepend fillvalue
                    v[k] = [self.fillvalue] + c

    def __str__(self):
        return self.norm_version

    def __eq__(self, other):
        for t1, t2 in zip([self.version, self.local], [other.version, other.local]):
            for v1, v2 in zip_longest(t1, t2, fillvalue=[self.fillvalue]):
                for c1, c2 in zip_longest(v1, v2, fillvalue=self.fillvalue):
                    if c1 != c2:
                        return False
        return True

    def __ne__(self, other):
        return not (self == other)

    def __lt__(self, other):
        for t1, t2 in zip([self.version, self.local], [other.version, other.local]):
            for v1, v2 in zip_longest(t1, t2, fillvalue=[self.fillvalue]):
                for c1, c2 in zip_longest(v1, v2, fillvalue=self.fillvalue):
                    if isinstance(c1, string_types):
                        if not isinstance(c2, string_types):
                            # str < int
                            return True
                    else:
                        if isinstance(c2, string_types):
                            # not (int < str)
                            return False
                    # c1 and c2 have the same type
                    if c1 < c2:
                        return True
                    if c2 < c1:
                        return False
                    # c1 == c2 => advance
        # self == other
        return False

    def __gt__(self, other):
        return other < self

    def __le__(self, other):
        return not (other < self)

    def __ge__(self, other):
        return not (self < other)

class NoPackagesFound(RuntimeError):
    def __init__(self, msg, pkgs):
        super(NoPackagesFound, self).__init__(msg)
        self.pkgs = pkgs

# This RE matches the operators '==', '!=', '<=', '>=', '<', '>'
# followed by a version string. It rejects expressions like
# '<= 1.2' (space after operator), '<>1.2' (unknown operator),
# and '<=!1.2' (nonsensical operator).
version_relation_re = re.compile(r'(==|!=|<=|>=|<|>)(?![=<>!])(\S+)$')
def ver_eval(version, constraint):
    """
    return the Boolean result of a comparison between two versions, where the
    second argument includes the comparison operator.  For example,
    ver_eval('1.2', '>=1.1') will return True.
    """
    a = version
    m = version_relation_re.match(constraint)
    if m is None:
        raise RuntimeError("Did not recognize version specification: %r" %
                           constraint)
    op, b = m.groups()
    return eval('VersionOrder("%s") %s VersionOrder("%s")' % (a, op, b))

class VersionSpecAtom(object):

    def __init__(self, spec):
        assert '|' not in spec
        assert ',' not in spec
        self.spec = spec
        if spec.startswith(('=', '<', '>', '!')):
            self.regex = False
        else:
            rx = spec.replace('.', r'\.')
            rx = rx.replace('+', r'\+')
            rx = rx.replace('*', r'.*')
            rx = r'(%s)$' % rx
            self.regex = re.compile(rx)

    def match(self, version):
        if self.regex:
            return bool(self.regex.match(version))
        else:
            return ver_eval(version, self.spec)

class VersionSpec(object):

    def __init__(self, spec):
        assert '|' not in spec
        self.constraints = [VersionSpecAtom(vs) for vs in spec.split(',')]

    def match(self, version):
        return all(c.match(version) for c in self.constraints)


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
        self.norm_version = VersionOrder(self.version)
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
        # FIXME: 'self.build' and 'other.build' are intentionally swapped
        # FIXME: see https://github.com/conda/conda/commit/3cc3ecc662914abe1d98b8d9c4caaa7c932a838e
        # FIXME: This should be reverted when the underlying problem is solved.
        return ((self.norm_version, self.build_number, other.build) <
                (other.norm_version, other.build_number, self.build))

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

class Resolve(object):

    def __init__(self, index):
        self.index = index
        self.groups = defaultdict(list)  # map name to list of filenames
        for fn, info in iteritems(index):
            self.groups[info['name']].append(fn)
        self.msd_cache = {}
        self.clear_filter()

    def clear_filter(self):
        self.filter_ = defaultdict(lambda:True)
        self.get_pkgs_ = {}

    def prune_packages(self, specs):
        log.debug('Beginning the pruning process')
        touched = defaultdict(bool)
        valid = {}

        def filter_group(matches):
            match1 = next(x for x in matches)
            name = match1.name

            first = False
            nold = nnew = 0
            group = self.groups[name]
            for fn in group:
                sat = valid.get(fn, None)
                if sat is None:
                    first = sat = True
                nold += sat
                # Prune packages that don't match any of the patterns
                if sat:
                    sat = any(m.match(fn) for m in matches)
                # Prune packages with missing dependencies
                if sat:
                    sat = all(any(valid.get(f2, True) and ms.match(f2)
                                  for f2 in self.find_matches(ms, True))
                              for ms in self.ms_depends(fn) if ms.name in self.groups)
                nnew += sat
                valid[fn] = sat

            reduced = nnew < nold
            if reduced:
                dotlog.debug('%s: pruned from %d -> %d' % (name, nold, nnew))
                if nnew == 0:
                    return True
            elif not first or nold == 0:
                return False

            # Perform the same filtering steps on any dependencies shared across
            # *all* packages in the group. Even if just one of the packages does
            # not have a particular dependency, it must be ignored in this pass.
            cdeps = {}
            for fn in group:
                if valid[fn]:
                    for m2 in self.ms_depends(fn):
                        if m2.name in self.groups:
                            cdeps.setdefault(m2.name,[]).append(m2)
            for mname, deps in iteritems(cdeps):
                if len(deps) == nnew:
                    filter_group(deps)
            return reduced

        def is_valid(fn):
            val = valid.get(fn, None)
            if val is None:
                val = valid[fn] = True
                for ms in self.ms_depends(fn):
                    if not any(is_valid(f2) for f2 in self.find_matches(ms, True)):
                        val = False
                        break
                valid[fn] = val
            return val

        def touch(fn, force=False):
            val = touched.get(fn, None)
            if val is None or (force and not val):
                val = touched[fn] = force or is_valid(fn)
                if val:
                    for ms in self.ms_depends(fn):
                        for f2 in self.find_matches(ms, True):
                            touch(f2, force)
            return val

        # Iterate in the filtering process until no more progress is made
        mspecs = [MatchSpec(s) for s in specs]
        while sum(filter_group([ms]) for ms in mspecs):
            pass

        # Now touch all of the packages to bring in the weak dependencies
        for ms in mspecs:
            if sum(touch(fn) for fn in self.find_matches(ms, True)) == 0:
                dotlog.debug('Spec %s cannot be satisfied' % ms.spec)
                return False

        self.filter_ = touched
        self.get_pkgs_ = {}
        return True

    def find_matches(self, ms, all=True):
        for fn in self.groups[ms.name]:
            if self.filter_[fn] and ms.match(fn):
                yield fn

    def ms_depends(self, fn):
        # We can't use @memoize here because this cache is modified
        # in update_with_features as well
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

    # Changed to manual memoization so that we can reset if we add/change the filter.
    def get_pkgs(self, ms, max_only=False):
        key = (ms,max_only)
        if key in self.get_pkgs_:
            return self.get_pkgs_[key]
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
            pkgs = ret
        self.get_pkgs_[key] = pkgs
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
                        "for %s: %s" % (ms, ', '.join(notfound)), [ms.spec] + notfound)

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

    def generate_version_eq(self, v, dists, installed_dists, specs,
        include0=False, update_deps=True):
        groups = defaultdict(list)  # map name to list of filenames
        for fn in sorted(dists):
            groups[self.index[fn]['name']].append(fn)

        eq = []
        max_rhs = 0
        for filenames in sorted(itervalues(groups)):
            pkgs = sorted(filenames, key=lambda i: dists[i], reverse=True)
            if (not update_deps and not any(s.split()[0] == pkgs[0].rsplit('-', 2)[0] for s in specs)):
                rearrange = True
                for d in installed_dists:
                    if d in pkgs:
                        break
                else:
                    # It isn't already installed
                    rearrange = False
                if rearrange:
                    idx = pkgs.index(d)
                    # For example, if the versions are 1.0, 2.0, 3.0, 4.0, and
                    # 5.0, and 3.0 is installed, this prefers 3.0 > 4.0 > 5.0
                    # > 2.0 > 1.0.
                    pkgs = [d] + list(reversed(pkgs[:idx])) + pkgs[idx+1:]
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

    def get_dists(self, specs, max_only=False, filtered=False):
        dists = {}
        if filtered:
            filtered = self.prune_packages(specs)
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
                if filtered:
                    self.clear_filter()
                raise NoPackagesFound("Could not find some dependencies for %s: %s" % (spec, ', '.join(notfound)), [spec] + notfound)
        if filtered:
            self.clear_filter()
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

    def solve2(self, specs, features, installed=(), guess=True, alg='BDD',
        returnall=False, minimal_hint=False, unsat_only=False, update_deps=True,
        try_max_only=None):
        log.debug("Solving for %s" % str(specs))
        log.debug("Features: %s" % str(features))
        log.debug("Installed: %s" % str(installed))

        # This won't packages that aren't in the index, but there isn't much
        # we can do with such packages here anyway.
        installed_dists = {pkg: Package(pkg, self.index[pkg]) for pkg in
            installed if pkg in self.index}

        if try_max_only is None:
            if unsat_only or update_deps:
                try_max_only = False
            else:
                try_max_only = True

        # XXX: Should try_max_only use the filtered list?
        if try_max_only:
            try:
                dists = self.get_dists(specs, max_only=True, filtered=False)
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
                try:
                    solutions = min_sat(clauses, alg='iterate',
                        raise_on_max_n=True)
                except MaximumIterationsError:
                    pass
                else:
                    if len(solutions) == 1:
                        ret = [w[lit] for lit in solutions.pop(0) if 0 < lit <= m]
                        if returnall:
                            return [ret]
                        return ret

        dists = self.get_dists(specs, filtered=True)

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
        eq, max_rhs = self.generate_version_eq(v, dists, installed_dists,
            specs, update_deps=update_deps)


        # Second common case, check if it's unsatisfiable
        dotlog.debug("Checking for unsatisfiability")
        solution = sat(clauses)

        if not solution:
            if guess:
                if minimal_hint:
                    stderrlog.info('\nError: Unsatisfiable package '
                        'specifications.\nGenerating minimal hint: \n')
                    sys.exit(self.minimal_unsatisfiable_subset(clauses, v,
            w))
                else:
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
        try:
            solutions = min_sat(clauses | constraints, N=m + 1, alg='iterate',
                raise_on_max_n=True)
        except MaximumIterationsError:
            solutions = min_sat(clauses | constraints, N=m + 1, alg='sorter')
        assert solutions, (specs, features)

        if len(solutions) > 1:
            stdoutlog.info('\nWarning: %s possible package resolutions (only showing differing packages):\n' % len(solutions))
            pretty_solutions = [{w[lit] for lit in sol if 0 < lit <= m} for
                sol in solutions]
            common  = set.intersection(*pretty_solutions)
            for sol in pretty_solutions:
                stdoutlog.info('\t%s,\n' % sorted(sol - common))

        log.debug("Older versions in the solution(s):")
        for sol in solutions:
            log.debug([(i, w[j]) for i, j in eq if j in sol])
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

        # Don't show the dots from solve2 in normal mode but do show the
        # dotlog messages with --debug
        dotlog.setLevel(logging.INFO)

        def sat(specs):
            try:
                self.solve2(specs, features, guess=False, unsat_only=True)
            except RuntimeError:
                return False
            return True

        hint = minimal_unsatisfiable_subset(specs, sat=sat, log=True)
        if not hint:
            return ''
        if len(hint) == 1:
            # TODO: Generate a hint from the dependencies.
            ret = (("\nHint: '{0}' has unsatisfiable dependencies (see 'conda "
                "info {0}')").format(hint[0].split()[0]))
        else:
            ret = """
Hint: the following packages conflict with each other:
  - %s

Use 'conda info %s' etc. to see the dependencies for each package.""" % ('\n  - '.join(hint), hint[0].split()[0])

        if features:
            ret += """

Note that the following features are enabled:
  - %s
""" % ('\n  - '.join(features))
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
                res.update(self.track_features(fn))
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
              minimal_hint=False, update_deps=True):
        if installed is None:
            installed = []
        if features is None:
            features = self.installed_features(installed)
        for spec in specs:
            if sys.platform == 'win32' and spec == 'python':
                continue
            # XXX: This does not work when a spec only contains the name,
            # and different versions of the package have different features.
            ms = MatchSpec(spec)
            for pkg in self.get_pkgs(ms, max_only=max_only):
                fn = pkg.fn
                features.update(self.track_features(fn))
        log.debug('specs=%r  features=%r' % (specs, features))
        for spec in specs:
            for pkg in self.get_pkgs(MatchSpec(spec), max_only=max_only):
                fn = pkg.fn
                self.update_with_features(fn, features)

        stdoutlog.info("Solving package specifications ...")
        try:
            return self.explicit(specs) or self.solve2(specs, features,
                installed, minimal_hint=minimal_hint, update_deps=update_deps)
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
