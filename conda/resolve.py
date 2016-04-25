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
        bad_deps = [list(map(lambda x: x.spec, dep)) for dep in bad_deps]
        if chains:
            chains = {}
            for dep in sorted(bad_deps, key=len, reverse=True):
                dep1 = [str(MatchSpec(s)).partition(' ') for s in dep[1:]]
                key = (dep[0],) + tuple(v[0] for v in dep1)
                vals = ('',) + tuple(v[2] for v in dep1)
                found = False
                for key2, csets in iteritems(chains):
                    if key2[:len(key)] == key:
                        for cset, val in zip(csets, vals):
                            cset.add(val)
                        found = True
                if not found:
                    chains[key] = [{val} for val in vals]
            bad_deps = []
            for key, csets in iteritems(chains):
                deps = []
                for name, cset in zip(key, csets):
                    if '' not in cset:
                        pass
                    elif len(cset) == 1:
                        cset.clear()
                    else:
                        cset.remove('')
                        cset.add('*')
                    if name[0] == '@':
                        name = 'feature:' + name[1:]
                    deps.append('%s %s' % (name, '|'.join(sorted(cset))) if cset else name)
                chains[key] = ' -> '.join(deps)
            bad_deps = [chains[key] for key in sorted(iterkeys(chains))]
            msg = '''The following specifications were found to be in conflict:%s
Use "conda info <package>" to see the dependencies for each package.'''
        else:
            bad_deps = [sorted(dep) for dep in bad_deps]
            bad_deps = [', '.join(dep) for dep in sorted(bad_deps)]
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
        msg = '%s missing in current %s channels: %s' % (what, config.subdir, bad_deps)
        super(NoPackagesFound, self).__init__(msg)
        self.pkgs = deps


class MatchSpec(object):
    def __new__(cls, spec, target=None, optional=None):
        if isinstance(spec, cls):
            return spec
        self = object.__new__(cls)
        spec, _, oparts = spec.partition('(')
        self.spec = spec.strip()
        if oparts and oparts.strip()[-1] != ')':
            raise ValueError("Invalid MatchSpec: %s" % spec)
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
        if oparts:
            for opart in oparts.strip()[:-1].split(','):
                if opart == 'optional':
                    self.optional = True
                elif opart.startswith('target='):
                    self.target = opart.split('=')[1].strip()
                else:
                    raise ValueError("Invalid MatchSpec: %s" % spec)
        if self.optional is None:
            self.optional = False
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
            name, version, build = info[:-8].rsplit('-', 2)
        else:
            name = info.get('name')
            version = info.get('version')
            build = info.get('build')
        if name != self.name:
            return False
        return self.match_fast(version, build)

    def to_filename(self):
        if self.strictness == 3 and not self.optional:
            return self.name + '-%s-%s.tar.bz2' % self.ver_build
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
        self.schannel = info.get('schannel')
        if self.schannel is None:
            self.schannel = config.canonical_channel_name(self.channel)
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


class Resolve(object):
    def __init__(self, index, sort=False, processed=False):
        if not processed:
            for fkey, info in iteritems(index.copy()):
                for fstr in chain(info.get('features', '').split(),
                                  info.get('track_features', '').split()):
                    fpkg = fstr + '@'
                    if fpkg not in index:
                        index[fpkg] = {
                            'name': fpkg, 'channel': '@', 'priority': 0,
                            'version': '0', 'build_number': 0,
                            'build': '', 'depends': [], 'track_features': fstr}
                for fstr in iterkeys(info.get('with_features_depends', {})):
                    index['%s[%s]' % (fkey, fstr)] = info

        groups = {}
        trackers = {}
        installed = set()
        for fkey, info in iteritems(index):
            groups.setdefault(info['name'], []).append(fkey)
            for feat in info.get('track_features', '').split():
                trackers.setdefault(feat, []).append(fkey)
            if 'link' in info:
                installed.add(fkey)

        self.index = index
        self.groups = groups
        self.installed = installed
        self.trackers = trackers
        self.find_matches_ = {}
        self.ms_depends_ = {}

        if sort:
            for name, group in iteritems(groups):
                groups[name] = sorted(group, key=self.version_key, reverse=True)

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
            fkey: a package key, a MatchSpec, or an iterable of these.
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

        def v_fkey_(fkey):
            val = filter.get(fkey)
            if val is None:
                filter[fkey] = True
                val = filter[fkey] = all(v_ms_(ms) for ms in self.ms_depends(fkey))
            return val

        return v_(spec)

    def touch(self, spec, touched, filter):
        """Determines a conservative set of packages to be considered given a
           package, or a spec, or a list thereof. Cyclic dependencies are not
           solved, so there is no guarantee a solution exists.

        Args:
            fkey: a package key or MatchSpec
            touched: a dict into which to accumulate the result. This is
                useful when processing multiple specs.
            filter: a dictionary of (fkey, valid) pairs to be used when
                testing for package validity.

        This function works in two passes. First, it verifies that the package has
        satisfiable dependencies from among the filtered packages. If not, then it
        is _not_ touched, nor are its dependencies. If so, then it is marked as
        touched, and any of its valid dependencies are as well.
        """
        def t_fkey_(fkey):
            val = touched.get(fkey)
            if val is None:
                val = touched[fkey] = self.valid(fkey, filter)
                if val:
                    for ms in self.ms_depends(fkey):
                        if ms.name[0] != '@':
                            t_ms_(ms)

        def t_ms_(ms):
            for fkey in self.find_matches(ms):
                t_fkey_(fkey)

        return t_ms_(spec) if isinstance(spec, MatchSpec) else t_fkey_(spec)

    def invalid_chains(self, spec, filter):
        """Constructs a set of 'dependency chains' for invalid specs.

        A dependency chain is a tuple of MatchSpec objects, starting with
        the requested spec, proceeding down the dependency tree, ending at
        a specification that cannot be satisfied. Uses self.valid_ as a
        filter, both to prevent chains and to allow other routines to
        prune the list of valid packages with additional criteria.

        Args:
            spec: a package key or MatchSpec
            filter: a dictionary of (fkey, valid) pairs to be used when
                testing for package validity.

        Returns:
            A list of tuples, or an empty list if the MatchSpec is valid.
        """
        def chains_(spec, top=None):
            if spec.name == top or self.valid(spec, filter):
                return []
            notfound = set()
            specs = self.find_matches(spec) if isinstance(spec, MatchSpec) else [spec]
            for fkey in specs:
                for m2 in self.ms_depends(fkey):
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
        spec2 = []
        feats = set()
        for s in specs:
            ms = MatchSpec(s)
            if ms.name[-1] == '@':
                feats.add(ms.name[:-1])
                continue
            if not ms.optional:
                spec2.append(ms)
            else:
                opts.append(ms)
        for ms in spec2:
            filter = self.default_filter(feats)
            if not self.valid(ms, filter):
                bad_deps.extend(self.invalid_chains(ms, filter))
        if bad_deps:
            raise NoPackagesFound(bad_deps)
        return spec2, opts, feats

    def get_dists(self, specs):
        log.debug('Retrieving packages for: %s' % specs)

        specs, optional, features = self.verify_specs(specs)
        filter = {}
        touched = {}
        snames = set()
        nspecs = set()
        unsat = set()

        def filter_group(matches, chains=None):
            # If we are here, then this dependency is mandatory,
            # so add it to the master list. That way it is still
            # participates in the pruning even if one of its
            # parents is pruned away
            if unsat:
                return False
            match1 = next(ms for ms in matches)
            name = match1.name
            first = name not in snames
            group = self.groups.get(name, [])

            # Prune packages that don't match any of the patterns
            # or which have unsatisfiable dependencies
            nold = 0
            bad_deps = []
            for fkey in group:
                if filter.setdefault(fkey, True):
                    nold += 1
                    sat = self.match_any(matches, fkey)
                    sat = sat and all(any(filter.get(f2, True) for f2 in self.find_matches(ms))
                                      for ms in self.ms_depends(fkey))
                    filter[fkey] = sat
                    if not sat:
                        bad_deps.append(fkey)

            # Build dependency chains if we detect unsatisfiability
            nnew = nold - len(bad_deps)
            reduced = nnew < nold
            if reduced:
                log.debug('%s: pruned from %d -> %d' % (name, nold, nnew))
            if nnew == 0:
                if name in snames:
                    snames.remove(name)
                bad_deps = [fkey for fkey in bad_deps if self.match_any(matches, fkey)]
                matches = [(ms,) for ms in matches]
                chains = [a + b for a in chains for b in matches] if chains else matches
                if bad_deps:
                    dep2 = set()
                    for fkey in bad_deps:
                        for ms in self.ms_depends(fkey):
                            if not any(filter.get(f2, True) for f2 in self.find_matches(ms)):
                                dep2.add(ms)
                    chains = [a + (b,) for a in chains for b in dep2]
                unsat.update(chains)
                return nnew != 0
            if not reduced and not first:
                return False

            # Perform the same filtering steps on any dependencies shared across
            # *all* packages in the group. Even if just one of the packages does
            # not have a particular dependency, it must be ignored in this pass.
            if first:
                snames.add(name)
                if match1 not in specs:
                    nspecs.add(MatchSpec(name))
            cdeps = defaultdict(list)
            for fkey in group:
                if filter[fkey]:
                    for m2 in self.ms_depends(fkey):
                        if m2.name[0] != '@' and not m2.optional:
                            cdeps[m2.name].append(m2)
            cdeps = {mname: set(deps) for mname, deps in iteritems(cdeps) if len(deps) >= nnew}
            if cdeps:
                matches = [(ms,) for ms in matches]
                if chains:
                    matches = [a + b for a in chains for b in matches]
                if sum(filter_group(deps, chains) for deps in itervalues(cdeps)):
                    reduced = True

            return reduced

        # Iterate in the filtering process until no more progress is made
        def full_prune(specs, optional, features):
            self.default_filter(features, filter)
            for ms in optional:
                for fkey in self.groups.get(ms.name, []):
                    if not self.match_fast(ms, fkey):
                        filter[fkey] = False
            feats = set(self.trackers.keys())
            snames.clear()
            specs = slist = list(specs)
            onames = set(s.name for s in specs)
            for iter in range(10):
                first = True
                while sum(filter_group([s]) for s in slist) and not unsat:
                    slist = specs + [MatchSpec(n) for n in snames - onames]
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
                for fkey, val in iteritems(touched):
                    if val:
                        nfeats.update(self.track_features(fkey))
                if len(nfeats) >= len(feats):
                    return True
                pruned = False
                for feat in feats - nfeats:
                    feats.remove(feat)
                    for fkey in self.trackers[feat]:
                        if filter.get(fkey, True):
                            filter[fkey] = False
                            pruned = True
                if not pruned:
                    return True

        #
        # In the case of a conflict, look for the minimum satisfiable subset
        #

        if not full_prune(specs, optional, features):
            def minsat_prune(specs):
                return full_prune(specs, optional, features)

            save_unsat = set(s for s in unsat if s[0] in specs)
            stderrlog.info('...')
            hint = minimal_unsatisfiable_subset(specs, sat=minsat_prune, log=False)
            save_unsat.update((ms,) for ms in hint)
            raise Unsatisfiable(save_unsat)

        dists = {fkey: self.index[fkey] for fkey, val in iteritems(touched) if val}
        return dists, list(map(MatchSpec, snames - {ms.name for ms in specs}))

    def match_any(self, mss, fkey):
        rec = self.index[fkey]
        n, v, b = rec['name'], rec['version'], rec['build']
        return any(n == ms.name and ms.match_fast(v, b) for ms in mss)

    def match(self, ms, fkey):
        return MatchSpec(ms).match(self.index[fkey])

    def match_fast(self, ms, fkey):
        rec = self.index[fkey]
        return ms.match_fast(rec['version'], rec['build'])

    def find_matches(self, ms):
        ms = MatchSpec(ms)
        res = self.find_matches_.get(ms, None)
        if res is None:
            if ms.name[0] == '@':
                res = self.trackers.get(ms.name[1:], [])
            else:
                res = self.groups.get(ms.name, [])
                res = [p for p in res if self.match_fast(ms, p)]
            self.find_matches_[ms] = res
        return res

    def ms_depends(self, fkey):
        deps = self.ms_depends_.get(fkey, None)
        if deps is None:
            rec = self.index[fkey]
            if fkey.endswith(']'):
                f2, fstr = fkey.rsplit('[', 1)
                fdeps = {d.name: d for d in self.ms_depends(f2)}
                for dep in rec['with_features_depends'][fstr[:-1]]:
                    dep = MatchSpec(dep)
                    fdeps[dep.name] = dep
                deps = list(fdeps.values())
            else:
                deps = [MatchSpec(d) for d in rec.get('depends', [])]
            deps.extend(MatchSpec('@'+feat) for feat in self.features(fkey))
            self.ms_depends_[fkey] = deps
        return deps

    def version_key(self, fkey, vtype=None):
        rec = self.index[fkey]
        cpri = -rec.get('priority', 1)
        ver = normalized_version(rec.get('version', ''))
        bld = rec.get('build_number', 0)
        return (cpri, ver, bld) if config.channel_priority else (ver, cpri, bld)

    def features(self, fkey):
        return set(self.index[fkey].get('features', '').split())

    def track_features(self, fkey):
        return set(self.index[fkey].get('track_features', '').split())

    def package_triple(self, fkey):
        rec = self.index.get(fkey, None)
        if rec is None:
            fkey = fkey.rsplit('[', 1)[0].rsplit('/', 1)[-1]
            if fkey.endswith('.tar.bz2'):
                fkey = fkey[:-8]
            return fkey.rsplit('-', 2)
        return (rec['name'], rec['version'], rec['build'])

    def package_name(self, fkey):
        return self.package_triple(fkey)[0]

    def get_pkgs(self, ms, emptyok=False):
        ms = MatchSpec(ms)
        pkgs = [Package(fkey, self.index[fkey]) for fkey in self.find_matches(ms)]
        if not pkgs and not emptyok:
            raise NoPackagesFound([(ms,)])
        return pkgs

    @staticmethod
    def ms_to_v(ms):
        ms = MatchSpec(ms)
        return '@s@' + ms.spec + ('?' if ms.optional else '')

    def push_MatchSpec(self, C, ms):
        ms = MatchSpec(ms)
        name = self.ms_to_v(ms)
        m = C.from_name(name)
        if m is None and not ms.optional:
            ms2 = MatchSpec(ms.spec, optional=True)
            m = C.from_name(self.ms_to_v(ms2))
        if m is None:
            libs = [fkey for fkey in self.find_matches(ms)]
            tgroup = (self.trackers.get(ms.name[1:], []) if ms.name[0] == '@'
                      else self.groups.get(ms.name, []))
            if len(libs) == len(tgroup):
                m = C.from_name(self.ms_to_v(ms.name))
        if m is None:
            # If the MatchSpec is optional, then there may be cases where we want
            # to assert that it is *not* True. This requires polarity=None. We do
            # the same for features as well for the same reason.
            polarity = None if ms.optional else True
            m = C.Any(libs, polarity=None if ms.optional else True)
            if polarity is None and ms.optional:
                # If we've created an optional variable, it works for non-optional too
                ms.optional = False
                C.name_var(m, self.ms_to_v(ms))
        C.name_var(m, name)
        return name

    def gen_clauses(self, specs):
        C = Clauses()

        # Creates a variable that represents the proposition:
        #     Does the package set include package "fn"?
        for name, group in iteritems(self.groups):
            for fkey in group:
                C.new_var(fkey)
            # Install no more than one version of each package
            C.Require(C.AtMostOne, group)
            # Create an on/off variable for the entire group
            name = self.ms_to_v(name)
            C.name_var(C.Any(group, polarity=None, name=name), name+'?')

        # Creates a variable that represents the proposition:
        #    Does the package set include track_feature "feat"?
        for name, group in iteritems(self.trackers):
            name = self.ms_to_v('@' + name)
            C.name_var(C.Any(group, polarity=None, name=name), name+'?')

        # Create propositions that assert:
        #     If package "fn" is installed, its dependencie must be satisfied
        for group in itervalues(self.groups):
            for fkey in group:
                nkey = C.Not(fkey)
                for ms in self.ms_depends(fkey):
                    if not ms.optional:
                        C.Require(C.Or, nkey, self.push_MatchSpec(C, ms))
        return C

    def generate_spec_constraints(self, C, specs):
        return [(self.push_MatchSpec(C, ms),) for ms in specs if not ms.optional]

    def generate_feature_count(self, C):
        return {self.ms_to_v('@' + name): 1 for name in iterkeys(self.trackers)}

    def generate_feature_metric(self, C):
        eq = {}
        total = 0
        for name, group in iteritems(self.groups):
            nf = [len(self.features(fkey)) for fkey in group]
            maxf = max(nf)
            eq.update({fn: maxf-fc for fn, fc in zip(group, nf) if fc < maxf})
            total += maxf
        return eq, total

    def generate_removal_count(self, C, specs):
        return {'!'+self.ms_to_v(ms): 1 for ms in specs}

    def generate_package_count(self, C, missing):
        return {self.ms_to_v(nm): 1 for nm in missing}

    def generate_version_metrics(self, C, specs):
        eqv = {}
        eqb = {}
        sdict = {}
        for s in specs:
            s = MatchSpec(s)  # needed for testing
            sdict.setdefault(s.name, []).append(s)
        for name, mss in iteritems(sdict):
            pkgs = [(self.version_key(p), p) for p in self.groups.get(name, [])]
            # If the "target" field in the MatchSpec is supplied, that means we want
            # to minimize the changes to the currently installed package. We prefer
            # any upgrade over any downgrade, but beyond that we want minimal change.
            targets = [ms.target for ms in mss if ms.target and ms.target in self.index]
            if targets:
                v1 = [(self.version_key(p), p) for p in targets]
                tver = max(v1)
                v2 = [p for p in pkgs if p > tver]
                v3 = list(reversed([p for p in pkgs if p <= tver and p not in v1]))
                pkgs = v1 + v2 + v3
            pkey = None
            for nkey, npkg in pkgs:
                if pkey is None:
                    iv = ib = 0
                elif pkey[0] != nkey[0] or pkey[1] != nkey[1]:
                    iv += 1
                    ib = 0
                elif pkey[2] != nkey[2]:
                    ib += 1
                if iv:
                    eqv[npkg] = iv
                if ib:
                    eqb[npkg] = ib
                pkey = nkey
        return eqv, eqb

    def dependency_sort(self, must_have):
        def lookup(value):
            return set(ms.name for ms in self.ms_depends(value + '.tar.bz2'))
        digraph = {}
        if not isinstance(must_have, dict):
            must_have = {self.package_name(dist): dist for dist in must_have}
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

    def bad_installed(self, installed, new_specs):
        log.debug('Checking if the current environment is consistent')
        if not installed:
            return None, []
        xtra = []
        dists = {}
        specs = []
        for fn in installed:
            rec = self.index.get(fn)
            if rec is None:
                xtra.append(fn)
            else:
                dists[fn] = rec
                specs.append(MatchSpec(' '.join(self.package_triple(fn))))
        if xtra:
            log.debug('Packages missing from index: %s' % ', '.join(xtra))
        r2 = Resolve(dists, True, True)
        C = r2.gen_clauses(specs)
        constraints = r2.generate_spec_constraints(C, specs)
        try:
            solution = C.sat(constraints)
        except TypeError:
            log.debug('Package set caused an unexpected error, assuming a conflict')
            solution = None
        limit = None
        if not solution or xtra:
            def get_(name, snames):
                if name not in snames:
                    snames.add(name)
                    for fn in self.groups.get(name, []):
                        for ms in self.ms_depends(fn):
                            get_(ms.name, snames)
            snames = set()
            for spec in new_specs:
                get_(MatchSpec(spec).name, snames)
            xtra = [x for x in xtra if x not in snames]
            if xtra or not (solution or all(s.name in snames for s in specs)):
                limit = set(s.name for s in specs if s.name in snames)
                xtra = [fn for fn in installed if self.package_name(fn) not in snames]
                log.debug(
                    'Limiting solver to the following packages: %s' %
                    ', '.join(limit))
        if xtra:
            log.debug('Packages to be preserved: %s' % ', '.join(xtra))
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
            name, version, build = self.package_triple(pkg)
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
        len0 = len(specs)
        specs, preserve = self.install_specs(specs, installed or [], update_deps)
        pkgs = self.solve(specs, len0=len0, returnall=returnall)
        self.restore_bad(pkgs, preserve)
        return pkgs

    def remove_specs(self, specs, installed):
        # These never match true version/build combos so it forces removal
        specs = [MatchSpec('%s @ @' % s, optional=True) for s in specs]
        snames = {s.name for s in specs}
        limit, _ = self.bad_installed(installed, specs)
        preserve = []
        for pkg in installed:
            nm, ver, build = self.package_triple(pkg)
            if nm in snames:
                continue
            elif limit is not None:
                preserve.append(pkg)
            elif ver:
                specs.append(MatchSpec('%s >=%s' % (nm, ver), optional=True, target=pkg))
            else:
                specs.append(MatchSpec(nm, optional=True, target=pkg))
        return specs, preserve

    def remove(self, specs, installed):
        specs, preserve = self.remove_specs(specs, installed)
        pkgs = self.solve(specs)
        self.restore_bad(pkgs, preserve)
        return pkgs

    def solve(self, specs, len0=None, returnall=False):
        try:
            stdoutlog.info("Solving package specifications ...")
            dotlog.debug("Solving for %s" % (specs,))

            # Find the compliant packages
            specs = list(map(MatchSpec, specs))
            if len0 is None:
                len0 = len(specs)
            dists, new_specs = self.get_dists(specs)
            if not dists:
                return False if dists is None else ([[]] if returnall else [])

            # Check if satisfiable
            dotlog.debug('Checking satisfiability')
            r2 = Resolve(dists, True, True)
            C = r2.gen_clauses(specs)
            constraints = r2.generate_spec_constraints(C, specs)
            solution = C.sat(constraints, True)
            if not solution:
                # Find the largest set of specs that are satisfiable, and return
                # the list of specs that are not in that set.
                solution = [C.Not(q) for q in range(1, C.m+1)]
                spec2 = [s for s in specs if not s.optional]
                eq_removal_count = r2.generate_removal_count(C, spec2)
                solution, obj1 = C.minimize(eq_removal_count, solution)
                specsol = [(s,) for s in spec2 if C.from_name(self.ms_to_v(s)) not in solution]
                raise Unsatisfiable(specsol, False)

            speco = []  # optional packages
            specr = []  # requested packages
            speca = []  # all other packages
            specm = set(r2.groups)  # missing from specs
            for k, s in enumerate(chain(specs, new_specs)):
                if s.name in specm:
                    specm.remove(s.name)
                if not s.optional:
                    (specr if k < len0 else speca).append(s)
                elif any(r2.find_matches(s)):
                    s = MatchSpec(s.name, optional=True, target=s.target)
                    speco.append(s)
                    speca.append(s)
            speca.extend(MatchSpec(s) for s in specm)

            # Removed packages: minimize count
            eq_optional_c = r2.generate_removal_count(C, speco)
            solution, obj7 = C.minimize(eq_optional_c, solution)
            dotlog.debug('Package removal metric: %d' % obj7)

            # Requested packages: maximize versions, then builds
            eq_req_v, eq_req_b = r2.generate_version_metrics(C, specr)
            solution, obj3 = C.minimize(eq_req_v, solution)
            solution, obj4 = C.minimize(eq_req_b, solution)
            dotlog.debug('Initial package version/build metrics: %d/%d' % (obj3, obj4))

            # Track features: minimize feature count
            eq_feature_count = r2.generate_feature_count(C)
            solution, obj1 = C.minimize(eq_feature_count, solution)
            dotlog.debug('Track feature count: %d' % obj1)

            # Featured packages: maximize featured package count
            eq_feature_metric, ftotal = r2.generate_feature_metric(C)
            solution, obj2 = C.minimize(eq_feature_metric, solution)
            obj2 = ftotal - obj2
            dotlog.debug('Package feature count: %d' % obj2)

            # Remaining packages: maximize versions, then builds, then count
            eq_v, eq_b = r2.generate_version_metrics(C, speca)
            solution, obj5 = C.minimize(eq_v, solution)
            solution, obj6 = C.minimize(eq_b, solution)
            dotlog.debug('Additional package version/build metrics: %d/%d' % (obj5, obj6))

            # Prune unnecessary packages
            eq_c = r2.generate_package_count(C, specm)
            solution, obj7 = C.minimize(eq_c, solution, trymax=True)
            dotlog.debug('Weak dependency count: %d' % obj7)

            def clean(sol):
                return [q for q in (C.from_index(s) for s in sol)
                        if q and q[0] != '!' and '@' not in q]
            dotlog.debug('Looking for alternate solutions')
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

            def stripfeat(sol):
                return sol.split('[')[0]
            stdoutlog.info('\n')
            if returnall:
                return [sorted(map(stripfeat, psol)) for psol in psolutions]
            else:
                return sorted(map(stripfeat, psolutions[0]))
        except:
            stdoutlog.info('\n')
            raise
