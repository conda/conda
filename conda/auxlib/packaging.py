# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import
from distutils.command.build_py import build_py
from distutils.command.sdist import sdist
from logging import getLogger
from os.path import basename, dirname, join, isdir
from re import match
from subprocess import CalledProcessError, check_call, check_output

from .path import absdirname, PackageFile, ROOT_PATH

log = getLogger(__name__)


def _get_version_from_pkg_info(package_name):
    with PackageFile('.version', package_name) as fh:
        return fh.read()


def _is_git_dirty():
    try:
        check_call(('git', 'diff', '--quiet'))
        check_call(('git', 'diff', '--cached', '--quiet'))
        return False
    except CalledProcessError:
        return True


def _get_most_recent_git_tag():
    try:
        return check_output(["git", "describe", "--tags"]).strip()
    except CalledProcessError as e:
        if e.returncode == 128:
            return "0.0.0.0"
        else:
            raise  # pragma: no cover


def _get_git_hash():
    try:
        return check_output(["git", "rev-parse", "HEAD"]).strip()[:7]
    except CalledProcessError:
        return 0


def _get_version_from_git_tag():
    """Return a PEP440-compliant version derived from the git status.
    If that fails for any reason, return the first 7 chars of the changeset hash.
    """
    tag = _get_most_recent_git_tag()
    m = match(b"(?P<xyz>\d+\.\d+\.\d+)(?:-(?P<dev>\d+)-(?P<hash>.+))?", tag)
    version = m.group('xyz').decode('utf-8')
    if m.group('dev') or _is_git_dirty():
        dev = (m.group('dev') or 0).decode('utf-8')
        hash_ = (m.group('hash') or _get_git_hash()).decode('utf-8')
        version += ".dev{dev}+{hash_}".format(dev=dev, hash_=hash_)
    return version


def is_git_repo(path, package):
    if path == ROOT_PATH or dirname(basename(path)) == package:
        return False
    else:
        return isdir(join(path, '.git')) or is_git_repo(dirname(path), package)


def get_version(file, package):
    """Returns a version string for the current package, derived
    either from git or from a .version file.

    This function is expected to run in two contexts. In a development
    context, where .git/ exists, the version is pulled from git tags.
    Using the BuildPyCommand and SDistCommand classes for cmdclass in
    setup.py will write a .version file into any dist.

    In an installed context, the .version file written at dist build
    time is the source of version information.

    """
    here = absdirname(file)
    if is_git_repo(here, package):
        return _get_version_from_git_tag()

    # fall back to .version file
    version_from_pkg = _get_version_from_pkg_info(package)
    if version_from_pkg:
        return version_from_pkg.decode('utf-8')

    raise RuntimeError("Could not get package version (no .git or .version file)")


class BuildPyCommand(build_py):
    def run(self):
        build_py.run(self)
        # locate .version in the new build/ directory and replace it with an updated value
        target_version_file = join(self.build_lib, self.distribution.metadata.name, ".version")
        print("UPDATING {0}".format(target_version_file))
        with open(target_version_file, 'w') as f:
            f.write(self.distribution.metadata.version)


class SDistCommand(sdist):
    def run(self):
        return sdist.run(self)

    def make_release_tree(self, base_dir, files):
        sdist.make_release_tree(self, base_dir, files)
        target_version_file = join(base_dir, self.distribution.metadata.name, ".version")
        print("UPDATING {0}".format(target_version_file))
        with open(target_version_file, 'w') as f:
            f.write(self.distribution.metadata.version)
