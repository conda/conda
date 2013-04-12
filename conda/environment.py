# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
''' The environment module provides the `environment` class, which provides
information about individual Anaconda environments, including prefix, activated
packages, and overall environment constraints.

'''
from naming import split_canonical_name
import logging
from os.path import isdir

from constraints import AllOf, AnyOf, Requires, Satisfies, Wildcard
from install import linked, get_meta
from package import Package
from package_spec import make_package_spec


log = logging.getLogger(__name__)


class Environment(object):
    ''' Provides information about a given :ref:`Anaconda environment <environment>`

    Parameters
    ----------
    conda : :py:class:`Anaconda <conda.anaconda.Anaconda>` object
    prefix : str
        full path to Anaconda environment

    Attributes
    ----------
    conda : anaconda object
    features : set of str
    linked : set of packages
    prefix : str
    requirements : package_constraint object

    '''

    __slots__ = ['_conda', '_prefix', '_canonical_names']

    def __init__(self, conda, prefix):
        if not isdir(prefix):
            raise RuntimeError("no environment found at location '%s'" % prefix)
        self._conda = conda
        self._prefix = prefix
        self._canonical_names = linked(self.prefix)

    @property
    def conda(self):
        ''' Return associated :py:class:`Anaconda <conda.anaconda.Anaconda>` object '''
        return self._conda

    @property
    def prefix(self):
        ''' Return directory location of this environment '''
        return self._prefix

    @property
    def linked(self):
        ''' Return the set of :ref:`linked <linked>` packages in this environment '''
        res = set()
        for name in self._canonical_names:
            try:
                res.add(self._conda.index.lookup_from_canonical_name(name))
            except KeyError:
                log.debug("cannot find linked package '%s' in package index" % name)
        return res

    @property
    def features(self):
        ''' Return the dictionary of :ref:`tracked features <tracked_features>` and associated packages for this environment '''
        res ={}
        for name in self._canonical_names:
            try:
                pkg = self._conda.index.lookup_from_canonical_name(name)
                for feature in pkg.track_features:
                    if not res.has_key(feature): res[feature] = set()
                    res[feature].add(pkg)
            except KeyError:
                log.debug("cannot find linked package '%s' in package index" % name)
        return res

    @property
    def requirements(self):
        ''' Return a baseline :py:class:`PackageConstraint <conda.constraints.PackageConstraint>` that packages in this environement must match

        Returns
        -------
        requirements : py:class:`PackageConstraint <conda.constraints.PackageConstraint>`
        '''
        py = self._python_constraint()
        np = self._numpy_constraint()
        return AllOf(py, np)

    def find_linked_package(self, pkg_name):
        ''' find and return an :ref:`linked <linked>` packages in the environment with the specified :ref:`package name <package_name>`

        Parameters
        ----------
        pkg_name : str
            :ref:`package name <package_name>` to match when searching linked packages

        Returns
        -------
        linked : :py:class:`Package <conda.package.Package>` object, or None

        '''
        for canonical_name in self._canonical_names:
            name, version, build = split_canonical_name(canonical_name)
            if name == pkg_name:
                try:
                    return self._conda.index.lookup_from_canonical_name(canonical_name)
                except KeyError:
                    log.debug("could not look up canonical_name '%s', using conda-meta" % canonical_name)
                    return Package(get_meta(canonical_name, self._prefix))
        return None

    def requirement_is_satisfied(self, spec):
        c = Satisfies(spec)
        for pkg in self.linked:
            if c.match(pkg):
                return True
        return False

    def _python_constraint(self):
        try:
            pkg = self.find_linked_package('python')
            spec = make_package_spec('%s %s.%s' % (pkg.name, pkg.version.version[0], pkg.version.version[1]))
            return AnyOf(Requires(spec), Satisfies(spec))
        except: # TODO
            log.debug('no python constraint, returning Wildcard()')
            return Wildcard()

    def _numpy_constraint(self):
        try:
            pkg = self.find_linked_package('numpy')
            req = make_package_spec('%s %s.%s' % (pkg.name, pkg.version.version[0], pkg.version.version[1]))
            sat = make_package_spec('%s %s %s' % (pkg.name, pkg.version.vstring, pkg.build))
            return AnyOf(Requires(req), Satisfies(sat))
        except: #TODO
            log.debug('no numpy constraint, returning Wildcard()')
            return Wildcard()

    def __str__(self):
        return 'env[%s]' % self.prefix

    def __repr__(self):
        return 'Environment(%r, %r)' % (self._conda, self._prefix)

    def __hash__(self):
        return hash(self._prefix)

    def __cmp__(self, other):
        return cmp(self._prefix, other._prefix)


def clone_environment(src_prefix, dst_prefix):
    from conda.anaconda import Anaconda
    from conda.package_plan import PackagePlan
    from os import mkdir
    conda = Anaconda()
    src = conda.lookup_environment(src_prefix)
    mkdir(dst_prefix)
    dst = Environment(conda, dst_prefix)
    plan = PackagePlan()
    plan.activations = src.activated
    plan.execute(dst)
