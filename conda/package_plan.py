# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
''' The package_plan module provides the `package_plan` class, which encapsulates
executing sets of operations that modify Anaconda environments, as well as functions
for creating package_plans for different circumstances.

'''
from difflib import get_close_matches
import logging


from config import DEFAULT_NUMPY_SPEC, DEFAULT_PYTHON_SPEC
from constraints import all_of, any_of, build_target, requires, satisfies
from install import make_available, activate, deactivate
from package import find_inconsistent_packages, newest_packages, sort_packages_by_name
from progressbar import Bar, ETA, FileTransferSpeed, Percentage, ProgressBar
from remote import fetch_file
from package_spec import package_spec, find_inconsistent_specs


__all__ = [
    'package_plan',
    'create_create_plan',
    'create_deactivate_plan',
    'create_update_plan',
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

    __slots__ = ['downloads', 'activations', 'deactivations', 'broken', 'missing', 'update']

    def __init__(self):
        self.downloads     = set()
        self.activations   = set()
        self.deactivations = set()
        self.broken        = set()
        self.missing       = set()
        self.update       = None

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
        if progress_bar:
            download_widgets = [
                '', ' ', Percentage(), ' ', Bar(), ' ', ETA(), ' ', FileTransferSpeed()
            ]
            download_progress = ProgressBar(widgets=download_widgets)

            package_widgets = ['', ' ', Bar(), ' ', Percentage()]
            package_progress = ProgressBar(widgets=package_widgets)
        else:
            download_progress = None
            package_progress = None

        self._handle_downloads(env, download_progress)
        self._handle_deactivations(env, package_progress)
        self._handle_activations(env, package_progress)

    def _handle_downloads(self, env, progress):
        if progress and self.downloads:
            print
            print "Fetching packages..."
            print

        for pkg in self.downloads:
            fetch_file(pkg.filename, md5=pkg.md5, size=pkg.size, progress=progress)
            make_available(env.conda.packages_dir, pkg.canonical_name)

    def _handle_deactivations(self, env, progress):
        if progress and self.deactivations:
            print
            print "Deactivating packages..."
            print
            progress.maxval = len(self.deactivations)
            progress.start()

        for i, pkg in enumerate(self.deactivations):
            if progress:
                progress.widgets[0] = '[%-20s]' % pkg.name
                progress.update(i)
            deactivate(pkg.canonical_name, env.prefix)

        if progress and self.deactivations:
            progress.widgets[0] = '[      COMPLETE      ]'
            progress.finish()

    def _handle_activations(self, env, progress):
        if progress and self.activations:
            print
            print "Activating packages..."
            print
            progress.maxval = len(self.activations)
            progress.start()

        for i, pkg in enumerate(self.activations):
            if progress:
                progress.widgets[0] = '[%-20s]' % pkg.name
                progress.update(i)
            activate(env.conda.packages_dir, pkg.canonical_name, env.prefix)

        if progress and self.activations:
            progress.widgets[0] = '[      COMPLETE      ]'
            progress.finish()

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
            result += download_string % self._format_packages(self.downloads, use_location=True)
        if self.deactivations:
            result += deactivate_string % self._format_packages(self.deactivations)
        if self.activations:
            result += activate_string % self._format_packages(self.activations)
        if self.broken:
            result += broken_string % self._format_packages(self.broken)
        if self.missing:
            result += missing_string % self._format_packages(self.missing)
        return result

    def _format_packages(self, pkgs, use_location=False):
        result = ''
        if use_location:
            for pkg in sort_packages_by_name(pkgs):
                result += '    %s [%s]\n' % (pkg.filename, pkg.location)
        else:
            result += "    %-25s  |  %-15s\n" % ('package', 'build')
            result += "    %-25s  |  %-15s\n" % ('-'*25, '-'*15)
            for pkg in sort_packages_by_name(pkgs):
                result += '    %-25s  |  %15s\n' % (pkg, pkg.build)
        return result


def create_create_plan(prefix, conda, spec_strings):
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

    Returns
    -------
    plan: :py:class:`package_plan <conda.package_plan.package_plan>`
        package plan for creating new Anaconda environment

    Raises
    ------
    RuntimeError
        if the environment cannot be created

    '''
    plan = package_plan()

    idx = conda.index

    specs = set()

    py_spec = None
    np_spec = None

    for spec_string in spec_strings:

        spec = package_spec(spec_string)

        if spec.name == 'python':
            if spec.version: py_spec = spec
            continue

        if spec.name == 'numpy':
            if spec.version: np_spec = spec
            continue

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

    # add constraints for default python and numpy specifications if needed
    constraints = [build_target(conda.target)]

    dep_names = [dep.name for dep in deps]

    if py_spec:
        constraints.append(_default_constraint(py_spec))
    elif 'python' in dep_names:
        constraints.append(_default_constraint(package_spec(DEFAULT_PYTHON_SPEC)))

    if np_spec:
        constraints.append(_default_constraint(np_spec))
    elif 'numpy' in dep_names:
        constraints.append(_default_constraint(package_spec(DEFAULT_NUMPY_SPEC)))

    env_constraints = all_of(*constraints)
    log.debug("computed environment constraints: %s\n" % env_constraints)

    # now we need to recompute the compatible packages using the computed environment constraints
    pkgs = idx.find_compatible_packages(specs)
    pkgs = idx.find_matches(env_constraints, pkgs)
    pkgs = newest_packages(pkgs)
    log.debug("updated packages: %s\n" % pkgs)

    # check to see if this is a meta-package situtaion (and handle it if so)
    all_pkgs = _handle_meta_create(conda, pkgs)

    if not all_pkgs:
        # find the associated dependencies
        deps = idx.get_deps(pkgs)
        deps = idx.find_matches(env_constraints, deps)
        deps = newest_packages(deps)
        log.debug("updated dependencies: %s\n" % deps)

        all_pkgs = newest_packages(pkgs | deps)
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

    Returns
    -------
    plan: :py:class:`package_plan <conda.package_plan.package_plan>`
        package plan for installing packages in an existing Anaconda environment

    Raises
    ------
    RuntimeError
        if the install cannot be performed

    '''
    plan = package_plan()

    idx = env.conda.index

    specs = set()

    py_spec = None
    np_spec = None

    for spec_string in spec_strings:

        spec = package_spec(spec_string)

        if spec.name == 'python':
            if env.find_activated_package('python'):
                raise RuntimeError('changing python versions in an existing Anaconda environment is not supported (create a new environment)')
            if spec.version: py_spec = spec
            continue
        if spec.name == 'numpy':
            if env.find_activated_package('numpy'):
                raise RuntimeError('changing numpy versions in an existing Anaconda environment is not supported (create a new environment)')
            if spec.version: np_spec = spec
            continue

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
    pkgs = idx.find_matches(env.requirements, pkgs)
    log.debug("initial packages: %s\n" % pkgs)

    # check to see if this is a meta-package situtaion (and handle it if so)
    log.info("%s" % pkgs)
    all_pkgs = _handle_meta_install(env.conda, pkgs)

    if not all_pkgs:
        # find the associated dependencies
        deps = idx.get_deps(pkgs)
        deps = idx.find_matches(env.requirements, deps)
        log.debug("initial dependencies: %s\n" % deps)

        # add default python and numpy requirements if needed
        constraints = [env.requirements]
        dep_names = [dep.name for dep in deps]

        if py_spec:
            constraints.append(_default_constraint(py_spec))
        elif 'python' in dep_names:
            constraints.append(_default_constraint(package_spec(DEFAULT_PYTHON_SPEC)))

        if np_spec:
            constraints.append(_default_constraint(np_spec))
        elif 'numpy' in dep_names:
            constraints.append(_default_constraint(package_spec(DEFAULT_NUMPY_SPEC)))

        env_constraints = all_of(*constraints)
        log.debug("computed environment constraints: %s\n" % env_constraints)

        # now we need to recompute the compatible packages using the updated package specifications
        pkgs = idx.find_compatible_packages(specs)
        pkgs = idx.find_matches(env_constraints, pkgs)
        pkgs = newest_packages(pkgs)
        log.debug("updated packages: %s\n" % pkgs)

        # find the associated dependencies
        deps = idx.get_deps(pkgs)
        deps = idx.find_matches(env_constraints, deps)
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


def create_update_plan(env, pkg_names):
    '''
    This function creates a package plan for updating specified packages to
    the latest version in the given Anaconda environment prefix. Only versions
    compatible with the existing environment are considered.

    Parameters
    ----------
    env : :py:class:`environment <conda.environment.environment>` object
        Anaconda environment to update packages in
    pkg_names : iterable of str
        package names of packages to update

    Returns
    -------
    plan: :py:class:`package_plan <conda.package_plan.package_plan>`
        package plan for updating packages in an existing Anaconda environment

    Raises
    ------
    RuntimeError
        if the update cannot be performed

    '''

    plan = package_plan()

    idx = env.conda.index

    pkgs = set()
    for pkg_name in pkg_names:
        pkg = env.find_activated_package(pkg_name)
        if not pkg:
            if pkg_name in env.conda.index.package_names:
                raise RuntimeError("package '%s' is not installed, cannot update (see conda install -h)" % pkg_name)
            else:
                raise RuntimeError("unknown package '%s', cannot update" % pkg_name)
        pkgs.add(pkg)

    # find any initial packages that have newer versions
    updates = set()
    for pkg in sort_packages_by_name(pkgs):
        candidates = idx.lookup_from_name(pkg.name)
        candidates = idx.find_matches(env.requirements, candidates)
        newest = max(candidates)
        log.debug("%s > %s == %s" % (newest.canonical_name, pkg.canonical_name, newest>pkg))
        if newest > pkg:
            updates.add(newest)
    log.debug('initial updates: %s' %  updates)

    if len(updates) == 0: return plan  # nothing to do

    all_pkgs = _handle_meta_update(env.conda, updates)

    if not all_pkgs:
        # get all the dependencies of the updates
        all_deps = idx.get_deps(updates)
        log.debug('update dependencies: %s' %  all_deps)

        # find newest packages compatible with these requirements and the build target
        all_pkgs = all_deps | updates
        all_pkgs = idx.find_matches(env.requirements, all_pkgs)
        all_pkgs = newest_packages(all_pkgs)

    # check for any inconsistent requirements the set of packages
    inconsistent = find_inconsistent_packages(all_pkgs)
    if inconsistent:
        raise RuntimeError('cannot update, the following packages are inconsistent: %s'
            % ', '.join('%s-%s' % (pkg.name, pkg.version.vstring) for pkg in inconsistent)
        )

    # download any activations that are not already availabls
    for pkg in all_pkgs:

        active = env.find_activated_package(pkg.name)
        if active and pkg > active:
            if pkg not in env.conda.available_packages:
                plan.downloads.add(pkg)
            plan.activations.add(pkg)
            plan.deactivations.add(active)

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

    Returns
    -------
    plan: :py:class:`package_plan <conda.package_plan.package_plan>`
        package plan for activating packages in an existing Anaconda environment

    Raises
    ------
    RuntimeError
        if the activations cannot be performed

    '''
    plan = package_plan()

    idx = env.conda.index

    for canonical_name in canonical_names:

        try:
            pkg = idx.lookup_from_canonical_name(canonical_name)
        except:
            raise RuntimeError("cannot activate unknown package '%s'" % canonical_name)

        if pkg in env.activated:
            raise RuntimeError("package '%s' is already activated in environment: %s" % (canonical_name, env.prefix))

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

    Returns
    -------
    plan: :py:class:`package_plan <conda.package_plan.package_plan>`
        package plan for de-activating packages in an existing Anaconda environment

    Raises
    ------
    RuntimeError
        if the deactivations cannot be performed

    '''
    plan = package_plan()

    idx = env.conda.index

    for canonical_name in canonical_names:

        try:
            pkg = idx.lookup_from_canonical_name(canonical_name)
        except:
            raise RuntimeError("cannot deactivate unknown package '%s'" % canonical_name)

        # if package is not already activated, there is nothing to do
        if pkg not in env.activated:
            raise RuntimeError("package '%s' is not activated in environment: %s" % (canonical_name, env.prefix))

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

    Returns
    -------
    plan: :py:class:`package_plan <conda.package_plan.package_plan>`
        package plan for downloading packages into :ref:`local availability <locally_available>`.

    Raises
    ------
    RuntimeError
        if the downloads cannot be performed

    '''
    plan = package_plan()

    idx = conda.index

    for canonical_name in canonical_names:

        try:
            pkg = idx.lookup_from_canonical_name(canonical_name)
        except:
            raise RuntimeError("cannot download unknown package '%s'" % canonical_name)

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





def _handle_meta_create(conda, pkgs):
    n_meta = sum(map(lambda pkg: pkg.is_meta, pkgs))

    if n_meta == 0:
        return set()

    if n_meta == 1 and len(pkgs) > 1:
        raise RuntimeError("create operation does not support mixing meta-packages and standard packages")

    if n_meta > 1:
        raise RuntimeError("create operation only supports one meta-package at a time")

    pkg = pkgs.pop()
    pkgs.add(pkg)

    for spec in pkg.requires:
        canonical_name = "%s-%s-%s" % (spec.name, spec.version.vstring, spec.build)
        pkgs.add(conda.index.lookup_from_canonical_name(canonical_name))

    return pkgs


def _handle_meta_install(conda, pkgs):
    n_meta = sum(map(lambda pkg: pkg.is_meta, pkgs))

    if n_meta == 0:
        return set()

    if n_meta == 1 and len(pkgs) > 1:
        raise RuntimeError("install operation does not support mixing meta-packages and standard packages")

    if n_meta > 1:
        raise RuntimeError("install operation only supports one meta-package at a time")

    pkg = pkgs.pop()
    pkgs.add(pkg)

    for spec in pkg.requires:
        canonical_name = "%s-%s-%s" % (spec.name, spec.version.vstring, spec.build)
        pkgs.add(conda.index.lookup_from_canonical_name(canonical_name))

    return pkgs


def _handle_meta_update(conda, pkgs):
    n_meta = sum(map(lambda pkg: pkg.is_meta, pkgs))

    if n_meta == 0:
        return set()

    if n_meta == 1 and len(pkgs) > 1:
        raise RuntimeError("update operation does not support mixing meta-packages and standard packages")

    if n_meta > 1:
        raise RuntimeError("update operation only supports one meta-package at a time")

    pkg = pkgs.pop()
    pkgs.add(pkg)

    for spec in pkg.requires:
        canonical_name = "%s-%s-%s" % (spec.name, spec.version.vstring, spec.build)
        pkgs.add(conda.index.lookup_from_canonical_name(canonical_name))

    return pkgs


def _default_constraint(spec):
    req = package_spec('%s %s.%s' % (spec.name,spec.version.version[0], spec.version.version[1]))
    sat = package_spec('%s %s %s' % (spec.name, spec.version.vstring, spec.build))
    return any_of(requires(req), satisfies(sat))


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
