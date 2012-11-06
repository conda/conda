
from naming import split_canonical_name
from os import listdir
from os.path import isdir, join
import logging
from requirement import requirement

from constraints import (
    all_of, any_of, build_target, requires, satisfies, wildcard
)


log = logging.getLogger(__name__)


class environment(object):

    __slots__ = ['_conda', '_prefix']

    def __init__(self, conda, prefix):
        self._conda = conda
        self._prefix = prefix

    @property
    def conda(self):
        return self._conda

    @property
    def prefix(self):
        return self._prefix

    @property
    def activated(self):
        index_path = join(self.prefix, '.index')
        res = set()
        if isdir(index_path):
            for fn in listdir(index_path):
                try:
                    res.add(self._conda.index.lookup_from_canonical_name(fn))
                except:  # TODO better except spec
                    msg = "cannot find activated package '%s' in pacakge index" % fn
                    log.warn(msg)
        return res

    @property
    def requirements(self):
        bt = build_target(self._conda.target)
        py = self._python_requirement()
        np = self._numpy_requirement()
        return all_of(bt, py, np)

    def find_activated_package(self, pkg_name):
        index_path = join(self.prefix, '.index')
        if not isdir(index_path): return None
        for fn in listdir(index_path):
            name, version, build = split_canonical_name(fn)
            if name == pkg_name:
                return self._conda.index.lookup_from_canonical_name(fn)

    def requirement_is_satisfied(self, req):
        c = satisfies(req)
        for pkg in self.activated:
            if c.match(pkg):
                return True

    def _python_requirement(self):
        try:
            pkg = self.find_activated_package('python')
            req = requirement('%s %s.%s' % (pkg.name, pkg.version.version[0], pkg.version.version[1]))
            sat = requirement('%s %s %s' % (pkg.name, pkg.version.vstring, pkg.build))
            return any_of(requires(req), satisfies(sat))
        except: # TODO
            log.debug('found no python requirement, returning wildcard()')
            return wildcard()

    def _numpy_requirement(self):
        try:
            pkg = self.find_activated_package('numpy')
            req = requirement('%s %s.%s' % (pkg.name, pkg.version.version[0], pkg.version.version[1]))
            sat = requirement('%s %s %s' % (pkg.name, pkg.version.vstring, pkg.build))
            return any_of(requires(req), satisfies(sat))
        except: #TODO
            log.debug('found no numpy requirement, returning wildcard()')
            return wildcard()

    def __str__(self):
        return 'env[%s]' % self.prefix

    def __repr__(self):
        return 'environment(%r, %r)' % (self._conda, self._prefix)

    def __hash__(self):
        return hash(self._prefix)

    def __cmp__(self, other):
        return cmp(self._prefix, other._prefix)



