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

from constraints import all_of, any_of, build_target, requires, satisfies, wildcard
from install import activated, get_meta
from package import package
from package_spec import package_spec


log = logging.getLogger(__name__)


class environment(object):
    ''' Provides information about a given :ref:`Anaconda environment <environment>`

    Parameters
    ----------
    conda : :py:class:`anaconda <conda.anaconda.anaconda>` object
    prefix : str
        full path to Anaconda environment

    Attributes
    ----------
    activated : set of packages
    conda : anaconda object
    prefix : str
    requirements : package_constraint object

    '''

    __slots__ = ['_conda', '_prefix']

    def __init__(self, conda, prefix):
        if not isdir(prefix):
            raise RuntimeError("no environment found at location '%s'" % prefix)
        self._conda = conda
        self._prefix = prefix

    @property
    def conda(self):
        ''' Return associated :py:class:`anaconda <conda.anaconda.anaconda>` object '''
        return self._conda

    @property
    def prefix(self):
        ''' Return directory location of this environment '''
        return self._prefix

    @property
    def activated(self):
        ''' Return the set of :ref:`activated <activated>` packages in this environment '''
        canonical_names = activated(self.prefix)
        res = set()
        for name in canonical_names:
            try:
                res.add(self._conda.index.lookup_from_canonical_name(name))
            except:  # TODO better except spec
                log.debug("cannot find activated package '%s' in package index" % name)
        return res

    @property
    def requirements(self):
        ''' Return a baseline :py:class:`package_constaint <conda.constraints.package_constraint>` that packages in this environement must match

        Returns
        -------
        requirements : py:class:`package constraint <conda.constraints.package_constraint>`
        '''
        bt = build_target(self._conda.target)
        py = self._python_constraint()
        np = self._numpy_constraint()
        return all_of(bt, py, np)

    def get_requirements(self, target=None):
        ''' This function is analogous to the requirements property, but it allows the build target to be overridden if necessary.

        Parameters
        ----------
        target : str
            build target to include in environment requirements, or None

        Returns
        -------
        requirements : py:class:`package constraint <conda.constraints.package_constraint>`
        '''
        if target:
            bt = build_target(target)
        else:
            bt = build_target(self._conda.target)
        py = self._python_constraint()
        np = self._numpy_constraint()
        return all_of(bt, py, np)

    def find_activated_package(self, pkg_name):
        ''' find and return an :ref:`activated <activated>` packages in the environment with the specified :ref:`package name <package_name>`

        Parameters
        ----------
        pkg_name : str
            :ref:`package name <package_name>` to match when searching activated packages

        Returns
        -------
        activated : :py:class:`package <conda.package.package>` object, or None

        '''
        canonical_names = activated(self.prefix)
        for canonical_name in canonical_names:
            name, version, build = split_canonical_name(canonical_name)
            if name == pkg_name:
                try:
                    return self._conda.index.lookup_from_canonical_name(canonical_name)
                except KeyError:
                    log.debug("could not look up canonical_name '%s', using conda-meta" % canonical_name)
                    return package(get_meta(canonical_name, self._prefix))
        return None

    def requirement_is_satisfied(self, spec):
        c = satisfies(spec)
        for pkg in self.activated:
            if c.match(pkg):
                return True
        return False

    def _python_constraint(self):
        try:
            pkg = self.find_activated_package('python')
            req = package_spec('%s %s.%s' % (pkg.name, pkg.version.version[0], pkg.version.version[1]))
            sat = package_spec('%s %s %s' % (pkg.name, pkg.version.vstring, pkg.build))
            return any_of(requires(req), satisfies(sat))
        except: # TODO
            log.debug('no python constraint, returning wildcard()')
            return wildcard()

    def _numpy_constraint(self):
        try:
            pkg = self.find_activated_package('numpy')
            req = package_spec('%s %s.%s' % (pkg.name, pkg.version.version[0], pkg.version.version[1]))
            sat = package_spec('%s %s %s' % (pkg.name, pkg.version.vstring, pkg.build))
            return any_of(requires(req), satisfies(sat))
        except: #TODO
            log.debug('no numpy constraint, returning wildcard()')
            return wildcard()

    def __str__(self):
        return 'env[%s]' % self.prefix

    def __repr__(self):
        return 'environment(%r, %r)' % (self._conda, self._prefix)

    def __hash__(self):
        return hash(self._prefix)

    def __cmp__(self, other):
        return cmp(self._prefix, other._prefix)

