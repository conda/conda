import logging
import sys
from itertools import groupby

if sys.platform == 'win32':
    from win_install import activate, deactivate
else:
    from install import activate, deactivate, extract

from remote import fetch_file
from package import sort_packages_by_name
from requirement import (apply_default_requirement, requirement,
                         find_inconsistent_requirements)
from constraints import build_target, satisfies
from progressbar import Bar, ETA, FileTransferSpeed, Percentage, ProgressBar


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

    def execute(self, env, no_progress_bar=False):
        '''
        Perform the operations contained in the package plan
        '''
        for pkg in self.downloads:
            if no_progress_bar:
                progress = None
            else:
                widgets = [' ', Percentage(), ' ', Bar(), ' ', ETA(),
                           ' ', FileTransferSpeed()]
                progress = ProgressBar(widgets=widgets)
            fetch_file(pkg.filename, progress=progress)
            if sys.platform != 'win32':
                extract(pkg, env)
        for pkg in self.deactivations:
            deactivate(pkg, env)
        for pkg in self.activations:
            activate(pkg, env)

    def empty(self):
        '''
        Return True if the package plan contains no operations to perform
        '''
        return not (self.downloads or self.activations or self.deactivations)

    def __str__(self):
        result = ''
        if self.downloads:
            result += download_string % self._format_packages(self.downloads, lookup_repo=True)
        if self.activations:
            result += activate_string % self._format_packages(self.activations)
        if self.deactivations:
            result += deactivate_string % self._format_packages(self.deactivations)
        if self.broken:
            result += broken_string % self._format_packages(self.broken)
        if self.missing:
            result += missing_string % self._format_packages(self.missing)
        return result

    def _format_packages(self, pkgs, lookup_repo=False):
        result = ''
        if lookup_repo:
            for pkg in sort_packages_by_name(pkgs):
                result += '\n        %s' % pkg.filename
        else:
            for pkg in sort_packages_by_name(pkgs):
                result += '\n        %s' % pkg
        return result


def create_create_plan(prefix, conda, reqs, no_defaults):
    '''
    This functions creates a package plan for activating packages in a new
    Anaconda environement, including all of their required dependencies. The
    desired packages are specified as constraints.
    '''
    plan = package_plan()

    idx = conda.index

    reqs = set(reqs)

    # abort if requirements are already incondsistent at this point
    inconsistent = find_inconsistent_requirements(reqs)
    if inconsistent:
        raise RuntimeError(
            'cannot create environment, the following requirements are inconsistent: %s' % str(inconsistent)
        )

    log.debug("initial requirements: %s" % reqs)

    # find packages compatible with the initial requirements and build target
    pkgs = idx.find_compatible_packages(reqs)
    pkgs = idx.find_matches(build_target(conda.target), pkgs)
    log.debug("initial compatible packages: %s" % pkgs)

    # find the associated dependencies
    all_reqs = idx.get_deps(pkgs) | reqs

    # add default python and numpy requirements if needed
    if not no_defaults:
        for req in all_reqs:
            if req.name == 'python':
                apply_default_requirement(reqs, requirement('python 2.7'))
            elif req.name == 'numpy':
                apply_default_requirement(reqs, requirement('numpy 1.7'))

    # OK, so we need to re-do the compatible packages computation using
    # the updated requirements

    # find packages compatible with the updated requirements and build target
    pkgs = idx.find_compatible_packages(reqs)
    pkgs = idx.find_matches(build_target(conda.target), pkgs)
    log.debug("updated compatible packages: %s" % pkgs)

    # find the associated dependencies
    all_reqs = idx.get_deps(pkgs) | reqs
    log.debug("all requirements: %s" % all_reqs)

    # find packages compatible with the full requirements and build target
    all_pkgs = idx.find_compatible_packages(all_reqs)
    all_pkgs = idx.find_matches(build_target(conda.target), all_pkgs)
    log.debug("all compatible packages: %s" % all_pkgs)

    # handle multiple matches, keep only the latest version
    all_pkgs = sort_packages_by_name(all_pkgs)
    all_pkgs = [max(g) for k,g in groupby(all_pkgs, key=lambda x: x.name)]
    log.debug("final packages: %s" % all_pkgs)

    # check again for inconsistent requirements
    inconsistent = find_inconsistent_requirements(idx.get_deps(all_pkgs))
    if inconsistent:
        raise RuntimeError('cannot create environment, the following requirements are inconsistent: %s'
            % ', '.join('%s-%s' % (req.name, req.version.vstring) for req in inconsistent)
        )

    # download any packages that are not available
    for pkg in all_pkgs:
        if pkg not in conda.available_packages:
            plan.downloads.add(pkg)

    plan.activations = all_pkgs

    return plan


def create_install_plan(env, args):
    '''
    This functions creates a package plan for activating packages in an
    existing Anaconda environement, including removing existing verions and
    also activating all required dependencies. The desired packages are
    specified as package names, package filenames, or requirements strings.
    '''
    plan = package_plan()

    idx = env.conda.index

    to_install= set()

    for arg in args:

        if arg.startswith('python-') or arg.startswith('python ') or arg.startswith('python='):
            raise RuntimeError('changing python versions in an existing Anaconda environment is not supported (create a new environment)')
        if arg.startswith('numpy'):
            raise RuntimeError('changing numpy versions in an existing Anaconda environment is not supported (create a new environment)')

        # attempt to parse as filename
        if arg.endswith('.tar.bz2'):
            try:
                pkg = idx.lookup_from_filename(arg)
                if not pkg.matches(env.requirements):
                    raise RuntimeError("package '%s' does not satisfy requirements for environment at: %s, which are: %s" % (arg, env.prefix, env.requirements))
                pkgs = set([pkg])
            except KeyError:
                pkgs = set()

        else:
            # attempt to parse as requirement string
            try:
                req = requirement(arg)
                pkgs = idx.find_matches(satisfies(req))
                pkgs = idx.find_matches(env.requirements, pkgs)

            # attempt to parse as package name
            except RuntimeError:
                pkgs = idx.lookup_from_name(arg)
                pkgs = idx.find_matches(env.requirements, pkgs)
                pkgs = set([max(pkgs)])

        if len(pkgs) == 0:
            raise RuntimeError("could not find package match for '%s'" % arg)
        elif len(pkgs) > 1:
            raise RuntimeError("found multiple package matches for '%s'" % arg)

        to_install.add(pkgs.pop())

    pkgs = to_install

    # find the associated dependencies
    reqs = idx.get_deps(pkgs)

    # find packages compatible with the full requirements and build target
    all_pkgs = idx.find_compatible_packages(reqs) | to_install
    all_pkgs = idx.find_matches(build_target(env.conda.target), all_pkgs)

    # download any packages that are not available
    for pkg in all_pkgs:

        # download any currently unavailable packages
        if pkg not in env.conda.available_packages:
            plan.downloads.add(pkg)

        # see if the package is already active
        active = env.find_activated_package(pkg.name)
        if active:
            if pkg != active:
                plan.deactivations.add(active)

        if pkg not in env.activated:
            plan.activations.add(pkg)

    return plan


def create_activate_plan(env, pkg_names, follow_deps=False):
    '''
    This function creates a package plan for activating the specified packages
    in the given Anaconda environment prefix. By default, dependent packages are
    not inlcuded, but may be ignored by setting the follow_deps argument
    '''
    plan = package_plan()

    idx = env.conda.index

    for pkg_name in pkg_names:

        # if package is already activated, there is nothing to do
        pkg = env.find_activated_package(pkg_name)
        if pkg: continue  # TODO warn?

        # find packages that match name and build target
        pkgs = idx.find_matches(
            build_target(env.conda.target),
            idx.lookup_from_name(pkg_name)
        )

        # pick the newest version if there are multiple matches
        if len(pkgs) == 0: continue
        if len(pkgs) == 1: pkg = pkgs.pop()
        else: pkg = max(pkgs)

        plan.activations.add(pkg)

        # add or warn about missing dependencies
        deps = idx.find_compatible_packages(idx.get_deps(pkgs))
        deps = idx.find_matches(env.requirements, deps)
        for dep in deps:
            if dep not in env.activated:
                if follow_deps:
                    plan.activations.add(dep)
                else:
                    plan.missing.add(dep)

    return plan


def create_deactivate_plan(env, pkg_names, follow_deps=False):
    '''
    This function creates a package plan for deactivating the specified packages
    in the given Anaconda environment prefix. By default, dependent packages are
    not inlcuded, but may be by setting the follow_deps argument
    '''
    plan = package_plan()

    idx = env.conda.index

    for pkg_name in pkg_names:

        # if package is not already activated, there is nothing to do
        pkg = env.find_activated_package(pkg_name)
        if not pkg: continue  # TODO warn?

        plan.deactivations.add(pkg)

    # find a requirement for this package that we can use to lookup reverse deps
    reqs = idx.find_compatible_requirements(plan.deactivations)

    # add or warn about broken reverse dependencies
    for rdep in idx.get_reverse_deps(reqs):
        if rdep in env.activated:
            if follow_deps:
                plan.deactivations.add(rdep)
            else:
                plan.broken.add(rdep)

    return plan


def create_upgrade_plan(env, pkgs):
    '''
    This function creates a package plan for upgrading specified packages to the latest
    version in the given Anaconda environment prefix. Only versions compatible with the
    existing environment are considered.
    '''
    plan = package_plan()

    idx = env.conda.index

    # find any packages that have newer versions
    upgrades = set()
    to_remove = set()
    for pkg in pkgs:
        newest = max(idx.lookup_from_name(pkg.name))
        log.debug("%s > %s == %s" % (newest, pkg, newest>pkg))
        if newest > pkg:
            upgrades.add(newest)
            to_remove.add(pkg)

    upgrades = idx.find_matches(env.requirements, upgrades)

    if len(upgrades) == 0: return plan  # nothing to do

    # get all the dependencies of the upgrades
    all_reqs = idx.get_deps(upgrades)

    # find packages compatible with these requirements and the build target
    all_pkgs = idx.find_compatible_packages(all_reqs) | upgrades
    all_pkgs = idx.find_matches(build_target(env.conda.target), all_pkgs)

    # handle multiple matches, find the latest version
    all_pkgs = sort_packages_by_name(all_pkgs)
    all_pkgs = [max(g) for k,g in groupby(all_pkgs, key=lambda x: x.name)]

    # check for any inconsistent requirements the set of packages
    inconsistent = find_inconsistent_requirements(idx.get_deps(all_pkgs))
    if inconsistent:
        raise RuntimeError('cannot upgrade pacakges, the following requirements are inconsistent: %s'
            % ', '.join('%s-%s' % (req.name, req.version.vstring) for req in inconsistent)
        )

    # deactivate original packages and activate new versions
    plan.deactivations = to_remove

    # download any activations that are not already availabls
    for pkg in all_pkgs:
        if pkg not in env.conda.available_packages:
            plan.downloads.add(pkg)
        if pkg not in env.activated:
            plan.activations.add(pkg)

    return plan


def create_download_plan(env, pkg_names, no_deps, force):
    '''
    This function creates a package plan for downloading the specified packages
    and their dependencies from remote Anaconda package repositories. By default,
    packages already available are ignored, but this can be overriden with the
    force argument.
    '''
    plan = package_plan()

    idx = env.conda.index

    for pkg_name in pkg_names:

        # lookup by explicit filename supported mainly for testing
        if pkg_name.endswith('.tar.bz2'):
            candidates = [idx.lookup_from_filename(pkg_name)]

        # find packages that match name and build target, etc
        else:
            candidates = idx.lookup_from_name(pkg_name)
            candidates = idx.find_matches(env.requirements, candidates)

        # bail if one of the names fails to produce a match
        if len(candidates) == 0:
            raise RuntimeError(
                "download of '%s' failed, no match found" % pkg_name
            )

        # add to downloads if not already available, or user requests force
        for candidate in candidates:
            if force or candidate not in env.conda.available_packages:
                plan.downloads.add(candidate)

        # download dependencies too, if requested
        if not no_deps:
            pkgs = idx.find_compatible_packages(idx.get_deps(candidates))
            pkgs = idx.find_matches(env.requirements, pkgs)

            for pkg in pkgs:
                if force or pkg not in env.conda.available_packages:
                    plan.downloads.add(pkg)

    return plan


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
