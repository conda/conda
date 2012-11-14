''' The package_index module provides the package_index class, which is the primary interface for looking up packages and their
dependencies, matching packages to constraints, etc.

'''


from constraints import satisfies
from package import package
from requirement import find_inconsistent_requirements


class package_index(object):
    ''' Encapsulates an Anaconda package index

    Parameters
    ----------
    info : dict
        dictionary of (package filename : package info) pairs

    Attributes
    ----------
    deps
    package_names
    rdeps

    '''

    def __init__(self, info):

        self.pkg_filenames = dict(
            (pkg_filename, package(pkg_info))
            for pkg_filename, pkg_info in info.items()
        )

        self.pkgs = set(
            package(pkg_info) for pkg_info in info.values()
        )

        # compute on demand
        self._deps = None
        self._rdeps = None
        self._compatible_pkgs = None
        self._compatible_reqs = None

    @property
    def deps(self):
        ''' Return the entire dependency graph '''
        if not self._deps:
            self._deps = self._compute_dependencies()
        return self._deps

    @property
    def rdeps(self):
        ''' Return the entire reverse dependency graph '''
        if not self._rdeps:
            self._rdeps = self._compute_reverse_dependencies()
        return self._rdeps

    @property
    def package_names(self):
        ''' Return a set of all package names for packages in this index '''
        return set([pkg.name for pkg in self.pkgs])

    def lookup_from_filename(self, pkg_filename):
        ''' Return a :py:class`package <conda`.package.package>` object corresponding to the given package filename

        Parameters
        ----------
        pkg_filename : str
            package filename of package to look up

        Returns
        -------
        package : :py:class`package <conda`.package.package>` object
            matching package, if one is found

        '''
        return self.pkg_filenames[pkg_filename]

    def lookup_from_canonical_name(self, canonical_name):
        ''' Return a :py:class`package <conda`.package.package>` object corresponding to the given canonical name

        Parameters
        ----------
        canonical_name : str
            canonical_name of package to look up

        Returns
        -------
        package : :py:class`package <conda`.package.package>` object
            matching package, if one is found

        '''
        return self.pkg_filenames[canonical_name+'.tar.bz2']

    def lookup_from_name(self, pkg_name):
        ''' Return a set of :py:class`package <conda`.package.package>` objects with the given package name

        Parameters
        ----------
        name : str
            name of packages to look up

        Returns
        -------
        package : set of :py:class`package <conda`.package.package>` objects
            matching packages

        '''
        return set([pkg for pkg in self.pkgs if pkg.name == pkg_name])

    def find_matches(self, constraint, pkgs=None):
        ''' Return a set of :py:class`package <conda`.package.package>` objects that match the given constraint

        Parameters
        ----------
        constraint : :py:class:`constraint <conda.constraints.package_constraint>` object
            constraint to match
        pkgs : iterable of :py:class`package <conda`.package.package>` objects, optional
            if supplied, search only packages in this collection

        Returns
        -------
        matches : set of iterable of :py:class`package <conda`.package.package>` objects
            matching packages

        '''
        if not pkgs is not None: pkgs = self.pkgs
        return set([pkg for pkg in pkgs if pkg.matches(constraint)])

    def get_deps(self, pkgs, max_depth=0):
        ''' Return mutual package dependencies for a collection of packages

        Parameters
        ----------
        pkgs : iterable of :py:class:`constraint <conda.constraints.package_constraint>` objects
            packages to find dependencies for
        max_depth : bool, optional
            how many levels of the dependency graph to search, defaults to 0 (all levels)

        Returns
        -------
        deps : set of :py:class:`requirement <conda.requirement.requirement>` objects
            mutual dependencies of all the supplied packages

        '''
        reqs = set()
        pkgs = set(pkgs)
        iterations = 0
        last_reqs = None

        while True:
            if max_depth and iterations >= max_depth: break
            for pkg in pkgs:
                reqs = reqs.union(self.deps.get(pkg, set()))
            if reqs == last_reqs: break
            pkgs = self.find_compatible_packages(reqs) - pkgs
            last_reqs = reqs
            iterations += 1

        return reqs

    def get_reverse_deps(self, reqs, max_depth=0):
        ''' Return mutual reverse dependencies for a collection of requirements

        Parameters
        ----------
        reqs : iterable of  :py:class:`requirement <conda.requirement.requirement>` objects
            requirements to find reverse dependencies for
        max_depth : bool, optional
            how many levels of the reverse dependency graph to search, defaults to 0 (all levels)

        Returns
        -------
        rdeps : set of :py:class:`constraint <conda.constraints.package_constraint>` objects
            mutual reverse dependencies of all the supplied requirements

        '''
        pkgs = set()
        reqs = set(reqs)
        iterations = 0
        last_pkgs = None

        while True:
            if max_depth and iterations >= max_depth: break
            for req in reqs:
                pkgs = pkgs.union(self.rdeps.get(req, set()))
            if pkgs == last_pkgs: break
            reqs = self.find_compatible_requirements(pkgs) - reqs
            last_pkgs = pkgs
            iterations += 1

        return pkgs

    def find_compatible_requirements(self, pkgs):
        '''
        For a set of packages, return the complete set of requirements that all
        of the packages packages satisfy together.

        Parameters
        ----------
        pkgs : iterable of :py:class:`constraint <conda.constraints.package_constraint>` objects
            collection of packages to compile requirements for

        Returns
        -------
        reqs : set of :py:class:`requirement <conda.requirement.requirement>` objects
            requirements satisfied by all the given packages

        '''
        reqs = set()
        for pkg in pkgs:
            for req in self.rdeps:
                if pkg.matches(satisfies(req)):
                    reqs.add(req)
        return reqs

    def find_compatible_packages(self, reqs):
        '''
        For a set of requirements, return the complete set of packages that
        satisfies all the requirements jointly.

        Parameters
        ----------
        reqs : iterable of py:class:`requirement <conda.requirement.requirement>` objects
            collection of requirements to find packages for

        Returns
        -------
        pkgs : set of :py:class:`constraint <conda.constraints.package_constraint>` objects:
            packages that satisfy by all the given requirements

        '''
        pkgs = set()

        # find all the packages that satisfy any of the requirements (these may
        # include packages inconsistent with other requirements)
        for req in reqs:
            if req.build:
                pkg_filename = "%s-%s-%s.tar.bz2" % (req.name,
                                                     req.version.vstring,
                                                     req.build)
                pkgs.add(self.lookup_from_filename(pkg_filename))
            else:
                pkgs = pkgs | self.find_matches(satisfies(req))

        # remove any packages whose requirements are inconsistent with the
        # user specified requirements
        to_remove = set()
        for pkg in pkgs:
            inconsistent = find_inconsistent_requirements(reqs | pkg.requires)
            if inconsistent: to_remove.add(pkg)
        pkgs = pkgs - to_remove

        return pkgs

    def _compute_dependencies(self):
        deps = {}
        for pkg in self.pkgs:
            deps[pkg] = pkg.requires
        return deps

    def _compute_reverse_dependencies(self):
        rdeps = {}
        for pkg in self.deps:
            if pkg.name == 'anaconda': continue # special case, otherwise everything gets swallowed
            for req in pkg.requires:
                if req not in rdeps:
                    rdeps[req] = set()
                rdeps[req].add(pkg)
        return rdeps
