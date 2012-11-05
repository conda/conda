from constraints import satisfies
from package import package
from requirement import find_inconsistent_requirements


class package_index(object):

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
        if not self._deps:
            self._deps = self._compute_dependencies()
        return self._deps

    @property
    def rdeps(self):
        if not self._rdeps:
            self._rdeps = self._compute_reverse_dependencies()
        return self._rdeps

    @property
    def package_names(self):
        return set([pkg.name for pkg in self.pkgs])

    def lookup_from_filename(self, pkg_filename):
        return self.pkg_filenames[pkg_filename]

    def lookup_from_canonical_name(self, canonical_name):
        return self.pkg_filenames[canonical_name+'.tar.bz2']

    def lookup_from_name(self, pkg_name):
        return set([pkg for pkg in self.pkgs if pkg.name == pkg_name])

    def find_matches(self, constraint, pkgs=None):
        if not pkgs is not None: pkgs = self.pkgs
        return set([pkg for pkg in pkgs if pkg.matches(constraint)])

    def get_deps(self, pkgs, max_depth=0):
        reqs = set()
        pkgs = set(pkgs)
        iterations = 0
        last_reqs = None

        while True:
            if max_depth and iterations >= max_depth: break
            for pkg in pkgs:
                reqs = reqs.union(self.deps.get(pkg, set()))
            if last_reqs is not None and reqs == last_reqs: break
            pkgs = self.find_compatible_packages(reqs) - pkgs
            last_reqs = reqs
            iterations += 1

        return reqs

    def get_reverse_deps(self, reqs, max_depth=0):
        pkgs = set()
        reqs = set(reqs)
        iterations = 0
        last_pkgs = None

        while True:
            if max_depth and iterations >= max_depth: break
            for req in reqs:
                pkgs = pkgs.union(self.rdeps.get(req, set()))
            if last_pkgs is not None and pkgs == last_pkgs: break
            reqs = self.find_compatible_requirements(pkgs) - reqs
            last_pkgs = pkgs
            iterations += 1

        return pkgs

    def find_compatible_requirements(self, pkgs):
        '''
        for a set of packages, find the complete set of requirements that all
        of the packages packages satisfy together
        '''
        reqs = set()
        for pkg in pkgs:
            for req in self.rdeps:
                if pkg.matches(satisfies(req)):
                    reqs.add(req)
        return reqs

    def find_compatible_packages(self, reqs):
        '''
        for a set of requirements, find the complete set of packages that
        satisfies all the requirements jointly
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
