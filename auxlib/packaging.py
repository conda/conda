# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import

import sys
from collections import namedtuple
from logging import getLogger
from os import getenv, remove
from os.path import abspath, dirname, expanduser, isdir, isfile, join
from re import compile
from shlex import split
from subprocess import CalledProcessError, Popen, PIPE
try:
    from setuptools.command.build_py import build_py
    from setuptools.command.sdist import sdist
    from setuptools.command.test import test as TestCommand
except ImportError:
    from distutils.command.build_py import build_py
    from distutils.command.sdist import sdist
    TestCommand = object


log = getLogger(__name__)

Response = namedtuple('Response', ['stdout', 'stderr', 'rc'])


def call(path, command, raise_on_error=True):
    p = Popen(split(command), cwd=path, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    rc = p.returncode
    log.debug("{0} $  {1}\n"
              "  stdout: {2}\n"
              "  stderr: {3}\n"
              "  rc: {4}"
              .format(path, command, stdout, stderr, rc))
    if raise_on_error and rc != 0:
        raise CalledProcessError(rc, command, "stdout: {0}\nstderr: {1}".format(stdout, stderr))
    return Response(stdout, stderr, rc)


def _get_version_from_version_file(path):
    file_path = join(path, '.version')
    if isfile(file_path):
        with open(file_path, 'r') as fh:
            return fh.read().strip()


def _git_describe_tags(path):
    call(path, "git update-index --refresh", raise_on_error=False)
    response = call(path, "git describe --tags --long", raise_on_error=False)
    if response.rc == 0:
        return response.stdout.strip()
    elif response.rc == 128 and "no names found" in response.stderr.lower():
        return None
    elif response.rc == 127:
        log.error("git not found on path: PATH={0}".format(getenv('PATH', None)))
        raise CalledProcessError(response.rc, response.stderr)
    else:
        raise CalledProcessError(response.rc, response.stderr)


DESCRIBE_REGEX = compile(r"(?:[_-a-zA-Z]*)"
                         r"(?P<version>\d+\.\d+\.\d+)"
                         r"(?:-(?P<dev>\d+)-g(?P<hash>[0-9a-f]{7}))$")
def _get_version_from_git_tag(path):
    """Return a PEP440-compliant version derived from the git status.
    If that fails for any reason, return the first 7 chars of the changeset hash.
    """
    m = DESCRIBE_REGEX.match(_git_describe_tags(path).decode('utf-8') or '')
    if m is None:
        return None
    version, post_commit, hash = m.groups()
    return version if post_commit == '0' else "{0}.dev{1}+{2}".format(version, post_commit, hash)


def get_version(dunder_file):
    """Returns a version string for the current package, derived
    either from git or from a .version file.

    This function is expected to run in two contexts. In a development
    context, where .git/ exists, the version is pulled from git tags.
    Using the BuildPyCommand and SDistCommand classes for cmdclass in
    setup.py will write a .version file into any dist.

    In an installed context, the .version file written at dist build
    time is the source of version information.

    """
    path = abspath(expanduser(dirname(dunder_file)))
    return _get_version_from_version_file(path) or _get_version_from_git_tag(path)


def write_version_into_init(target_dir, version):
    target_init_file = join(target_dir, "__init__.py")
    assert isfile(target_init_file), "File not found: {0}".format(target_init_file)
    with open(target_init_file, 'r') as f:
        init_lines = f.readlines()
    for q in range(len(init_lines)):
        if init_lines[q].startswith('__version__'):
            init_lines[q] = '__version__ = "{0}"\n'.format(version)
        elif init_lines[q].startswith(('from auxlib', 'import auxlib')):
            init_lines[q] = None
    print("UPDATING {0}".format(target_init_file))
    remove(target_init_file)
    with open(target_init_file, 'w') as f:
        f.write(''.join(l for l in init_lines if l is not None))


def write_version_file(target_dir, version):
    assert isdir(target_dir), "Directory not found: {0}".format(target_dir)
    target_file = join(target_dir, ".version")
    with open(target_file, 'w') as f:
        f.write(version)


class BuildPyCommand(build_py):
    def run(self):
        build_py.run(self)
        target_dir = join(self.build_lib, self.distribution.metadata.name)
        write_version_into_init(target_dir, self.distribution.metadata.version)
        write_version_file(target_dir, self.distribution.metadata.version)


class SDistCommand(sdist):
    def make_release_tree(self, base_dir, files):
        sdist.make_release_tree(self, base_dir, files)
        target_dir = join(base_dir, self.distribution.metadata.name)
        write_version_into_init(target_dir, self.distribution.metadata.version)
        write_version_file(target_dir, self.distribution.metadata.version)


class Tox(TestCommand):
    user_options = [('tox-args=', 'a', "Arguments to pass to tox")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.tox_args = None

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import tox
        import shlex
        args = self.tox_args
        if args:
            args = shlex.split(self.tox_args)
        else:
            args = ''
        errno = tox.cmdline(args=args)
        sys.exit(errno)
