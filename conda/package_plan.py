
from difflib import get_close_matches
from itertools import groupby
import logging


from config import DEFAULT_NUMPY_SPEC, DEFAULT_PYTHON_SPEC
from constraints import build_target, satisfies
from install import make_available, activate, deactivate
from package import sort_packages_by_name
from progressbar import Bar, ETA, FileTransferSpeed, Percentage, ProgressBar
from remote import fetch_file
from requirement import apply_default_requirement, requirement, find_inconsistent_requirements


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
        '''
        Return True if the package plan contains no operations to perform
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
                result += '\n        %s' % pkg
        return result


def create_create_plan(prefix, conda, spec_strings, use_defaults):
    '''
    This functions creates a package plan for activating packages in a new
    Anaconda environement, including all of their required dependencies. The
    desired packages are specified as constraints.
    '''
    plan = package_plan()

    idx = conda.index

    reqs = set()

    for spec_string in spec_strings:

        if spec_string == 'python':
            reqs.add(requirement(DEFAULT_PYTHON_SPEC))
            continue

        if spec_string == 'numpy':
            reqs.add(requirement(DEFAULT_NUMPY_SPEC))
            continue

        try:
            reqs.add(requirement(spec_string))
        except RuntimeError:
            candidates = conda.index.lookup_from_name(spec_string)
            if candidates:
                candidate = max(candidates)
                reqs.add(requirement("%s %s" % (candidate.name, candidate.version.vstring)))
            else:
                message = "unknown package name '%s'" % spec_string
                close = get_close_matches(spec_string, conda.index.package_names)
                if close:
                    message += '\n\nDid you mean one of these?\n'
                    for s in close:
                        message += '    %s' % s
                    message += "\n"
                raise RuntimeError(message)



    # abort if requirements are already incondsistent at this point
    inconsistent = find_inconsistent_requirements(reqs)
    if inconsistent:
        raise RuntimeError(
            'cannot create environment, the following requirements are inconsistent: %s' % str(inconsistent)
        )

    log.debug("initial requirements: %s\n" % reqs)

    # find packages compatible with the initial requirements and build target
    pkgs = idx.find_compatible_packages(reqs)
    pkgs = idx.find_matches(build_target(conda.target), pkgs)
    log.debug("initial compatible packages: %s\n" % pkgs)

    # find the associated dependencies
    all_reqs = idx.get_deps(pkgs) | reqs

    # add default python and numpy requirements if needed
    if use_defaults:
        for req in all_reqs:
            if req.name == 'python':
                apply_default_requirement(reqs, requirement(DEFAULT_PYTHON_SPEC))
            elif req.name == 'numpy':
                apply_default_requirement(reqs, requirement(DEFAULT_NUMPY_SPEC))

    # OK, so we need to re-do the compatible packages computation using
    # the updated requirements

    # find packages compatible with the updated requirements and build target
    pkgs = idx.find_compatible_packages(reqs)
    pkgs = idx.find_matches(build_target(conda.target), pkgs)
    pkgs = sort_packages_by_name(pkgs)
    pkgs = [max(g) for k, g in groupby(pkgs, key=lambda x: x.name)]
    log.debug("updated compatible packages: %s\n" % pkgs)

    # find the associated dependencies
    all_reqs = idx.get_deps(pkgs) | reqs
    log.debug("all requirements: %s\n" % all_reqs)

    # find packages compatible with the full requirements and build target
    all_pkgs = idx.find_compatible_packages(all_reqs)
    all_pkgs = idx.find_matches(build_target(conda.target), all_pkgs)
    log.debug("all compatible packages: %s\n" % all_pkgs)

    # handle multiple matches, keep only the latest version
    all_pkgs = sort_packages_by_name(all_pkgs)
    all_pkgs = [max(g) for k, g in groupby(all_pkgs, key=lambda x: x.name)]
    log.debug("final packages: %s\n" % all_pkgs)

    # check again for inconsistent requirements
    inconsistent = find_inconsistent_requirements(idx.get_deps(all_pkgs))
    if inconsistent:
        raise RuntimeError('cannot create environment, the following requirements are inconsistent: %s'
                                % ', '.join('%s-%s' % (req.name, req.version.vstring)
                                       for req in inconsistent))

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

    to_install = set()

    for arg in args:

        if arg.startswith('python-') or arg.startswith('python ') or arg.startswith('python='):
            raise RuntimeError('changing python versions in an existing Anaconda environment is not supported (create a new environment)')
        if arg.startswith('numpy') and env.find_activated_package('numpy'):
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
                if pkgs:
                    pkgs = idx.find_matches(env.requirements, pkgs)
                    if pkgs: pkgs = set([max(pkgs)])
                else:
                    message = "unknown package name '%s'" % arg
                    from difflib import get_close_matches
                    close = get_close_matches(arg, idx.package_names)
                    if close:
                        message += '\n\nDid you mean one of these?\n'
                        for s in close:
                            message += '    %s' % s
                        message += "\n"
                    raise RuntimeError(message)

        if len(pkgs) > 1:
            raise RuntimeError("found multiple package matches for '%s'" % arg)

        to_install.add(pkgs.pop())

    pkgs = to_install

    # find the associated dependencies
    reqs = idx.get_deps(pkgs)
    to_remove = set()
    for req in reqs:
        if env.requirement_is_satisfied(req):
            to_remove.add(req)
    reqs = reqs - to_remove

    # find packages compatible with the full requirements and build target
    all_pkgs = idx.find_compatible_packages(reqs) | to_install
    all_pkgs = idx.find_matches(env.requirements, all_pkgs)

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
            else: raise RuntimeError("package '%s' is already activated in environment: %s" % (pkg, env.prefix))

        if pkg not in env.activated:
            plan.activations.add(pkg)

    return plan


def create_upgrade_plan(env, pkgs):
    '''
    This function creates a package plan for upgrading specified packages to
    the latest version in the given Anaconda environment prefix. Only versions
    compatible with the existing environment are considered.
    '''
    plan = package_plan()

    idx = env.conda.index

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
    log.debug('upgrade requirements: %s' %  all_reqs)

    # find packages compatible with these requirements and the build target
    all_pkgs = idx.find_compatible_packages(all_reqs) | upgrades
    all_pkgs = idx.find_matches(build_target(env.conda.target), all_pkgs)

    # handle multiple matches, find the latest version
    all_pkgs = sort_packages_by_name(all_pkgs)
    all_pkgs = [max(g) for k,g in groupby(all_pkgs, key=lambda x: x.name)]
    log.debug('all packages: %s' %  all_pkgs)

    # check for any inconsistent requirements the set of packages
    inconsistent = find_inconsistent_requirements(idx.get_deps(all_pkgs))
    if inconsistent:
        raise RuntimeError('cannot upgrade packages, the following requirements are inconsistent: %s'
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


def create_activate_plan(env, canonical_names):
    '''
    This function creates a package plan for activating the specified packages
    in the given Anaconda environment prefix.
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
