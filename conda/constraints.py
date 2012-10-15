
class package_constraint(object):
    def match(self, info):
        raise NotImplementedError()
    def __hash__(self):
        return hash(str(self))


class all_of(package_constraint):
    '''
    Matches if a package matches all the specified constraints
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
    '''
    Matches if a package matches any of the specified constraints
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
    '''
    Matches if a package matches any of the specified constraints
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
    '''
    Matches if a package has the specified name
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
    '''
    Matches if a package contains the specified requirement
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
    '''
    Matches if a package contains the specified requirement, or no requirement
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
        for req in pkg.requires:
            if req.name == self._req.name and req.version != self._req.version:
                return False
        return True


class satisfies(package_constraint):
    '''
    Matches if a package satisfies the specified requirement
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
    '''
    Matches if a package satisfies the specified requirement
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
    '''
    Matches if specific package versions (excluding build) agree
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
    '''
    Matches if specific package versions (including build) agree
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
    '''
    Matches if a package has the specified build target, or no build target
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
    '''
    Matches all packages
    '''
    def __str__(self):
        return 'wildcard'
    def __repr__(self):
        return 'wildcard'
    def __cmp__(self, other):
        return 0
    def match(self, pkg):
        return True
