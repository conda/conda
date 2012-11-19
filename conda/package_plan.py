
from difflib import get_close_matches
import logging


from config import DEFAULT_NUMPY_SPEC, DEFAULT_PYTHON_SPEC
from constraints import build_target, satisfies
from install import make_available, activate, deactivate
from package import newest_packages, sort_packages_by_name
from progressbar import Bar, ETA, FileTransferSpeed, Percentage, ProgressBar
from remote import fetch_file
from package_spec import apply_default_spec, package_spec, find_inconsistent_specs


__all__ = [
    'package_plan',
    'create_create_plan',
    'create_deactivate_plan',
    'create_upgrade_plan',
    'create_download_plan'
]


log = logging.getLogger(__name__)


class package_plan(object):
    '''
    Encapsulates a package management action, describing all operations to
    take place. Operations include downloading packages from a repository,
    activating and deactivating available packages. Additionally, package_plan
    objects report any packages that will be left with unmet dependencies as a
    result of this action.
    '''

    __slots__ = ['downloads', 'activations', 'deactivations', 'broken', 'missing', 'upgrade']

    def __init__(self):
        self.downloads     = set()
        self.activations   = set()
        self.deactivations = set()
        self.broken        = set()
        self.missing       = set()
        self.upgrade       = None

    def execute(self, env, progress_bar=True):
        '''
        Perform the operations contained in the package plan

        Parameters
        ----------
        env : :py:class:`environment <conda.environment.environment>` object
            Anaconda environment to execute plan in
        progress_bar : bool, optional
            whether to show a progress bar during any downloads

        '''
        for pkg in self.downloads:
            if progress_bar:
                widgets = [
                    ' ', Percentage(), ' ', Bar(), ' ', ETA(), ' ', FileTransferSpeed()
                ]
                progress = ProgressBar(widgets=widgets)
            else:
                progress = None
            fetch_file(pkg.filename, md5=pkg.md5, size=pkg.size,
                       progress=progress)
            make_available(env.conda.packages_dir, pkg.canonical_name)
        for pkg in self.deactivations:
            deactivate(pkg.canonical_name, env.prefix)
        for pkg in self.activations:
            activate(env.conda.packages_dir, pkg.canonical_name, env.prefix)

    def empty(self):
        ''' Return whether the package plan has any operations to perform or not

        Returns
        -------
        empty bool
            True if the package plan contains no operations to perform
        '''
        return not (self.downloads or self.activations or self.deactivations)

    def __str__(self):
        result = ''
        if self.downloads:
            result += download_string % self._format_packages(self.downloads,
                                                              lookup_repo=True)
        if self.activations:
            result += activate_string % self._format_packages(self.activations)
        if self.deactivations:
            result += deactivate_string % self._format_packages(
                                                 self.deactivations)
        if self.broken:
            result += broken_string % self._format_packages(self.broken)
        if self.missing:
            result += missing_string % self._format_packages(self.missing)
        return result

    def _format_packages(self, pkgs, lookup_repo=False):
        result = ''
        if lookup_repo:
            for pkg in sort_packages_by_name(pkgs):
                result += '\n        %s [%s]' % (pkg.filename, pkg.location)
        else:
            for pkg in sort_packages_by_name(pkgs):
                result += '\n        %s  (build: %s)' % (pkg, pkg.build)
        return result


def create_create_plan(prefix, conda, spec_strings, use_defaults):
    '''
    This functions creates a package plan for activating packages in a new
    Anaconda environement, including all of their required dependencies. The
    desired packages are specified as constraints.

    Parameters
    ----------
    prefix : str
        directory to create new Anaconda environment in
    conda : :py:class:`anaconda <conda.anaconda.anaconda>` object
    spec_strings : iterable of str
        package specification strings for packages to install in new Anaconda environment
    use_defaults : bool
        whether to automatically apply default versions for base packages

    Raises
    ------
    RuntimeError
        if the environment cannot be created

    '''
    plan = package_plan()

    idx = conda.index

    specs = set()

    for spec_string in spec_strings:

        if spec_string == 'python':
            specs.add(package_spec(DEFAULT_PYTHON_SPEC))
            continue

        if spec_string == 'numpy':
            specs.add(package_spec(DEFAULT_NUMPY_SPEC))
            continue

        spec = package_spec(spec_string)

        _check_unknown_spec(idx, spec)

        specs.add(spec)

    # abort if specifications are already incondsistent at this point
    inconsistent = find_inconsistent_specs(specs)
    if inconsistent:
        raise RuntimeError(
            'cannot create environment, the following requirements are inconsistent: %s' % str(inconsistent)
        )

    log.debug("initial package specifications: %s\n" % specs)

    # find packages compatible with the initial specifications and build target
    pkgs = idx.find_compatible_packages(specs)
    pkgs = idx.find_matches(build_target(conda.target), pkgs)
    log.debug("initial packages: %s\n" % pkgs)

    # find the associated dependencies
    deps = idx.get_deps(pkgs)
    deps = idx.find_matches(build_target(conda.target), deps)
    log.debug("initial dependencies: %s\n" % deps)

    # add default python and numpy requirements if needed
    if use_defaults:
        dep_names = [dep.name for dep in deps]
        if 'python' in dep_names:
            specs = apply_default_spec(specs, package_spec(DEFAULT_PYTHON_SPEC))
        if 'numpy' in dep_names:
            specs = apply_default_spec(specs, package_spec(DEFAULT_NUMPY_SPEC))

    log.debug("updated package specifications: %s\n" % specs)

    # now we need to recompute the compatible packages using the updated package specifications
    pkgs = idx.find_compatible_packages(specs)
    pkgs = idx.find_matches(build_target(conda.target), pkgs)
    pkgs = newest_packages(pkgs)
    log.debug("updated packages: %s\n" % pkgs)

    # find the associated dependencies
    deps = idx.get_deps(pkgs)
    deps = idx.find_matches(build_target(conda.target), deps)
    deps = newest_packages(deps)
    log.debug("updated dependencies: %s\n" % deps)

    all_pkgs = pkgs | deps
    all_pkgs = newest_packages(all_pkgs)
    log.debug("all packages: %s\n" % all_pkgs)

    # make sure all user supplied specs were satisfied
    for spec in specs:
        if not idx.find_matches(satisfies(spec), all_pkgs):
            raise RuntimeError("could not find package for package specification '%s' compatible with other requirements" % spec)

    # download any packages that are not available
    for pkg in all_pkgs:
        if pkg not in conda.available_packages:
            plan.downloads.add(pkg)

    plan.activations = all_pkgs

    return plan


def create_install_plan(env, spec_strings):
    '''
    This functions creates a package plan for activating packages in an
    existing Anaconda environement, including removing existing verions and
    also activating all required dependencies. The desired packages are
    specified as package names, package filenames, or package_spec strings.

    Parameters
    ----------
    env : :py:class:`environment <conda.environment.environment>` object
        Anaconda environment to install packages into
    spec_strings : iterable of str
        string package specifications of packages to install in Anaconda environment

    Raises
    ------
    RuntimeError
        if the install cannot be performed

    '''
    plan = package_plan()

    idx = env.conda.index

    specs = set()

    for spec_string in spec_strings:

        spec = package_spec(spec_string)

        _check_unknown_spec(idx, spec)

        if spec.name == 'python' and env.find_activated_package('python'):
            raise RuntimeError('changing python versions in an existing Anaconda environment is not supported (create a new environment)')
        if spec.name == 'numpy' and env.find_activated_package('numpy'):
            raise RuntimeError('changing numpy versions in an existing Anaconda environment is not supported (create a new environment)')

        specs.add(spec)

    # abort if specifications are already incondsistent at this point
    inconsistent = find_inconsistent_specs(specs)
    if inconsistent:
        raise RuntimeError(
            'cannot create environment, the following requirements are inconsistent: %s' % str(inconsistent)
        )

    log.debug("initial package specifications: %s\n" % specs)

    # find packages compatible with the initial specifications and build target
    pkgs = idx.find_compatible_packages(specs)
    pkgs = idx.find_matches(env.requirements, pkgs)
    log.debug("initial packages: %s\n" % pkgs)

    # find the associated dependencies
    deps = idx.get_deps(pkgs)
    deps = idx.find_matches(env.requirements, deps)
    log.debug("initial dependencies: %s\n" % deps)

    # add default python and numpy requirements if needed
    if True:
        dep_names = [dep.name for dep in deps]
        if 'python' in dep_names and not env.find_activated_package('python'):
            specs = apply_default_spec(specs, package_spec(DEFAULT_PYTHON_SPEC))
        if 'numpy' in dep_names and not env.find_activated_package('python'):
            specs = apply_default_spec(specs, package_spec(DEFAULT_NUMPY_SPEC))

    log.debug("updated package specifications: %s\n" % specs)

    # now we need to recompute the compatible packages using the updated package specifications
    pkgs = idx.find_compatible_packages(specs)
    pkgs = idx.find_matches(env.requirements, pkgs)
    pkgs = newest_packages(pkgs)
    log.debug("updated packages: %s\n" % pkgs)

    # find the associated dependencies
    deps = idx.get_deps(pkgs)
    deps = idx.find_matches(env.requirements, deps)
    deps = newest_packages(deps)
    log.debug("updated dependencies: %s\n" % deps)

    all_pkgs = pkgs | deps
    all_pkgs = newest_packages(all_pkgs)
    log.debug("all packages: %s\n" % all_pkgs)

    # make sure all user supplied specs were satisfied
    for spec in specs:
        if not idx.find_matches(satisfies(spec), all_pkgs):
            if idx.find_matches(satisfies(spec)):
                raise RuntimeError("could not find package for package specification '%s' compatible with other requirements" % spec)
            else:
                raise RuntimeError("could not find package for package specification '%s'" % spec)

    # download any packages that are not available
    for pkg in all_pkgs:

        # download any currently unavailable packages
        if pkg not in env.conda.available_packages:
            plan.downloads.add(pkg)

        # see if the package is already active
        active = env.find_activated_package(pkg.name)
        if active and pkg != active:
            plan.deactivations.add(active)

        if pkg not in env.activated:
            plan.activations.add(pkg)

    return plan


def create_upgrade_plan(env, pkg_names):
    '''
    This function creates a package plan for upgrading specified packages to
    the latest version in the given Anaconda environment prefix. Only versions
    compatible with the existing environment are considered.

    Parameters
    ----------
    env : :py:class:`environment <conda.environment.environment>` object
        Anaconda environment to upgrade packages in
    pkg_names : iterable of str
        package names of packages to upgrade

    Raises
    ------
    RuntimeError
        if the upgrade cannot be performed

    '''

    plan = package_plan()

    idx = env.conda.index

    if len(pkg_names) == 0:
        pkgs = env.activated
    else:
        pkgs = set()
        for pkg_name in pkg_names:
            pkg = env.find_activated_package(pkg_name)
            if not pkg:
                if pkg_name in env.conda.index.package_names:
                    raise RuntimeError("package '%s' is not installed, cannot upgrade (see conda install -h)" % pkg_name)
                else:
                    raise RuntimeError("unknown package '%s', cannot upgrade" % pkg_name)
            pkgs.add(pkg)

    # find any packages that have newer versions
    upgrades = set()
    to_remove = set()
    for pkg in pkgs:
        candidates = idx.lookup_from_name(pkg.name)
        candidates = idx.find_matches(env.requirements, candidates)
        newest = max(candidates)
        log.debug("%s > %s == %s" % (newest.canonical_name, pkg.canonical_name, newest>pkg))
        if newest > pkg:
            upgrades.add(newest)
            to_remove.add(pkg)

    log.debug('initial upgrades: %s' %  upgrades)

    if len(upgrades) == 0: return plan  # nothing to do

    # get all the dependencies of the upgrades
    all_reqs = idx.get_deps(upgrades)
    log.debug('upgrade dependencies: %s' %  all_reqs)

    # find newest packages compatible with these requirements and the build target
    all_pkgs = idx.find_compatible_packages(all_reqs) | upgrades
    all_pkgs = idx.find_matches(build_target(env.conda.target), all_pkgs)
    all_pkgs = newest_packages(all_pkgs)
    log.debug('all packages: %s' %  all_pkgs)

    # check for any inconsistent requirements the set of packages
    # inconsistent = find_inconsistent_specs(idx.get_deps(all_pkgs))
    # if inconsistent:
    #     raise RuntimeError('cannot upgrade packages, the following requirements are inconsistent: %s'
    #         % ', '.join('%s-%s' % (req.name, req.version.vstring) for req in inconsistent)
    #     )

    # deactivate original packages and activate new versions
    plan.deactivations = to_remove

    # download any activations that are not already availabls
    for pkg in all_pkgs:
        if pkg not in env.conda.available_packages:
            plan.downloads.add(pkg)
        if pkg not in env.activated:
            plan.activations.add(pkg)

    return plan


def create_activate_plan(env, canonical_names):
    '''
    This function creates a package plan for activating the specified packages
    in the given Anaconda environment prefix.

    Parameters
    ----------
    env : :py:class:`environment <conda.environment.environment>` object
        Anaconda environment to activate packages in
    canonical_names : iterable of str
        canonical names of packages to activate

    '''
    plan = package_plan()

    idx = env.conda.index

    for canonical_name in canonical_names:

        try:
            pkg = idx.lookup_from_canonical_name(canonical_name)
        except:
            # can't activate a package we know nothing about
            continue  # TODO warn?

        # if package is already activated, there is nothing to do
        if pkg in env.activated:
            continue  # TODO warn?

        plan.activations.add(pkg)

        # add or warn about missing dependencies
        deps = idx.find_compatible_packages(idx.get_deps(plan.activations))
        deps = idx.find_matches(env.requirements, deps)
        for dep in deps:
            if dep not in env.activated:
                plan.missing.add(dep)

    return plan


def create_deactivate_plan(env, canonical_names):
    '''
    This function creates a package plan for deactivating the specified packages
    in the given Anaconda environment prefix.

    Parameters
    ----------
    env : :py:class:`environment <conda.environment.environment>` object
        Anaconda environment to deactivate packages in
    canonical_names : iterable of str
        canonical names of packages to deactivate

    '''
    plan = package_plan()

    idx = env.conda.index

    for canonical_name in canonical_names:

        try:
            pkg = idx.lookup_from_canonical_name(canonical_name)
        except:
            # can't deactivate a package we know nothing about
            continue  # TODO warn?

        # if package is not already activated, there is nothing to do
        if pkg not in env.activated:
            continue  # TODO warn?

        plan.deactivations.add(pkg)

    # find a requirement for this package that we can use to lookup reverse deps
    reqs = idx.find_compatible_requirements(plan.deactivations)

    # warn about broken reverse dependencies
    for rdep in idx.get_reverse_deps(reqs):
        if rdep in env.activated:
           plan.broken.add(rdep)

    return plan


def create_download_plan(conda, canonical_names, force):
    '''
    This function creates a package plan for downloading the specified
    packages from remote Anaconda package repositories. By default,
    packages already available are ignored, but this can be overriden
    with the force argument.

    Parameters
    ----------
    conda : :py:class:`anaconda <conda.anaconda.anaconda>` object
        Anaconda installation to download packages into
    canonical_names : iterable of str
        canonical names of packages to download
    force : bool
        whether to force download even if package is already locally available

    '''
    plan = package_plan()

    idx = conda.index

    for canonical_name in canonical_names:

        try:
            pkg = idx.lookup_from_canonical_name(canonical_name)
        except:
            raise RuntimeError(
                "download of '%s' failed, no match found" % canonical_name
            )

        if force or pkg not in conda.available_packages:
            plan.downloads.add(pkg)

    return plan



def _check_unknown_spec(idx, spec):

    if spec.name not in idx.package_names:
        message = "unknown package name '%s'" % spec.name
        close = get_close_matches(spec.name, idx.package_names)
        if close:
            message += '\n\nDid you mean one of these?\n'
            for s in close:
                message += '    %s' % s
            message += "\n"
        raise RuntimeError(message)



download_string = '''
    The following packages will be downloaded:
        %s
'''

activate_string = '''
    The following packages will be activated:
        %s
'''

deactivate_string = '''
    The following packages will be DE-activated:
        %s
'''

broken_string = '''
    The following packages will be left with BROKEN dependencies after this operation:
        %s
'''

missing_string = '''
    After this operation, the following dependencies will be MISSING:
        %s
'''
