
class package_constraint(object):
    ''' Base class for specific package_constraint objects that match packages with
    specified criteria.
    '''
    def match(self, info):
        '''
        match criteria against package info

        Parameters
        ----------
        info : dict
            package info dictionary

        Returns
        -------
        matches : bool
            whether the specified package matches this constraint

        '''
        raise NotImplementedError()
    def __hash__(self):
        return hash(str(self))


class all_of(package_constraint):
    ''' Match if a package matches all the specified constraints

    Parameters
    ----------
    *constraints : :py:class:`package_constraint <conda.constraints.package_constraint>` objects
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
        for constraint in self._constraints:
            if not pkg.matches(constraint): return False
        return True


class any_of(package_constraint):
    ''' Match if a package matches any of the specified constraints

    Parameters
    ----------
    *constraints : :py:class:`package_constraint <conda.constraints.package_constraint>` objects
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
        for constraint in self._constraints:
            if pkg.matches(constraint): return True
        return False


class negate(package_constraint):
    ''' Match if a package does NOT match the specified constraint

    Parameters
    ----------
    constraint : :py:class:`package_constraint <conda.constraints.package_constraint>` object
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
        return not pkg.matches(self._constraint)


class named(package_constraint):
    ''' Match if a package has the specified name

    Parameters
    ----------
    name : str
        :ref:`package name <package_name>` to match
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
        return pkg.name == self._name


class strict_requires(package_constraint):
    ''' Match if a package contains the specified requirement

    Parameters
    ----------
    req : :py:class:`package_spec <conda.package_spec.package_spec>` object
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
        # package never requires itself
        if pkg.name == self._req.name: return False
        for req in pkg.requires:
            if req.name == self._req.name and req.version == self._req.version:
                return True
        return False


class requires(package_constraint):
    ''' Match if a package contains the specified requirement, or no requirement

    Parameters
    ----------
    req : :py:class:`package_spec <conda.package_spec.package_spec>` object
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
        # package never requires itself
        if pkg.name == self._req.name: return False
        vlen = len(self._req.version.version)
        for req in pkg.requires:
            if req.name == self._req.name and req.version.version[:vlen] != self._req.version.version[:vlen]:
                return False
        return True


class satisfies(package_constraint):
    ''' Match if a package satisfies the specified requirement

    Parameters
    ----------
    req : :py:class:`package_spec <conda.package_spec.package_spec>` object
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
        if self._req.name != pkg.name: return False
        vlen = len(self._req.version.version)
        try:
            return self._req.version.version[:vlen] == pkg.version.version[:vlen]
        except:
            return False

class weak_satisfies(package_constraint):
    ''' Match if a package satisfies the specified requirement

    Parameters
    ----------
    req : :py:class:`package_spec <conda.package_spec.package_spec>` object
    '''
    def __init__(self, req):
        self._req = req
    def __str__(self):
        return 'weak_satisfies[%s]' % str(self._req)
    def __repr__(self):
        return 'weak_satisfies[%s]' % str(self._req)
    def __cmp__(self, other):
        return cmp(self._req, other._req)
    def match(self, pkg):
        if self._req.name != pkg.name: return True
        vlen = len(self._req.version.version)
        try:
            return self._req.version.version[:vlen] == pkg.version.version[:vlen]
        except:
            return False


class package_version(package_constraint):
    ''' Match if specific package versions (excluding build) agree
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
        return self._pkg.name == pkg.name and self._pkg.version == pkg.version


class build_version(package_constraint):
    ''' Match if specific package versions (including build) agree
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
        return self._pkg == pkg


class build_target(package_constraint):
    ''' Match if a package has the specified build target, or no build target

    Parameters
    ----------
    req : str ``{'ce', 'pro'}``
        build target to match
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
        return (not pkg.build_target) or pkg.build_target == self._target


class wildcard(package_constraint):
    ''' Match all packages
    '''
    def __str__(self):
        return 'wildcard'
    def __repr__(self):
        return 'wildcard'
    def __cmp__(self, other):
        return 0
    def match(self, pkg):
        return True
