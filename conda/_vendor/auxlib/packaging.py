# -*- coding: utf-8 -*-
"""
=====
Usage
=====

Method #1: auxlib.packaging as a run time dependency
---------------------------------------------------

Place the following lines in your package's main __init__.py

from auxlib import get_version
__version__ = get_version(__file__)



Method #2: auxlib.packaging as a build time-only dependency
----------------------------------------------------------


import auxlib

# When executing the setup.py, we need to be able to import ourselves, this
# means that we need to add the src directory to the sys.path.
here = os.path.abspath(os.path.dirname(__file__))
src_dir = os.path.join(here, "auxlib")
sys.path.insert(0, src_dir)

setup(
    version=auxlib.__version__,
    cmdclass={
        'build_py': auxlib.BuildPyCommand,
        'sdist': auxlib.SDistCommand,
        'test': auxlib.Tox,
    },
)



Place the following lines in your package's main __init__.py

from auxlib import get_version
__version__ = get_version(__file__)


Method #3: write .version file
------------------------------



Configuring `python setup.py test` for Tox
------------------------------------------

must use setuptools (distutils doesn't have a test cmd)

setup(
    version=auxlib.__version__,
    cmdclass={
        'build_py': auxlib.BuildPyCommand,
        'sdist': auxlib.SDistCommand,
        'test': auxlib.Tox,
    },
)


"""
from __future__ import print_function, division, absolute_import

import sys
from re import sub
from collections import namedtuple
from logging import getLogger
from os import getenv, remove, listdir, name as osname, stat, chmod
from os.path import abspath, basename, dirname, expanduser, isdir, isfile, join
from re import compile
from shlex import split
from subprocess import CalledProcessError, Popen, PIPE
from fnmatch import fnmatchcase
from distutils.util import convert_path
from stat import ST_MODE
import io

is_develop = 'develop' in sys.argv
if is_develop:
    from setuptools.command.build_py import build_py
    from setuptools.command.sdist import sdist
    from setuptools.command.develop import develop
    from setuptools.command.test import test as TestCommand
else:
    from distutils.command.build_py import build_py
    from distutils.command.sdist import sdist
    from distutils.command.install_scripts import install_scripts
    TestCommand = object

log = getLogger(__name__)

Response = namedtuple('Response', ['stdout', 'stderr', 'rc'])
GIT_DESCRIBE_REGEX = compile(r"(?:[_-a-zA-Z]*)"
                             r"(?P<version>\d+\.\d+\.\d+)"
                             r"(?:-(?P<dev>\d+)-g(?P<hash>[0-9a-f]{7}))$")


def call(command, path=None, raise_on_error=True):
    path = sys.prefix if path is None else abspath(path)
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
    return Response(stdout.decode('utf-8'), stderr.decode('utf-8'), int(rc))


def _get_version_from_version_file(path):
    file_path = join(path, '.version')
    if isfile(file_path):
        with open(file_path, 'r') as fh:
            return fh.read().strip()


def _git_describe_tags(path):
    try:
        call("git update-index --refresh", path, raise_on_error=False)
    except CalledProcessError as e:
        # git is probably not installed
        log.warn(repr(e))
        return None
    response = call("git describe --tags --long", path, raise_on_error=False)
    if response.rc == 0:
        return response.stdout.strip()
    elif response.rc == 128 and "no names found" in response.stderr.lower():
        # directory is a git repo, but no tags found
        return None
    elif response.rc == 128 and "not a git repository" in response.stderr.lower():
        return None
    elif response.rc == 127:
        log.error("git not found on path: PATH={0}".format(getenv('PATH', None)))
        raise CalledProcessError(response.rc, response.stderr)
    else:
        raise CalledProcessError(response.rc, response.stderr)


def _get_version_from_git_tag(path):
    """Return a PEP440-compliant version derived from the git status.
    If that fails for any reason, return the first 7 chars of the changeset hash.
    """
    m = GIT_DESCRIBE_REGEX.match(_git_describe_tags(path) or '')
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
    try:
        return _get_version_from_version_file(path) or _get_version_from_git_tag(path)
    except CalledProcessError as e:
        log.warn(repr(e))
        return None
    except Exception as e:
        log.exception(e)
        return None


def write_version_into_init(target_dir, version):
    target_init_file = join(target_dir, "__init__.py")
    assert isfile(target_init_file), "File not found: {0}".format(target_init_file)
    with open(target_init_file, 'r') as f:
        init_lines = f.readlines()
    for q in range(len(init_lines)):
        if init_lines[q].startswith('__version__'):
            init_lines[q] = '__version__ = "{0}"\n'.format(version)
        elif (init_lines[q].startswith(('from auxlib', 'import auxlib'))
              or 'auxlib.packaging' in init_lines[q]):
            init_lines[q] = None
    print("UPDATING {0}".format(target_init_file))
    remove(target_init_file)
    with open(target_init_file, 'w') as f:
        f.write(''.join(l for l in init_lines if l is not None))


def write_version_file(target_dir, version):
    assert isdir(target_dir), "Directory not found: {0}".format(target_dir)
    target_file = join(target_dir, ".version")
    print("WRITING {0} with version {1}".format(target_file, version))
    with open(target_file, 'w') as f:
        f.write(version)


def process_conda_install_scripts(install_dir, files):
    # files have been copied into new location
    # check the new files for prefix
    for file in files:
        # read text
        with open(file, 'r') as f:
            text = f.read()

        # POSIX replacement
        text = sub(r"\${CONDA_INSTALL_PREFIX}", install_dir, text)
        # Windows CMD.exe replacement
        text = sub(r"%CONDA_INSTALL_PREFIX%", install_dir, text)

        # write new text
        with open(file, 'w') as f:
            f.write(text)


if is_develop:
    class DevelopCommand(develop):
        def install_egg_scripts(self, dist):
            """
            Override develop's install_egg_scripts.

            Cannot simply super the parent function since we need to track
            the scripts installed (see the outputs list).
            """
            if dist is not self.dist:
                # Installing a dependency, so fall back to normal behavior
                return easy_install.install_egg_scripts(self, dist)

            # create wrapper scripts in the script dir, pointing to dist.scripts

            # new-style...
            self.install_wrapper_scripts(dist)

            # ...and old-style
            outputs = []
            for script_name in self.distribution.scripts or []:
                script_path = abspath(convert_path(script_name))
                script_name = basename(script_path)
                with io.open(script_path) as strm:
                    script_text = strm.read()
                self.install_script(dist, script_name, script_text, script_path)
                outputs += [script_name]

            outputs = map(lambda f: join(self.script_dir,f), outputs)
            process_conda_install_scripts(self.script_dir, outputs)
else:
    class InstallScriptsCommand(install_scripts):
        def run(self):
            """
            Extend install_scripts's run.
            """
            install_scripts.run(self)

            process_conda_install_scripts(self.install_dir, self.get_outputs())


class BuildPyCommand(build_py):
    def run(self):
        build_py.run(self)
        target_dir = join(self.build_lib, self.distribution.metadata.name)
        write_version_into_init(target_dir, self.distribution.metadata.version)
        write_version_file(target_dir, self.distribution.metadata.version)
        # TODO: separate out .version file implementation


class SDistCommand(sdist):
    def make_release_tree(self, base_dir, files):
        sdist.make_release_tree(self, base_dir, files)
        target_dir = join(base_dir, self.distribution.metadata.name)
        write_version_into_init(target_dir, self.distribution.metadata.version)
        write_version_file(target_dir, self.distribution.metadata.version)


class Tox(TestCommand):
    # TODO: Make this class inherit from distutils instead of setuptools
    user_options = [('tox-args=', 'a', "Arguments to pass to tox")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.tox_args = None

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, because outside the eggs aren't loaded
        from tox import cmdline
        from shlex import split
        args = self.tox_args
        if args:
            args = split(self.tox_args)
        else:
            args = ''
        errno = cmdline(args=args)
        sys.exit(errno)


# swiped from setuptools
def find_packages(where='.', exclude=()):
    out = []
    stack = [(convert_path(where), '')]
    while stack:
        where, prefix = stack.pop(0)
        for name in listdir(where):
            fn = join(where, name)
            if ('.' not in name and isdir(fn) and
                    isfile(join(fn, '__init__.py'))
                ):
                out.append(prefix + name)
                stack.append((fn, prefix + name + '.'))
    for pat in list(exclude) + ['ez_setup', 'distribute_setup']:
        out = [item for item in out if not fnmatchcase(item, pat)]
    return out
