from __future__ import print_function, division, absolute_import

import re
import sys
import logging
from collections import defaultdict
from itertools import chain

from conda.utils import memoize
from conda.compat import iterkeys, itervalues, iteritems, string_types, zip_longest
from conda.logic import (sat, optimize, minimal_unsatisfiable_subset)
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

def dashlist(iter):
    return ''.join('\n  - ' + str(x) for x in iter)

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
            self.vspecs = [VersionSpec(s) for s in parts[1].split('|')]
        elif self.strictness == 3:
            self.ver_build = tuple(parts[1:3])
        self.target = target
        self.optional = optional
        self.parent = parent
        return self

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

def build_groups(index, features=True):
    groups = {}
    for fn, info in iteritems(index):
        if isinstance(info, Package):
            info = info.info
        nm = info['name']
        groups.setdefault(nm,[]).append(fn)
        tfeats = info.get('track_features','').split() if features else []
        for feat in tfeats:
            groups.setdefault('@'+feat,[]).append(fn)
    return groups

class Resolve(object):

    def __init__(self, index):
        self.index = index.copy()
        for fn, info in iteritems(index):
            for fstr in info.get('track_features','').split():
                if fstr not in index:
                    self.index[fstr+'@'] = {
                        'name':fstr+'@', 'version':'1.0', 
                        'build':'0', 'build_number':0,
                        'depends':[], 'track_features':fstr
                    }
            for fstr in iterkeys(info.get('with_features_depends',{})):
                fn2 = fn + '[' + fstr + ']'
                self.index[fn2] = info
        self.groups = build_groups(self.index)
        self.ms_cache = {}


    def get_dists(self, specs, filtered=True, wrap=True, sat_only=False):
        log.debug('Beginning the pruning process')

        specs = map(MatchSpec, specs)
        len0 = len(specs)
        bad_deps = []
        valid = {}
        unsat = []

        def filter_group(matches, top):
            # Ignore optional specifications
            if any(ms.optional for ms in matches):
                matches = [ms for ms in matches if not ms.optional]
                if not matches:
                    return False

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
                    sat = any(self.match(ms, fn) for ms in matches)
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
                if not ms.optional:
                    for fn in self.groups.get(ms.name, []):
                        if valid.get(fn, True):
                            feats.update(self.track_features(fn))
            pruned = False
            log.debug('Possible installed features: '+str(tuple(feats)))
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
                                bad_deps.append((ms,'@'+name))
            return pruned

        # Initial scan to rule out missing packages
        for ms in specs:
            if not ms.optional and not any(True for _ in self.find_matches(ms)):
                bad_deps.append(ms)
            if bad_deps:
                raise NoPackagesFound(
                    "No packages found in current %s channels matching: %s" % 
                    (config.subdir, ' '.join(map(str,bad_deps))), bad_deps)

        # Iterate in the filtering process until no more progress is made
        if filtered:
            pruned = True
            while pruned:
                pruned = prune_features()
                for s in list(specs):
                    pruned += filter_group([s], None)

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
            print(unsat,hint)
            hint = ['  - %s'%str(x) for x in set(chain(unsat, hint))]
            hint = (['The following specifications were found to be in conflict:'] + hint 
                + ['Use "conda info <package>" to see the dependencies for each package.'])
            sys.exit('\n'.join(hint))

        dists = {fn:info for fn,info in iteritems(self.index) if touched.get(fn)}
        if wrap:
            dists = {fn:Package(fn,info) for fn,info in iteritems(dists)}
        return dists, specs


    def match(self, ms, fn):
        ms = MatchSpec(ms)
        if fn[-1] == ']':
            fn = fn.rsplit('[',1)[0]
        if ms.name[0] == '@':
            return ms.name[1:] in self.track_features(fn)
        return ms.match(self.index[fn])

    def find_matches(self, ms, groups=None):
        ms = MatchSpec(ms)
        for fn in (groups or self.groups).get(ms.name, []):
            if self.match(ms, fn):
                yield fn

    @memoize
    def ms_depends(self, fn):
        if fn[-1] == ']':
            fn2, fstr = fn[:-1].split('[')
            fdeps = {d.name:d for d in self.ms_depends(fn2)}
            for dep in self.index[fn2]['with_features_depends'][fstr]:
                dep = MatchSpec(dep)
                fdeps[dep.name] = dep
            deps = fdeps.values()
        else:
            deps = [MatchSpec(d) for d in self.index[fn].get('depends',[])]
        deps.extend(MatchSpec('@' + feat) for feat in self.features(fn))
        return deps

    @memoize
    def version_key(self, fn):
        rec = self.index.get(fn, None)
        if rec is None:
            return None
        return (VersionOrder(rec['version']), len(self.features(fn)), rec['build_number'], rec['build'])

    @memoize
    def features(self, fn):
        if fn[-1] == ']':
            return self.features(fn.rsplit('[',1)[0])
        return set(self.index[fn].get('features', '').split())

    @memoize
    def track_features(self, fn):
        if fn[-1] == ']':
            return self.track_features(fn.rsplit('[',1)[0])
        return set(self.index[fn].get('track_features', '').split())

    @memoize
    def get_pkgs(self, ms, emptyok=False):
        ms = MatchSpec(ms)
        pkgs = [Package(fn, self.index[fn]) for fn in self.find_matches(ms) if '@' not in fn]
        if not pkgs and not emptyok:
            raise NoPackagesFound("No packages found in current %s channels matching: %s" % (config.subdir, ms), [ms.spec])
        return pkgs

    def gen_clauses(self, v, groups, specs):
        specs = map(MatchSpec, specs)
        for name, group in iteritems(groups):
            if name[0] == '@':
                # Ensure at least one track feature package is installed
                # if a dependency is activated
                clause = [v[fn2] for fn2 in self.find_matches(MatchSpec(name), groups)]
                yield tuple([-v[name]] + clause)
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
                    if ms.name[0] == '@':
                        yield (nval, v[ms.name])
                    else:
                        clause = [v[fn2] for fn2 in self.find_matches(ms, groups)]
                        assert clause, '%s %r' % (fn1, ms)
                        yield tuple([nval] + clause)

        # Ensure that at least one package is installed matching each spec
        # fn1 OR fn2 OR fn3 OR ... OR fnN
        for ms in specs:
            if not ms.optional:
                clause = [v[fn] for fn in self.find_matches(ms, groups)]
                assert len(clause) >= 1, ms
                yield tuple(clause)

    def generate_feature_eq(self, v, groups, specs):
        may_omit = set()
        sdict = {s.name:s for s in map(MatchSpec, specs)}
        for name in iterkeys(groups):
            if name[0] == '@':
                if name not in sdict or sdict[name].optional:
                    may_omit.add(name[1:])
        if may_omit:
            for name, ms in iteritems(sdict):
                if name[0] != '@' and not ms.optional:
                    for fn in self.find_matches(ms, groups):
                        may_omit -= self.track_features(fn)
                        if not may_omit:
                            break
        return [(1,v['@'+name]) for name in may_omit]

    def generate_version_eq(self, v, groups, specs, include0=False):
        eq = []
        sdict = {s.name:s for s in map(MatchSpec, specs)}
        for name, pkgs in iteritems(groups):
            if name[0] == '@':
                continue
            pkg_ver = sorted([(self.version_key(p),p) for p in pkgs], reverse=True)
            # If the "target" field in the MatchSpec is supplied, that means we want
            # to minimize the changes to the currently installed package. We prefer
            # any upgrade over any downgrade, but beyond that we want minimal change.
            ms = sdict.get(name)
            if ms and ms.target:
                dkey = (self.version_key(ms.target),ms.target)
                new_ver = [p for p in pkg_ver if p >= dkey]
                new_ver.extend(reversed([p for p in pkg_ver if p < dkey]))
                pkg_ver = new_ver
            wgt = 1 if not ms or ms.optional else 4
            i = 0
            prev = None
            for nkey, pkg in pkg_ver:
                if prev and prev != nkey:
                    i += wgt
                if i or include0:
                    eq += [(i, v[pkg])]
                prev = nkey
        return eq

    def generate_package_count(self, v, groups, specs):
        eq = []
        snames = {s.name for s in map(MatchSpec, specs)}
        for name, pkgs in iteritems(groups):
            if name not in snames and name[0] != '@':
                eq.extend((1,v[pkg]) for pkg in pkgs)
        return eq

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

    def build_vw(self, groups):
        v = {}  # map fn to variable number
        w = {}  # map variable number to fn
        i = -1  # in case the loop doesn't run
        for name, group in iteritems(groups):
            if name[0] == '@':
                i += 1
                v[name] = i + 1
                w[i + 1] = name
            else:
                for fn in group:
                    i += 1
                    v[fn] = i + 1
                    w[i + 1] = fn
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
            dists = self.get_dists(specs, wrap=False)
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
        hint = map(str, hint)
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
        specs = map(MatchSpec, specs)
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

    @memoize
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
              guess=True, minimal_hint=False, alg='BDD'):

        stdoutlog.info("Solving package specifications: ")
        res = self.explicit(specs)
        if res is not None:
            return res

        # If update_deps=True, set the target package in MatchSpec so that
        # the solver can minimize the version change. If update_deps=False,
        # fix the version and build so that no change is possible.
        specs = map(MatchSpec, specs)
        snames = {s.name for s in specs}
        for pkg in installed:
            rec = self.index.get(pkg)
            if rec is None:
                continue
            name = rec['name']
            if name in snames:
                continue
            if update_deps:
                spec = MatchSpec(name, target=pkg)
            else:
                spec = MatchSpec(name+' '+rec['version']+' '+rec['build'])
            specs.append(spec)
            snames.add(spec)
        dotlog.debug("Solving for %s" % specs)

        try:
            dists, new_specs = self.get_dists(specs, wrap=False)
        except NoPackagesFound:
            raise

        # Check if satisfiable
        dotlog.debug('Checking satisfiability')
        groups = build_groups(dists)
        m, v, w = self.build_vw(groups)
        clauses = set(self.gen_clauses(v, groups, specs))
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

        dotlog.debug('Optimizing feature count')
        eq_features = self.generate_feature_eq(v, groups, new_specs)
        clauses, solution = optimize(eq_features, clauses, solution)

        dotlog.debug('Optimizing versions')
        eq_version = self.generate_version_eq(v, groups, new_specs)
        clauses, solution = optimize(eq_version, clauses, solution)

        dotlog.debug('Optimizing dependency count')
        eq_packages = self.generate_package_count(v, groups, new_specs)
        clauses, solution = optimize(eq_packages, clauses, solution, trymin=False)

        dotlog.debug('Looking for alternate solutions')
        solutions = [solution]
        nsol = 1
        while True:
            nclause = tuple(-q for q in solution if 0 < q <= m)
            clauses.add(nclause)
            solution = sat(clauses)
            if solution is None:
                break
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

        log.debug("Older versions in the solution(s):")
        for sol in solutions:
            log.debug([(i, w[j]) for i, j in eq_version if j in sol])
        stdoutlog.info('\n')
        return map(sorted, psolutions) if returnall else sorted(psolutions[0])


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
