# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
''' The constraints module provides a variety of package `constraint` classes that
can be used to search and match packages in the package index.

'''

class package_constraint(object):
    ''' Base class for specific package_constraint objects that match packages with
    specified criteria.

    '''
    def match(self, pkg):
        '''
        match criteria against package info


        Parameters
        ----------
        pkg : :py:class:`package <conda.package.package>` object
            package to match

        Returns
        -------
        matches : bool
            whether the specified package matches this constraint

        '''
        raise NotImplementedError()
    def __hash__(self):
        return hash(str(self))


class all_of(package_constraint):
    ''' logical AND for matching multiple constraints

    Parameters
    ----------
    *constraints : :py:class:`package_constraint <conda.constraints.package_constraint>` objects
        package constraints to AND together


    '''
    def __init__(self, *constraints):
        self._constraints = tuple(set(constraints))
    def __str__(self):
        return 'all_of[%s]' % ', '.join(str(c) for c in self._constraints)
    def __repr__(self):
        return 'all_of[%s]' % ', '.join(str(c) for c in self._constraints)
    def __cmp__(self, other):
        return cmp(self._constraints, other._constraints)
    def match(self, pkg):
        ''' Match if a package matches all the specified constraints

        Parameters
        ----------
        pkg : :py:class:`package <conda.package.package>` object
            package to match

        Returns
        -------
        matches : bool
            True if all of the `constraints` match, False otherwise

        '''
        for constraint in self._constraints:
            if not pkg.matches(constraint): return False
        return True


class any_of(package_constraint):
    ''' logical OR for matching multiple constraints

    Parameters
    ----------
    *constraints : :py:class:`package_constraint <conda.constraints.package_constraint>` objects
        package constraints to OR together

    '''
    def __init__(self, *constraints):
        self._constraints = tuple(set(constraints))
    def __str__(self):
        return 'any_of[%s]' % ', '.join(str(c) for c in self._constraints)
    def __repr__(self):
        return 'any_of[%s]' % ', '.join(str(c) for c in self._constraints)
    def __cmp__(self, other):
        return cmp(self._constraints, other._constraints)
    def match(self, pkg):
        ''' Match if a package matches any of the specified constraints

        Parameters
        ----------
        pkg : :py:class:`package <conda.package.package>` object
            package to match

        Returns
        -------
        matches : bool
            True if any of the `constraints` match, False otherwise

        '''
        for constraint in self._constraints:
            if pkg.matches(constraint): return True
        return False


class negate(package_constraint):
    ''' logical NOT for matching constraints

    Parameters
    ----------
    constraint : :py:class:`package_constraint <conda.constraints.package_constraint>` object
        package constraint to negate

    '''
    def __init__(self, constraint):
        self._constraint = constraint
    def __str__(self):
        return 'negate[%s]' % str(self._constraint)
    def __repr__(self):
        return 'negate[%s]' % str(self._constraint)
    def __cmp__(self, other):
        return cmp(self._constraint, other._constraint)
    def match(self, pkg):
        ''' Match if a package does NOT match the specified constraint

        Parameters
        ----------
        pkg : :py:class:`package <conda.package.package>` object
            package to match

        Returns
        -------
        matches : bool
            True if `constraint` does *not* match, False otherwise

        '''
        return not pkg.matches(self._constraint)


class named(package_constraint):
    ''' constraint for matching package names

    Parameters
    ----------
    name : str
        :ref:`package name <package_name>` to match against

    '''
    def __init__(self, name):
        self._name = name
    def __str__(self):
        return 'named[%s]' % self._name
    def __repr__(self):
        return 'named[%s]' % self._name
    def __cmp__(self, other):
        return cmp(self._name, other._name)
    def match(self, pkg):
        ''' Match if a package has the specified name

        Parameters
        ----------
        pkg : :py:class:`package <conda.package.package>` object
            package to match

        Returns
        -------
        matches : bool
            True if the package name matches, False otherwise

        '''
        return pkg.name == self._name


class strict_requires(package_constraint):
    ''' constraint for strictly matching package dependencies

    Parameters
    ----------
    req : :py:class:`package_spec <conda.package_spec.package_spec>` object
        package specification to match against

    '''
    def __init__(self, req):
        self._req = req
    def __str__(self):
        return 'strict_requires[%s]' % str(self._req)
    def __repr__(self):
        return 'strict_requires[%s]' % str(self._req)
    def __cmp__(self, other):
        return cmp(self._req, other._req)
    def match(self, pkg):
        ''' Match if a package contains a specified requirement

        Parameters
        ----------
        pkg : :py:class:`package <conda.package.package>` object
            package to match

        Returns
        -------
        matches : bool
            True if `req` is an exact requirement for `pkg`, False otherwise

        '''
        # package never requires itself
        if pkg.name == self._req.name: return False
        for req in pkg.requires:
            if req.name == self._req.name and req.version == self._req.version:
                return True
        return False


class requires(package_constraint):
    ''' constraint for matching package dependencies

    Parameters
    ----------
    req : :py:class:`package_spec <conda.package_spec.package_spec>` object
        package specification to match against

    '''
    def __init__(self, req):
        self._req = req
    def __str__(self):
        return 'requires[%s]' % str(self._req)
    def __repr__(self):
        return 'requires[%s]' % str(self._req)
    def __cmp__(self, other):
        return cmp(self._req, other._req)
    def match(self, pkg):
        ''' Match if a `req` is compatible with the requirements for `pkg`

        .. note:: matching includes the case when `pkg` has no requirement at all for the package specified by `req`

        Parameters
        ----------
        pkg : :py:class:`package <conda.package.package>` object
            package to match

        Returns
        -------
        matches : bool
            True if `req` is compatible requirement for `pkg`, has False otherwise

        '''
        # package never requires itself
        if pkg.name == self._req.name: return False
        vlen = len(self._req.version.version)
        for req in pkg.requires:
            if req.name == self._req.name and req.version.version[:vlen] != self._req.version.version[:vlen]:
                return False
        return True


class satisfies(package_constraint):
    ''' constraint for matching whether a package satisfies a package specification

    Parameters
    ----------
    req : :py:class:`package_spec <conda.package_spec.package_spec>` object
        package specification to match against

    '''
    def __init__(self, req):
        self._req = req
    def __str__(self):
        return 'satisfies[%s]' % str(self._req)
    def __repr__(self):
        return 'satisfies[%s]' % str(self._req)
    def __cmp__(self, other):
        return cmp(self._req, other._req)
    def match(self, pkg):
        ''' Match if a package satisfies the specified requirement

        Parameters
        ----------
        pkg : :py:class:`package <conda.package.package>` object
            package to match

        Returns
        -------
        matches : bool
            True if `pkg` is compatible with the package specification `req`

        '''
        if self._req.name != pkg.name: return False
        if not self._req.version: return True
        vlen = len(self._req.version.version)
        try:
            return self._req.version.version[:vlen] == pkg.version.version[:vlen]
        except:
            return False


class package_version(package_constraint):
    ''' constraint for matching package versions

    Parameters
    ----------
    req : :py:class:`package_spec <conda.package.package>` object
        pacakge to match against

    '''
    def __init__(self, pkg):
        self._pkg = pkg
    def __str__(self):
        return 'package_version[%s]' % str(self._pkg)
    def __repr__(self):
        return 'package_version[%s]' % str(self._pkg)
    def __cmp__(self, other):
        return cmp(self._pkg, other._pkg)
    def match(self, pkg):
        ''' Match if specific package versions (excluding build) agree

        Parameters
        ----------
        pkg : :py:class:`package <conda.package.package>` object
            package to match

        Returns
        -------
        matches : bool
            True if `pkg` matches the specified package version exactly, False otherwise

        '''
        return self._pkg.name == pkg.name and self._pkg.version == pkg.version


class exact_package(package_constraint):
    ''' constraint for matching exact packages

        Parameters
        ----------
        pkg : :py:class:`package <conda.package.package>` object
            package to match against

    '''
    def __init__(self, pkg):
        self._pkg = pkg
    def __str__(self):
        return 'build_version[%s]' % str(self._pkg)
    def __repr__(self):
        return 'build_version[%s]' % str(self._pkg)
    def __cmp__(self, other):
        return cmp(self._pkg, other._pkg)
    def match(self, pkg):
        ''' Match if specific package versions (including build) agree

        Parameters
        ----------
        pkg : :py:class:`package <conda.package.package>` object
            package to match

        Returns
        -------
        matches : bool
            True if `pkg` matches the specified package exactly, False otherwise

        '''
        return self._pkg == pkg


class build_target(package_constraint):
    ''' constraint for matching package build targets

    Parameters
    ----------
    req : str ``{'ce', 'pro'}``
        build target to match against

    '''
    def __init__(self, target):
        self._target = target
    def __str__(self):
        return 'build_target[%s]' % self._target
    def __repr__(self):
        return 'build_target[%s]' % self._target
    def __cmp__(self, other):
        return cmp(self._target, other._target)
    def match(self, pkg):
        ''' Match if a package has the specified build target, or no build target

        Parameters
        ----------
        pkg : :py:class:`package <conda.package.package>` object
            package to match

        Returns
        -------
        matches : bool
            True if `pkg` matches the specified build target, False otherwise

        '''
        return (not pkg.build_target) or pkg.build_target == self._target


class wildcard(package_constraint):
    ''' constraint that always matches everything

    '''
    def __str__(self):
        return 'wildcard'
    def __repr__(self):
        return 'wildcard'
    def __cmp__(self, other):
        return 0
    def match(self, pkg):
        ''' Match all packages

        Parameters
        ----------
        pkg : :py:class:`package <conda.package.package>` object
            package to match

        Returns
        -------
        matches : bool
            True

        '''
        return True
