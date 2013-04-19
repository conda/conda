# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
''' The package_index module provides the `PackageIndex` class, which is the
primary interface for looking up packages and their dependencies, matching
packages to constraints, etc.

'''


from constraints import Satisfies
from package import group_packages_by_name, Package
from package_spec import find_inconsistent_specs


class PackageIndex(object):
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

        self.pkg_filenames = dict()
        self.pkg_names = dict()
        self.pkgs = set()
        self.pkg_features = dict()
        for pkg_filename, pkg_info in info.items():

            pkg = Package(pkg_info)

            self.pkgs.add(pkg)

            self.pkg_filenames[pkg_filename] = pkg

            if not self.pkg_names.has_key(pkg.name):
                self.pkg_names[pkg.name] = set()
            self.pkg_names[pkg.name].add(pkg)

            for feature in pkg.features:
                if not self.pkg_features.has_key(feature):
                    self.pkg_features[feature] = set()
                self.pkg_features[feature].add(pkg)

        # compute on demand
        self._deps = None
        self._rdeps = None
        self._names = None

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
        if not self._names:
            self._names = set([pkg.name for pkg in self.pkgs])
        return self._names

    def lookup_from_filename(self, pkg_filename):
        ''' Return a :py:class`Package <conda.package.Package>` object corresponding to the given package filename

        Parameters
        ----------
        pkg_filename : str
            package filename of package to look up

        Returns
        -------
        package : :py:class`Package <conda.package.Package>` object
            matching package, if one is found

        '''
        return self.pkg_filenames[pkg_filename]

    def lookup_from_canonical_name(self, canonical_name):
        ''' Return a :py:class`Package <conda.package.Package>` object corresponding to the given canonical name

        Parameters
        ----------
        canonical_name : str
            canonical_name of package to look up

        Returns
        -------
        package : :py:class`Package <conda.package.Package>` object
            matching package, if one is found

        '''
        return self.pkg_filenames[canonical_name+'.tar.bz2']

    def lookup_from_name(self, pkg_name):
        ''' Return a set of :py:class`Package <conda.package.Package>` objects with the given package name

        Parameters
        ----------
        name : str
            name of packages to look up

        Returns
        -------
        package : set of :py:class`Package <conda.package.Package>` objects
            matching packages

        '''
        return self.pkg_names[pkg_name]

    def lookup_from_feature(self, feature):
        ''' Return a set of :py:class`Package <conda.package.Package>` objects that provide the given feature.

        Parameters
        ----------
        feature : str
            name of feature to look up

        Returns
        -------
        package : set of :py:class`Package <conda.package.Package>` objects
            matching packages

        '''
        return self.pkg_features.get(feature, set())

    def find_matches(self, constraint, pkgs=None):
        ''' Return a set of :py:class`Package <conda.package.Package>` objects that match the given constraint

        Parameters
        ----------
        constraint : :py:class:`PackageConstraint <conda.constraints.PackageConstraint>` object
            constraint to match
        pkgs : iterable of :py:class`Package <conda.package.Package>` objects, optional
            if supplied, search only packages in this collection

        Returns
        -------
        matches : set of iterable of :py:class`Package <conda.package.Package>` objects
            matching packages

        '''
        if pkgs is None: pkgs = self.pkgs
        return set([pkg for pkg in pkgs if pkg.matches(constraint)])

    def feature_select(self, pkgs, track_features):
        ''' Return a set of :py:class`Package <conda.package.Package>` objects that track the given features

        Parameters
        ----------
        pkgs : iterable of :py:class`Package <conda.package.Package>` objects
            collection of packages to select from
        track_features : iterable of str
            features to select for

        Returns
        -------
        matches : set of iterable of :py:class`Package <conda.package.Package>` objects
            matching packages

        '''
        package_groups = {}
        others = set(pkgs)
        for pkg in pkgs:
            for f in pkg.features:
                if f not in package_groups:
                    package_groups[f] = set()
                package_groups[f].add(pkg)
                others.remove(pkg)
        for feature in track_features:
            fpkgs = self.lookup_from_feature(feature)
            if feature in package_groups:
                package_groups[feature] &= fpkgs
        result = set([])
        for pkgs in package_groups.values():
            for pkg in pkgs:
                if (pkg.features - track_features):
                    continue
                result.add(pkg)
        return result.union(others)


    def get_deps(self, pkgs, max_depth=0):
        ''' Return mutual package dependencies for a collection of packages

        Parameters
        ----------
        pkgs : iterable of :py:class:`Package <conda.package.Package>` objects
            packages to find dependencies for
        max_depth : bool, optional
            how many levels of the dependency graph to search, defaults to 0 (all levels)

        Returns
        -------
        deps : set of :py:class:`PackageSpec <conda.package_spec.PackageSpec>` objects
            mutual dependencies of all the supplied packages

        '''
        deps = set()
        pkgs = set(pkgs)
        iterations = 0
        last_deps = None

        while True:
            if max_depth and iterations >= max_depth: break
            for pkg in pkgs:
                deps |= self.deps.get(pkg, set())
            if deps == last_deps: break
            pkgs = deps - pkgs
            last_deps = deps
            iterations += 1

        return deps

    def get_reverse_deps(self, pkgs, max_depth=0):
        ''' Return mutual reverse dependencies for a collection of requirements

        Parameters
        ----------
        pkgs : iterable of  :py:class:`Package <conda.package.package>` objects
            packages to find reverse dependencies for
        max_depth : bool, optional
            how many levels of the reverse dependency graph to search, defaults to 0 (all levels)

        Returns
        -------
        rdeps : set of :py:class:`Package <conda.package.Package>` objects
            mutual reverse dependencies of all the supplied requirements

        '''
        rdeps = set()
        pkgs = set(pkgs)
        iterations = 0
        last_rdeps = None

        while True:
            if max_depth and iterations >= max_depth: break
            for pkg in pkgs:
                rdeps |= self.rdeps.get(pkg, set())
            if rdeps == last_rdeps: break
            pkgs = rdeps - pkgs
            last_rdeps = rdeps
            iterations += 1

        return rdeps

    def find_compatible_requirements(self, pkgs):
        '''
        For a set of packages, return the complete set of requirements that all
        of the packages packages satisfy together.

        Parameters
        ----------
        pkgs : iterable of :py:class:`PackageConstraint <conda.constraints.PackageConstraint>` objects
            collection of packages to compile requirements for

        Returns
        -------
        reqs : set of :py:class:`PackageSpec <conda.package_spec.PackageSpec>` objects
            package specifications satisfied by all the given packages

        '''
        reqs = set()
        for pkg in pkgs:
            for req in self.rdeps:
                if pkg.matches(Satisfies(req)):
                    reqs.add(req)
        return reqs

    def find_compatible_packages(self, reqs):
        '''
        For a set of requirements, return the complete set of packages that
        satisfies all the requirements jointly.

        Parameters
        ----------
        reqs : iterable of py:class:`PackageSpec <conda.package_spec.PackageSpec>` objects
            collection of package specifications to find packages for

        Returns
        -------
        pkgs : set of :py:class:`PackageConstraint <conda.constraints.PackageConstraint>` objects:
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
                pkgs = pkgs | self.find_matches(Satisfies(req))

        # remove any packages whose requirements are inconsistent with the
        # user specified requirements
        to_remove = set()
        for pkg in pkgs:
            inconsistent = find_inconsistent_specs(reqs | pkg.requires)
            if inconsistent: to_remove.add(pkg)
        pkgs = pkgs - to_remove

        return pkgs

    def _compute_dependencies(self):
        deps = dict()
        for pkg in self.pkgs:
            deps[pkg] = set()
            for req in pkg.requires:
                deps[pkg] |= self.find_matches(Satisfies(req))
        return deps

    def _compute_reverse_dependencies(self):
        rdeps = dict()
        for pkg, deps in self.deps.items():
            if pkg.is_meta: continue
            for dep in deps:
                if dep not in rdeps:
                    rdeps[dep] = set()
                rdeps[dep].add(pkg)
        return rdeps

