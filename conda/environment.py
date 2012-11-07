
from naming import split_canonical_name
import logging
from requirement import requirement

from constraints import (
    all_of, any_of, build_target, requires, satisfies, wildcard
)
from install import activated


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
        canonical_names = activated(self.prefix)
        res = set()
        for name in canonical_names:
            try:
                res.add(self._conda.index.lookup_from_canonical_name(name))
            except:  # TODO better except spec
                msg = "cannot find activated package '%s' in pacakge index" % name
                log.warn(msg)
        return res

    @property
    def requirements(self):
        bt = build_target(self._conda.target)
        py = self._python_requirement()
        np = self._numpy_requirement()
        return all_of(bt, py, np)

    def find_activated_package(self, pkg_name):
        canonical_names = activated(self.prefix)
        for canonical_name in canonical_names:
            name, version, build = split_canonical_name(canonical_name)
            if name == pkg_name:
                return self._conda.index.lookup_from_canonical_name(canonical_name)
        return None

    def requirement_is_satisfied(self, req):
        c = satisfies(req)
        for pkg in self.activated:
            if c.match(pkg):
                return True
        return False

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



