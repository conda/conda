# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import bz2
from contextlib import contextmanager
from glob import glob
import json
from json import loads as json_loads
from logging import DEBUG, getLogger
import os
from os.path import basename, exists, isdir, isfile, join, relpath, dirname
from random import sample
from shlex import split
from shutil import copyfile, rmtree
from subprocess import check_call
import sys
from tempfile import gettempdir
from unittest import TestCase
from uuid import uuid4

import shutil

from datetime import datetime

import conda
from conda._vendor.auxlib.ish import dals
from conda.gateways.anaconda_client import read_binstar_tokens
import pytest
import requests

from conda import CondaError, CondaMultiError, plan, __version__ as CONDA_VERSION
from conda._vendor.auxlib.entity import EntityEncoder
from conda.base.context import context, reset_context
from conda.cli.common import get_index_trap
from conda.cli.main import generate_parser, init_loggers
from conda.cli.main_clean import configure_parser as clean_configure_parser
from conda.cli.main_config import configure_parser as config_configure_parser
from conda.cli.main_create import configure_parser as create_configure_parser
from conda.cli.main_info import configure_parser as info_configure_parser
from conda.cli.main_install import configure_parser as install_configure_parser
from conda.cli.main_list import configure_parser as list_configure_parser
from conda.cli.main_remove import configure_parser as remove_configure_parser
from conda.cli.main_search import configure_parser as search_configure_parser
from conda.cli.main_update import configure_parser as update_configure_parser
from conda.common.compat import itervalues, text_type, PY2
from conda.common.io import captured, disable_logger, replace_log_streams, stderr_log_level, \
    env_var
from conda.common.path import get_bin_directory_short_path, get_python_site_packages_short_path, pyc_path
from conda.common.url import path_to_url
from conda.common.yaml import yaml_load
from conda.core.repodata import create_cache_dir
from conda.core.linked_data import get_python_version_for_prefix, \
    linked as install_linked, linked_data, linked_data_
from conda.core.package_cache import PackageCache
from conda.exceptions import CondaHTTPError, DryRunExit, RemoveError, conda_exception_handler, \
    PackageNotFoundError
from conda.gateways.disk.create import mkdir_p
from conda.gateways.disk.delete import rm_rf
from conda.gateways.disk.update import touch
from conda.gateways.logging import TRACE
from conda.gateways.subprocess import subprocess_call
from conda.models.index_record import IndexRecord
from conda.utils import on_win

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch


log = getLogger(__name__)
TRACE, DEBUG = TRACE, DEBUG  # these are so the imports aren't cleared, but it's easy to switch back and forth
TEST_LOG_LEVEL = DEBUG
PYTHON_BINARY = 'python.exe' if on_win else 'bin/python'
BIN_DIRECTORY = 'Scripts' if on_win else 'bin'
UINCODE_CHARACTERS = u"ōγђ家固한"
UINCODE_CHARACTERS = u"áêñßôç"


def escape_for_winpath(p):
    return p.replace('\\', '\\\\')


def make_temp_prefix(name=None, create_directory=True):
    tempdir = gettempdir()
    if PY2:
        dirpath = str(uuid4())[:8] if name is None else name
    else:
        random_unicode = ''.join(sample(UINCODE_CHARACTERS, len(UINCODE_CHARACTERS)))
        dirpath = (str(uuid4())[:4] + ' ' + random_unicode) if name is None else name
    prefix = join(tempdir, dirpath)
    os.makedirs(prefix)
    if create_directory:
        assert isdir(prefix)
    else:
        os.removedirs(prefix)
    return prefix


class Commands:
    CONFIG = "config"
    CLEAN = "clean"
    CREATE = "create"
    INFO = "info"
    INSTALL = "install"
    LIST = "list"
    REMOVE = "remove"
    SEARCH = "search"
    UPDATE = "update"


parser_config = {
    Commands.CONFIG: config_configure_parser,
    Commands.CLEAN: clean_configure_parser,
    Commands.CREATE: create_configure_parser,
    Commands.INFO: info_configure_parser,
    Commands.INSTALL: install_configure_parser,
    Commands.LIST: list_configure_parser,
    Commands.REMOVE: remove_configure_parser,
    Commands.SEARCH: search_configure_parser,
    Commands.UPDATE: update_configure_parser,
}


def run_command(command, prefix, *arguments, **kwargs):
    use_exception_handler = kwargs.get('use_exception_handler', False)
    arguments = list(arguments)
    p, sub_parsers = generate_parser()
    parser_config[command](sub_parsers)

    if command is Commands.CONFIG:
        arguments.append('--file "{0}"'.format(join(prefix, 'condarc')))
    if command in (Commands.LIST, Commands.CREATE, Commands.INSTALL,
                   Commands.REMOVE, Commands.UPDATE):
        arguments.append('-p "{0}"'.format(prefix))
    if command in (Commands.CREATE, Commands.INSTALL, Commands.REMOVE, Commands.UPDATE):
        arguments.extend(["-y", "-q"])

    arguments = list(map(escape_for_winpath, arguments))
    command_line = "{0} {1}".format(command, " ".join(arguments))

    args = p.parse_args(split(command_line))
    context._set_argparse_args(args)
    init_loggers(context)
    print("\n\nEXECUTING COMMAND >>> $ conda %s\n\n" % command_line, file=sys.stderr)
    with stderr_log_level(TEST_LOG_LEVEL, 'conda'), stderr_log_level(TEST_LOG_LEVEL, 'requests'):
        with captured() as c, replace_log_streams():
            if use_exception_handler:
                conda_exception_handler(args.func, args, p)
            else:
                args.func(args, p)
    print(c.stderr, file=sys.stderr)
    print(c.stdout, file=sys.stderr)
    if command is Commands.CONFIG:
        reload_config(prefix)
    return c.stdout, c.stderr


@contextmanager
def make_temp_env(*packages, **kwargs):
    name = kwargs.pop('name', None)
    prefix = kwargs.pop('prefix', None) or make_temp_prefix(name)
    assert isdir(prefix), prefix
    with disable_logger('fetch'), disable_logger('dotupdate'):
        try:
            # try to clear any config that's been set by other tests
            reset_context([os.path.join(prefix+os.sep, 'condarc')])
            run_command(Commands.CREATE, prefix, *packages)
            yield prefix
        finally:
            rmtree(prefix, ignore_errors=True)

@contextmanager
def make_temp_channel(packages):
    package_reqs = [pkg.replace('-', '=') for pkg in packages]
    package_names = [pkg.split('-')[0] for pkg in packages]

    with make_temp_env(*package_reqs) as prefix:
        for package in packages:
            assert_package_is_installed(prefix, package)
        data = [p for p in itervalues(linked_data(prefix)) if p['name'] in package_names]
        run_command(Commands.REMOVE, prefix, *package_names)
        for package in packages:
            assert not package_is_installed(prefix, package)
        assert_package_is_installed(prefix, 'python')

    repodata = {'info': {}, 'packages': {}}
    tarfiles = {}
    for package_data in data:
        pkg_data = package_data
        fname = pkg_data['fn']
        tarfiles[fname] = join(PackageCache.first_writable().pkgs_dir, fname)

        pkg_data = pkg_data.dump()
        for field in ('url', 'channel', 'schannel'):
            del pkg_data[field]
        repodata['packages'][fname] = IndexRecord(**pkg_data)

    with make_temp_env() as channel:
        subchan = join(channel, context.subdir)
        noarch_dir = join(channel, 'noarch')
        channel = path_to_url(channel)
        os.makedirs(subchan)
        os.makedirs(noarch_dir)
        for fname, tar_old_path in tarfiles.items():
            tar_new_path = join(subchan, fname)
            copyfile(tar_old_path, tar_new_path)

        with bz2.BZ2File(join(subchan, 'repodata.json.bz2'), 'w') as f:
            f.write(json.dumps(repodata, cls=EntityEncoder).encode('utf-8'))
        with bz2.BZ2File(join(noarch_dir, 'repodata.json.bz2'), 'w') as f:
            f.write(json.dumps({}, cls=EntityEncoder).encode('utf-8'))

        yield channel


def reload_config(prefix):
    prefix_condarc = join(prefix+os.sep, 'condarc')
    reset_context([prefix_condarc])


def package_is_installed(prefix, package, exact=False):
    packages = list(install_linked(prefix))
    if '::' in package:
        packages = list(map(text_type, packages))
    else:
        packages = list(map(lambda x: x.dist_name, packages))
    if exact:
        return package in packages
    return any(p.startswith(package) for p in packages)


def assert_package_is_installed(prefix, package, exact=False):
    if not package_is_installed(prefix, package, exact):
        print(list(install_linked(prefix)))
        raise AssertionError("package {0} is not in prefix".format(package))


def get_conda_list_tuple(prefix, package_name):
    stdout, stderr = run_command(Commands.LIST, prefix)
    stdout_lines = stdout.split('\n')
    package_line = next((line for line in stdout_lines
                         if line.lower().startswith(package_name + " ")), None)
    return package_line.split()


def get_shortcut_dir():
    assert on_win
    user_mode = 'user' if exists(join(sys.prefix, u'.nonadmin')) else 'system'
    try:
        from menuinst.win32 import dirs_src as win_locations
        return win_locations[user_mode]["start"][0]
    except ImportError:
        try:
            from menuinst.win32 import dirs as win_locations
            return win_locations[user_mode]["start"]
        except ImportError:
            raise


@pytest.mark.integration
class IntegrationTests(TestCase):

    def setUp(self):
        PackageCache.clear()

    def test_install_python2(self):
        with make_temp_env("python=2") as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            assert_package_is_installed(prefix, 'python-2')

            # regression test for #4513
            run_command(Commands.CONFIG, prefix, "--add channels https://repo.continuum.io/pkgs/not-a-channel")
            stdout, stderr = run_command(Commands.SEARCH, prefix, "python --json")
            packages = json.loads(stdout)
            assert len(packages) > 1

    def test_create_install_update_remove(self):
        with make_temp_env("python=3.5") as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            assert_package_is_installed(prefix, 'python-3')

            run_command(Commands.INSTALL, prefix, 'flask=0.10')
            assert_package_is_installed(prefix, 'flask-0.10.1')
            assert_package_is_installed(prefix, 'python-3')

            # Test force reinstall
            run_command(Commands.INSTALL, prefix, '--force', 'flask=0.10')
            assert_package_is_installed(prefix, 'flask-0.10.1')
            assert_package_is_installed(prefix, 'python-3')

            run_command(Commands.UPDATE, prefix, 'flask')
            assert not package_is_installed(prefix, 'flask-0.10.1')
            assert_package_is_installed(prefix, 'flask')
            assert_package_is_installed(prefix, 'python-3')

            run_command(Commands.REMOVE, prefix, 'flask')
            assert not package_is_installed(prefix, 'flask-0.')
            assert_package_is_installed(prefix, 'python-3')

            run_command(Commands.INSTALL, prefix, '--revision 0')
            assert not package_is_installed(prefix, 'flask')
            assert_package_is_installed(prefix, 'python-3')

            self.assertRaises(CondaError, run_command, Commands.INSTALL, prefix, 'conda')
            assert not package_is_installed(prefix, 'conda')

            self.assertRaises(CondaError, run_command, Commands.INSTALL, prefix, 'constructor=1.0')
            assert not package_is_installed(prefix, 'constructor')

    def test_json_create_install_update_remove(self):
        # regression test for #5384

        def assert_json_parsable(content):
            string = None
            try:
                for string in content and content.split('\0') or ():
                    json.loads(string)
            except Exception as e:
                log.warn(
                    "Problem parsing json output.\n"
                    "  content: %s\n"
                    "  string: %s\n"
                    "  error: %r",
                    content, string, e
                )
                raise

        try:
            prefix = make_temp_prefix(str(uuid4())[:7])

            stdout, stderr = run_command(Commands.CREATE, prefix, "python=3.5 --json")
            assert_json_parsable(stdout)
            assert not stderr

            stdout, stderr = run_command(Commands.INSTALL, prefix, 'flask=0.10 --json')
            assert_json_parsable(stdout)
            assert not stderr
            assert_package_is_installed(prefix, 'flask-0.10.1')
            assert_package_is_installed(prefix, 'python-3')

            # Test force reinstall
            stdout, stderr = run_command(Commands.INSTALL, prefix, '--force', 'flask=0.10', '--json')
            assert_json_parsable(stdout)
            assert not stderr
            assert_package_is_installed(prefix, 'flask-0.10.1')
            assert_package_is_installed(prefix, 'python-3')

            stdout, stderr = run_command(Commands.UPDATE, prefix, 'flask --json')
            assert_json_parsable(stdout)
            assert not stderr
            assert not package_is_installed(prefix, 'flask-0.10.1')
            assert_package_is_installed(prefix, 'flask')
            assert_package_is_installed(prefix, 'python-3')

            stdout, stderr = run_command(Commands.REMOVE, prefix, 'flask --json')
            assert_json_parsable(stdout)
            assert not stderr
            assert not package_is_installed(prefix, 'flask-0.')
            assert_package_is_installed(prefix, 'python-3')

            stdout, stderr = run_command(Commands.INSTALL, prefix, '--revision 0', '--json')
            assert_json_parsable(stdout)
            assert not stderr
            assert not package_is_installed(prefix, 'flask')
            assert_package_is_installed(prefix, 'python-3')
        finally:
            rmtree(prefix, ignore_errors=True)

    def test_noarch_python_package_with_entry_points(self):
        with make_temp_env("-c conda-test flask") as prefix:
            py_ver = get_python_version_for_prefix(prefix)
            sp_dir = get_python_site_packages_short_path(py_ver)
            py_file = sp_dir + "/flask/__init__.py"
            pyc_file = pyc_path(py_file, py_ver)
            assert isfile(join(prefix, py_file))
            assert isfile(join(prefix, pyc_file))
            exe_path = join(prefix, get_bin_directory_short_path(), 'flask')
            if on_win:
                exe_path += ".exe"
            assert isfile(exe_path)

            run_command(Commands.REMOVE, prefix, "flask")

            assert not isfile(join(prefix, py_file))
            assert not isfile(join(prefix, pyc_file))
            assert not isfile(exe_path)

    def test_noarch_python_package_without_entry_points(self):
        # regression test for #4546
        with make_temp_env("-c conda-test itsdangerous") as prefix:
            py_ver = get_python_version_for_prefix(prefix)
            sp_dir = get_python_site_packages_short_path(py_ver)
            py_file = sp_dir + "/itsdangerous.py"
            pyc_file = pyc_path(py_file, py_ver)
            assert isfile(join(prefix, py_file))
            assert isfile(join(prefix, pyc_file))

            run_command(Commands.REMOVE, prefix, "itsdangerous")

            assert not isfile(join(prefix, py_file))
            assert not isfile(join(prefix, pyc_file))

    def test_noarch_generic_package(self):
        with make_temp_env("-c conda-test font-ttf-inconsolata") as prefix:
            assert isfile(join(prefix, 'fonts', 'Inconsolata-Regular.ttf'))

    def test_create_empty_env(self):
        with make_temp_env() as prefix:
            assert exists(join(prefix, 'conda-meta/history'))

            list_output = run_command(Commands.LIST, prefix)
            stdout = list_output[0]
            stderr = list_output[1]
            expected_output = """# packages in environment at %s:
#

""" % prefix
            self.assertEqual(stdout, expected_output)
            self.assertEqual(stderr, '')

            revision_output = run_command(Commands.LIST, prefix, '--revisions')
            stdout = revision_output[0]
            stderr = revision_output[1]
            self.assertEquals(stderr, '')
            self.assertIsInstance(stdout, str)

    @pytest.mark.skipif(True, reason="pip 10 dropped --egg")
    def test_list_with_pip_egg(self):
        with make_temp_env("python=3.5 pip") as prefix:
            check_call(PYTHON_BINARY + " -m pip install --egg --no-binary flask flask==0.10.1",
                       cwd=prefix, shell=True)
            stdout, stderr = run_command(Commands.LIST, prefix)
            stdout_lines = stdout.split('\n')
            assert any(line.endswith("<pip>") for line in stdout_lines
                       if line.lower().startswith("flask"))

            # regression test for #5847
            #   when using rm_rf on a directory
            assert prefix in linked_data_
            rm_rf(join(prefix, get_python_site_packages_short_path("3.5")))
            assert prefix not in linked_data_

    def test_list_with_pip_wheel(self):
        with make_temp_env("python=3.6 pip") as prefix:
            check_call(PYTHON_BINARY + " -m pip install flask==0.10.1",
                       cwd=prefix, shell=True)
            stdout, stderr = run_command(Commands.LIST, prefix)
            stdout_lines = stdout.split('\n')
            assert any(line.endswith("<pip>") for line in stdout_lines
                       if line.lower().startswith("flask"))

            # regression test for #3433
            run_command(Commands.INSTALL, prefix, "python=3.5")
            assert_package_is_installed(prefix, 'python-3.5.')

            # regression test for #5847
            #   when using rm_rf on a file
            assert prefix in linked_data_
            rm_rf(join(prefix, get_python_site_packages_short_path("3.5")), "os.py")
            assert prefix not in linked_data_

        # regression test for #5980, related to #5847
        with make_temp_env() as prefix:
            assert isdir(prefix)
            assert prefix in linked_data_

            rmtree(prefix)
            assert not isdir(prefix)
            assert prefix in linked_data_

            rm_rf(prefix)
            assert not isdir(prefix)
            assert prefix not in linked_data_

    def test_install_tarball_from_local_channel(self):
        # Regression test for #2812
        # install from local channel
        with make_temp_env() as prefix, make_temp_channel(["flask-0.10.1"]) as channel:
            run_command(Commands.INSTALL, prefix, '-c', channel, 'flask=0.10.1', '--json')
            assert_package_is_installed(prefix, channel + '::' + 'flask-')
            flask_fname = [p for p in itervalues(linked_data(prefix)) if p['name'] == 'flask'][0]['fn']

            run_command(Commands.REMOVE, prefix, 'flask')
            assert not package_is_installed(prefix, 'flask-0')

            # Regression test for 2970
            # install from build channel as a tarball
            tar_path = join(PackageCache.first_writable().pkgs_dir, flask_fname)
            conda_bld = join(dirname(PackageCache.first_writable().pkgs_dir), 'conda-bld')
            conda_bld_sub = join(conda_bld, context.subdir)
            if not isdir(conda_bld_sub):
                os.makedirs(conda_bld_sub)
            tar_bld_path = join(conda_bld_sub, basename(tar_path))
            copyfile(tar_path, tar_bld_path)
            # CondaFileNotFoundError: '/home/travis/virtualenv/python2.7.9/conda-bld/linux-64/flask-0.10.1-py27_2.tar.bz2'.
            run_command(Commands.INSTALL, prefix, tar_bld_path)
            assert_package_is_installed(prefix, 'flask-')

    def test_tarball_install_and_bad_metadata(self):
        with make_temp_env("python flask=0.10.1 --json") as prefix:
            assert_package_is_installed(prefix, 'flask-0.10.1')
            flask_data = [p for p in itervalues(linked_data(prefix)) if p['name'] == 'flask'][0]
            run_command(Commands.REMOVE, prefix, 'flask')
            assert not package_is_installed(prefix, 'flask-0.10.1')
            assert_package_is_installed(prefix, 'python')

            flask_fname = flask_data['fn']
            tar_old_path = join(PackageCache.first_writable().pkgs_dir, flask_fname)

            assert isfile(tar_old_path)

            # regression test for #2886 (part 1 of 2)
            # install tarball from package cache, default channel
            run_command(Commands.INSTALL, prefix, tar_old_path)
            assert_package_is_installed(prefix, 'flask-0.')

            # regression test for #2626
            # install tarball with full path, outside channel
            tar_new_path = join(prefix, flask_fname)
            copyfile(tar_old_path, tar_new_path)
            run_command(Commands.INSTALL, prefix, '"%s"' % tar_new_path)
            assert_package_is_installed(prefix, 'flask-0')

            # regression test for #2626
            # install tarball with relative path, outside channel
            run_command(Commands.REMOVE, prefix, 'flask')
            assert not package_is_installed(prefix, 'flask-0.10.1')
            tar_new_path = relpath(tar_new_path)
            run_command(Commands.INSTALL, prefix, '"%s"' % tar_new_path)
            assert_package_is_installed(prefix, 'flask-0.')

            # regression test for #2886 (part 2 of 2)
            # install tarball from package cache, local channel
            run_command(Commands.REMOVE, prefix, 'flask', '--json')
            assert not package_is_installed(prefix, 'flask-0')
            run_command(Commands.INSTALL, prefix, tar_old_path)
            # The last install was from the `local::` channel
            assert_package_is_installed(prefix, 'flask-')

            # regression test for #2599
            linked_data_.clear()
            flask_metadata = glob(join(prefix, 'conda-meta', flask_fname[:-8] + '.json'))[-1]
            bad_metadata = join(prefix, 'conda-meta', 'flask.json')
            copyfile(flask_metadata, bad_metadata)
            assert not package_is_installed(prefix, 'flask', exact=True)
            assert_package_is_installed(prefix, 'flask-0.')

    def test_remove_all(self):
        with make_temp_env("python=2") as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            assert_package_is_installed(prefix, 'python-2')

            run_command(Commands.REMOVE, prefix, '--all')
            assert not exists(prefix)

    @pytest.mark.skipif(on_win, reason="nomkl not present on windows")
    def test_remove_features(self):
        with make_temp_env("python=2 numpy=1.13 nomkl") as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            assert_package_is_installed(prefix, 'numpy')
            assert_package_is_installed(prefix, 'nomkl')
            assert not package_is_installed(prefix, 'mkl')

            run_command(Commands.REMOVE, prefix, '--features', 'nomkl')
            assert_package_is_installed(prefix, 'numpy')
            assert not package_is_installed(prefix, 'nomkl')
            assert_package_is_installed(prefix, 'mkl')

    @pytest.mark.skipif(on_win and context.bits == 32, reason="no 32-bit windows python on conda-forge")
    def test_dash_c_usage_replacing_python(self):
        # Regression test for #2606
        with make_temp_env("-c conda-forge python=3.5") as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            run_command(Commands.INSTALL, prefix, "decorator")
            assert_package_is_installed(prefix, 'conda-forge::python-3.5')

            with make_temp_env('--clone "%s"' % prefix) as clone_prefix:
                assert_package_is_installed(clone_prefix, 'conda-forge::python-3.5')
                assert_package_is_installed(clone_prefix, "decorator")

            # Regression test for #2645
            fn = glob(join(prefix, 'conda-meta', 'python-3.5*.json'))[-1]
            with open(fn) as f:
                data = json.load(f)
            for field in ('url', 'channel', 'schannel'):
                if field in data:
                    del data[field]
            with open(fn, 'w') as f:
                json.dump(data, f)
            linked_data_.clear()

            with make_temp_env('-c conda-forge --clone "%s"' % prefix) as clone_prefix:
                assert_package_is_installed(clone_prefix, 'python-3.5')
                assert_package_is_installed(clone_prefix, 'decorator')

    def test_install_prune(self):
        with make_temp_env("python=2 decorator") as prefix:
            assert_package_is_installed(prefix, 'decorator')

            # prune is a feature used by conda-env
            # conda itself does not provide a public API for it
            index = get_index_trap(prefix=prefix)
            actions_set = plan.install_actions_list(prefix,
                                           index,
                                           specs=['flask'],
                                           prune=True)
            for actions in actions_set:
                plan.execute_actions(actions, index, verbose=True)

            assert_package_is_installed(prefix, 'flask')
            assert not package_is_installed(prefix, 'decorator')

    @pytest.mark.skipif(on_win, reason="mkl package not available on Windows")
    def test_install_features(self):
        with make_temp_env("python=2 numpy") as prefix:
            numpy_details = get_conda_list_tuple(prefix, "numpy")
            assert len(numpy_details) == 3 or 'nomkl' not in numpy_details[3]

            run_command(Commands.INSTALL, prefix, "nomkl")
            numpy_details = get_conda_list_tuple(prefix, "numpy")
            assert len(numpy_details) == 4 and 'nomkl' in numpy_details[3]

    def test_clone_offline_simple(self):
        with make_temp_env("python flask=0.10.1") as prefix:
            assert_package_is_installed(prefix, 'flask-0.10.1')
            assert_package_is_installed(prefix, 'python')

            with make_temp_env('--clone "%s"' % prefix, "--offline") as clone_prefix:
                assert context.offline
                assert_package_is_installed(clone_prefix, 'flask-0.10.1')
                assert_package_is_installed(clone_prefix, 'python')

    def test_rpy_search(self):
        with make_temp_env("python=3.5") as prefix:
            run_command(Commands.CONFIG, prefix, "--add channels https://repo.continuum.io/pkgs/free")
            run_command(Commands.CONFIG, prefix, "--remove channels defaults")
            stdout, stderr = run_command(Commands.CONFIG, prefix, "--show", "--json")
            json_obj = json_loads(stdout)
            assert 'defaults' not in json_obj['channels']

            assert_package_is_installed(prefix, 'python')
            assert 'r' not in context.channels

            # assert conda search cannot find rpy2
            stdout, stderr = run_command(Commands.SEARCH, prefix, "rpy2", "--json", use_exception_handler=True)
            json_obj = json_loads(stdout.replace("Fetching package metadata ...", "").strip())
            assert json_obj['exception_name'] == 'PackageNotFoundError'

            # add r channel
            run_command(Commands.CONFIG, prefix, "--add channels r")
            stdout, stderr = run_command(Commands.CONFIG, prefix, "--show", "--json")
            json_obj = json_loads(stdout)
            assert 'r' in json_obj['channels']

            # assert conda search can now find rpy2
            stdout, stderr = run_command(Commands.SEARCH, prefix, "rpy2", "--json")
            json_obj = json_loads(stdout.replace("Fetching package metadata ...", "").strip())
            assert len(json_obj['rpy2']) > 1

    def test_clone_offline_multichannel_with_untracked(self):
        with make_temp_env("python=3.5") as prefix:
            run_command(Commands.CONFIG, prefix, "--add channels https://repo.continuum.io/pkgs/free")
            run_command(Commands.CONFIG, prefix, "--remove channels defaults")

            run_command(Commands.INSTALL, prefix, "-c conda-test flask")

            touch(join(prefix, 'test.file'))  # untracked file
            with make_temp_env("--clone '%s'" % prefix, "--offline") as clone_prefix:
                assert context.offline
                assert_package_is_installed(clone_prefix, 'python-3.5')
                assert_package_is_installed(clone_prefix, 'flask-0.11.1-py_0')
                assert isfile(join(clone_prefix, 'test.file'))  # untracked file

    def test_package_pinning(self):
        with make_temp_env("python=2.7 itsdangerous=0.23 pytz=2015.7") as prefix:
            assert package_is_installed(prefix, "itsdangerous-0.23")
            assert package_is_installed(prefix, "python-2.7")
            assert package_is_installed(prefix, "pytz-2015.7")

            with open(join(prefix, 'conda-meta', 'pinned'), 'w') as fh:
                fh.write("itsdangerous 0.23\n")

            run_command(Commands.UPDATE, prefix, "--all")
            assert package_is_installed(prefix, "itsdangerous-0.23")
            # assert not package_is_installed(prefix, "python-3.5")  # should be python-3.6, but it's not because of add_defaults_to_specs
            assert package_is_installed(prefix, "python-2.7")
            assert not package_is_installed(prefix, "pytz-2015.7")
            assert package_is_installed(prefix, "pytz-")

            run_command(Commands.UPDATE, prefix, "--all --no-pin")
            assert package_is_installed(prefix, "python-2.7")
            assert not package_is_installed(prefix, "itsdangerous-0.23")

    def test_update_deps_flag_absent(self):
        with make_temp_env("python=2 itsdangerous=0.23") as prefix:
            assert package_is_installed(prefix, 'python-2')
            assert package_is_installed(prefix, 'itsdangerous-0.23')
            assert not package_is_installed(prefix, 'flask')

            run_command(Commands.INSTALL, prefix, 'flask')
            assert package_is_installed(prefix, 'python-2')
            assert package_is_installed(prefix, 'itsdangerous-0.23')
            assert package_is_installed(prefix, 'flask')

    @pytest.mark.xfail(datetime.now() < datetime(2018, 3, 1), reason="#5263", strict=True)
    def test_update_deps_flag_present(self):
        with make_temp_env("python=2 itsdangerous=0.23") as prefix:
            assert package_is_installed(prefix, 'python-2')
            assert package_is_installed(prefix, 'itsdangerous-0.23')
            assert not package_is_installed(prefix, 'flask')

            run_command(Commands.INSTALL, prefix, '--update-deps python=2 flask')
            assert package_is_installed(prefix, 'python-2')
            assert not package_is_installed(prefix, 'itsdangerous-0.23')
            assert package_is_installed(prefix, 'itsdangerous')
            assert package_is_installed(prefix, 'flask')

    # @pytest.mark.skipif(not on_win, reason="shortcuts only relevant on Windows")
    # def test_shortcut_in_underscore_env_shows_message(self):
    #     prefix = make_temp_prefix("_" + str(uuid4())[:7])
    #     with make_temp_env(prefix=prefix):
    #         stdout, stderr = run_command(Commands.INSTALL, prefix, "console_shortcut")
    #         assert ("Environment name starts with underscore '_'.  "
    #                 "Skipping menu installation." in stderr)

    @pytest.mark.skipif(not on_win, reason="shortcuts only relevant on Windows")
    def test_shortcut_not_attempted_with_no_shortcuts_arg(self):
        prefix = make_temp_prefix("_" + str(uuid4())[:7])
        shortcut_dir = get_shortcut_dir()
        shortcut_file = join(shortcut_dir, "Anaconda Prompt ({0}).lnk".format(basename(prefix)))
        with make_temp_env(prefix=prefix):
            stdout, stderr = run_command(Commands.INSTALL, prefix, "console_shortcut",
                                         "--no-shortcuts")
            assert ("Environment name starts with underscore '_'.  Skipping menu installation."
                    not in stderr)
            assert not isfile(shortcut_file)

    @pytest.mark.skipif(not on_win, reason="shortcuts only relevant on Windows")
    def test_shortcut_creation_installs_shortcut(self):
        shortcut_dir = get_shortcut_dir()
        shortcut_dir = join(shortcut_dir, "Anaconda{0} ({1}-bit)"
                                          "".format(sys.version_info.major, context.bits))

        prefix = make_temp_prefix(str(uuid4())[:7])
        shortcut_file = join(shortcut_dir, "Anaconda Prompt ({0}).lnk".format(basename(prefix)))
        try:
            with make_temp_env("console_shortcut", prefix=prefix):
                assert package_is_installed(prefix, 'console_shortcut')
                assert isfile(shortcut_file), ("Shortcut not found in menu dir. "
                                               "Contents of dir:\n"
                                               "{0}".format(os.listdir(shortcut_dir)))

                # make sure that cleanup without specifying --shortcuts still removes shortcuts
                run_command(Commands.REMOVE, prefix, 'console_shortcut')
                assert not package_is_installed(prefix, 'console_shortcut')
                assert not isfile(shortcut_file)
        finally:
            rmtree(prefix, ignore_errors=True)
            if isfile(shortcut_file):
                os.remove(shortcut_file)

    @pytest.mark.skipif(not on_win, reason="shortcuts only relevant on Windows")
    def test_shortcut_absent_does_not_barf_on_uninstall(self):
        shortcut_dir = get_shortcut_dir()
        shortcut_dir = join(shortcut_dir, "Anaconda{0} ({1}-bit)"
                                          "".format(sys.version_info.major, context.bits))

        prefix = make_temp_prefix(str(uuid4())[:7])
        shortcut_file = join(shortcut_dir, "Anaconda Prompt ({0}).lnk".format(basename(prefix)))
        assert not isfile(shortcut_file)

        try:
            # including --no-shortcuts should not get shortcuts installed
            with make_temp_env("console_shortcut", "--no-shortcuts", prefix=prefix):
                assert package_is_installed(prefix, 'console_shortcut')
                assert not isfile(shortcut_file)

                # make sure that cleanup without specifying --shortcuts still removes shortcuts
                run_command(Commands.REMOVE, prefix, 'console_shortcut')
                assert not package_is_installed(prefix, 'console_shortcut')
                assert not isfile(shortcut_file)
        finally:
            rmtree(prefix, ignore_errors=True)
            if isfile(shortcut_file):
                os.remove(shortcut_file)

    @pytest.mark.skipif(not on_win, reason="shortcuts only relevant on Windows")
    def test_shortcut_absent_when_condarc_set(self):
        shortcut_dir = get_shortcut_dir()
        shortcut_dir = join(shortcut_dir, "Anaconda{0} ({1}-bit)"
                                          "".format(sys.version_info.major, context.bits))

        prefix = make_temp_prefix(str(uuid4())[:7])
        shortcut_file = join(shortcut_dir, "Anaconda Prompt ({0}).lnk".format(basename(prefix)))
        assert not isfile(shortcut_file)

        # set condarc shortcuts: False
        run_command(Commands.CONFIG, prefix, "--set shortcuts false")
        stdout, stderr = run_command(Commands.CONFIG, prefix, "--get", "--json")
        json_obj = json_loads(stdout)
        assert json_obj['rc_path'] == join(prefix, 'condarc')
        assert json_obj['get']['shortcuts'] is False

        try:
            with make_temp_env("console_shortcut", prefix=prefix):
                # including shortcuts: False from condarc should not get shortcuts installed
                assert package_is_installed(prefix, 'console_shortcut')
                assert not isfile(shortcut_file)

                # make sure that cleanup without specifying --shortcuts still removes shortcuts
                run_command(Commands.REMOVE, prefix, 'console_shortcut')
                assert not package_is_installed(prefix, 'console_shortcut')
                assert not isfile(shortcut_file)
        finally:
            rmtree(prefix, ignore_errors=True)
            if isfile(shortcut_file):
                os.remove(shortcut_file)

    def test_create_default_packages(self):
        # Regression test for #3453
        try:
            prefix = make_temp_prefix(str(uuid4())[:7])

            # set packages
            run_command(Commands.CONFIG, prefix, "--add create_default_packages pip")
            run_command(Commands.CONFIG, prefix, "--add create_default_packages flask")
            stdout, stderr = run_command(Commands.CONFIG, prefix, "--show")
            yml_obj = yaml_load(stdout)
            assert yml_obj['create_default_packages'] == ['flask', 'pip']

            assert not package_is_installed(prefix, 'python-2')
            assert not package_is_installed(prefix, 'pytz')
            assert not package_is_installed(prefix, 'flask')

            with make_temp_env("python=2", "pytz", prefix=prefix):
                assert_package_is_installed(prefix, 'python-2')
                assert_package_is_installed(prefix, 'pytz')
                assert_package_is_installed(prefix, 'flask')

        finally:
            rmtree(prefix, ignore_errors=True)

    def test_create_default_packages_no_default_packages(self):
        try:
            prefix = make_temp_prefix(str(uuid4())[:7])

            # set packages
            run_command(Commands.CONFIG, prefix, "--add create_default_packages pip")
            run_command(Commands.CONFIG, prefix, "--add create_default_packages flask")
            stdout, stderr = run_command(Commands.CONFIG, prefix, "--show")
            yml_obj = yaml_load(stdout)
            assert yml_obj['create_default_packages'] == ['flask', 'pip']

            assert not package_is_installed(prefix, 'python-2')
            assert not package_is_installed(prefix, 'pytz')
            assert not package_is_installed(prefix, 'flask')

            with make_temp_env("python=2", "pytz", "--no-default-packages", prefix=prefix):
                assert_package_is_installed(prefix, 'python-2')
                assert_package_is_installed(prefix, 'pytz')
                assert not package_is_installed(prefix, 'flask')

        finally:
            rmtree(prefix, ignore_errors=True)

    def test_create_dry_run(self):
        # Regression test for #3453
        prefix = '/some/place'
        with pytest.raises(DryRunExit):
            run_command(Commands.CREATE, prefix, "--dry-run")
        stdout, stderr = run_command(Commands.CREATE, prefix, "--dry-run", use_exception_handler=True)
        assert join('some', 'place') in stdout
        # TODO: This assert passes locally but fails on CI boxes; figure out why and re-enable
        # assert "The following empty environments will be CREATED" in stdout

        prefix = '/another/place'
        with pytest.raises(DryRunExit):
            run_command(Commands.CREATE, prefix, "flask", "--dry-run")
        stdout, stderr = run_command(Commands.CREATE, prefix, "flask", "--dry-run", use_exception_handler=True)
        assert "flask:" in stdout
        assert "python:" in stdout
        assert join('another', 'place') in stdout

    def test_packages_not_found(self):
        with make_temp_env() as prefix:
            with pytest.raises(PackageNotFoundError) as exc:
                run_command(Commands.INSTALL, prefix, "not-a-real-package")
            assert "not-a-real-package" in text_type(exc.value)

            stdout, stderr = run_command(Commands.INSTALL, prefix, "not-a-real-package",
                                         use_exception_handler=True)
            assert "not-a-real-package" in stderr

            stdout, stderr = run_command(Commands.SEARCH, prefix, "not-a-real-package", "--json",
                                         use_exception_handler=True)
            assert not stderr
            json_obj = json_loads(stdout.strip())
            assert json_obj['exception_name'] == 'PackageNotFoundError'
            assert not len(json_obj.keys()) == 0

    @pytest.mark.skipif(on_win, reason="gawk is a windows only package")
    def test_search_gawk_not_win_filter(self):
        with make_temp_env() as prefix:
            stdout, stderr = run_command(
                Commands.SEARCH, prefix, "gawk", "--platform", "win-64", "--json",
                "-c", "https://repo.continuum.io/pkgs/msys2 --json",
                use_exception_handler=True,
            )
            json_obj = json_loads(stdout.replace("Fetching package metadata ...", "").strip())
            assert "gawk" in json_obj.keys()
            assert "m2-gawk" in json_obj.keys()
            assert len(json_obj.keys()) == 2

    @pytest.mark.skipif(not on_win, reason="gawk is a windows only package")
    def test_search_gawk_on_win(self):
        with make_temp_env() as prefix:
            stdout, stderr = run_command(Commands.SEARCH, prefix, "gawk", "--json", use_exception_handler=True)
            json_obj = json_loads(stdout.replace("Fetching package metadata ...", "").strip())
            assert "gawk" in json_obj.keys()
            assert "m2-gawk" in json_obj.keys()
            assert len(json_obj.keys()) == 2

    @pytest.mark.skipif(not on_win, reason="gawk is a windows only package")
    def test_search_gawk_on_win_filter(self):
        with make_temp_env() as prefix:
            stdout, stderr = run_command(Commands.SEARCH, prefix, "gawk", "--platform",
                                         "linux-64", "--json", use_exception_handler=True)
            json_obj = json_loads(stdout.replace("Fetching package metadata ...", "").strip())
            assert not len(json_obj.keys()) == 0

    def test_bad_anaconda_token_infinite_loop(self):
        # This test is being changed around 2017-10-17, when the behavior of anaconda.org
        # was changed.  Previously, an expired token would return with a 401 response.
        # Now, a 200 response is always given, with any public packages available on the channel.
        response = requests.get("https://conda.anaconda.org/t/cqgccfm1mfma/data-portal/"
                                "%s/repodata.json" % context.subdir)
        assert response.status_code == 200

        try:
            prefix = make_temp_prefix(str(uuid4())[:7])
            channel_url = "https://conda.anaconda.org/t/cqgccfm1mfma/data-portal"
            run_command(Commands.CONFIG, prefix, "--add channels %s" % channel_url)
            stdout, stderr = run_command(Commands.CONFIG, prefix, "--show")
            yml_obj = yaml_load(stdout)
            assert yml_obj['channels'] == [channel_url, 'defaults']

            with pytest.raises(PackageNotFoundError):
                run_command(Commands.SEARCH, prefix, "boltons", "--json")

            stdout, stderr = run_command(Commands.SEARCH, prefix, "anaconda-mosaic", "--json")

            json_obj = json.loads(stdout)
            assert "anaconda-mosaic" in json_obj
            assert len(json_obj["anaconda-mosaic"]) > 0

        finally:
            rmtree(prefix, ignore_errors=True)
            reset_context()

    def test_anaconda_token_with_private_package(self):
        # TODO: should also write a test to use binstar_client to set the token,
        # then let conda load the token

        # Step 0. xfail if a token is set, for example when testing locally
        tokens = read_binstar_tokens()
        if tokens:
            pytest.xfail("binstar token found in global configuration")

        # Step 1. Make sure without the token we don't see the anyjson package
        try:
            prefix = make_temp_prefix(str(uuid4())[:7])
            channel_url = "https://conda.anaconda.org/kalefranz"
            run_command(Commands.CONFIG, prefix, "--add channels %s" % channel_url)
            run_command(Commands.CONFIG, prefix, "--remove channels defaults")
            stdout, stderr = run_command(Commands.CONFIG, prefix, "--show")
            yml_obj = yaml_load(stdout)
            assert yml_obj['channels'] == [channel_url]

            stdout, stderr = run_command(Commands.SEARCH, prefix, "anyjson", "--platform",
                                         "linux-64", "--json", use_exception_handler=True)
            json_obj = json_loads(stdout)
            assert json_obj['exception_name'] == 'PackageNotFoundError'

        finally:
            rmtree(prefix, ignore_errors=True)
            reset_context()

        # Step 2. Now with the token make sure we can see the anyjson package
        try:
            prefix = make_temp_prefix(str(uuid4())[:7])
            channel_url = "https://conda.anaconda.org/t/zlZvSlMGN7CB/kalefranz"
            run_command(Commands.CONFIG, prefix, "--add channels %s" % channel_url)
            run_command(Commands.CONFIG, prefix, "--remove channels defaults")
            stdout, stderr = run_command(Commands.CONFIG, prefix, "--show")
            yml_obj = yaml_load(stdout)
            assert yml_obj['channels'] == [channel_url]

            stdout, stderr = run_command(Commands.SEARCH, prefix, "anyjson", "--platform",
                                         "linux-64", "--json")
            json_obj = json_loads(stdout)
            assert 'anyjson' in json_obj

        finally:
            rmtree(prefix, ignore_errors=True)

    def test_clean_index_cache(self):
        prefix = ''

        # make sure we have something in the index cache
        stdout, stderr = run_command(Commands.INFO, prefix, "flask --json")
        assert "flask" in json_loads(stdout)
        index_cache_dir = create_cache_dir()
        assert glob(join(index_cache_dir, "*.json"))

        # now clear it
        run_command(Commands.CLEAN, prefix, "--index-cache")
        assert not glob(join(index_cache_dir, "*.json"))

    def test_use_index_cache(self):
        from conda.connection import CondaSession

        prefix = make_temp_prefix("_" + str(uuid4())[:7])
        with make_temp_env(prefix=prefix):
            # First, clear the index cache to make sure we start with an empty cache.
            index_cache_dir = create_cache_dir()
            run_command(Commands.CLEAN, '', "--index-cache")
            assert not glob(join(index_cache_dir, "*.json"))

            # Then, populate the index cache.
            orig_get = CondaSession.get
            with patch.object(CondaSession, 'get', autospec=True) as mock_method:
                def side_effect(self, url, **kwargs):
                    # Make sure that we don't use the cache because of the
                    # corresponding HTTP header. This test is supposed to test
                    # whether the --use-index-cache causes the cache to be used.
                    result = orig_get(self, url, **kwargs)
                    for header in ['Etag', 'Last-Modified', 'Cache-Control']:
                        if header in result.headers:
                            del result.headers[header]
                    return result

                mock_method.side_effect = side_effect
                stdout, stderr = run_command(Commands.INFO, prefix, "flask --json")
                assert mock_method.called

            # Next run with --use-index-cache and make sure it actually hits the cache
            # and does not go out fetching index data remotely.
            with patch.object(CondaSession, 'get', autospec=True) as mock_method:
                def side_effect(self, url, **kwargs):
                    if url.endswith('/repodata.json') or url.endswith('/repodata.json.bz2'):
                        raise AssertionError('Index cache was not hit')
                    else:
                        return orig_get(self, url, **kwargs)

                mock_method.side_effect = side_effect
                run_command(Commands.INSTALL, prefix, "flask", "--json", "--use-index-cache")

    def test_offline_with_empty_index_cache(self):
        with make_temp_env() as prefix, make_temp_channel(['flask-0.10.1']) as channel:
            # Clear the index cache.
            index_cache_dir = create_cache_dir()
            run_command(Commands.CLEAN, '', "--index-cache")
            assert not exists(index_cache_dir)

            # Then attempt to install a package with --offline. The package (flask) is
            # available in a local channel, however its dependencies are not. Make sure
            # that a) it fails because the dependencies are not available and b)
            # we don't try to download the repodata from non-local channels but we do
            # download repodata from local channels.
            from conda.connection import CondaSession

            orig_get = CondaSession.get

            result_dict = {}
            def side_effect(self, url, **kwargs):
                if not url.startswith('file://'):
                    raise AssertionError('Attempt to fetch repodata: {}'.format(url))
                if url.startswith(channel):
                    result_dict['local_channel_seen'] = True
                return orig_get(self, url, **kwargs)

            with patch.object(CondaSession, 'get', autospec=True) as mock_method:
                mock_method.side_effect = side_effect

                # Fails because flask dependencies are not retrievable.
                with pytest.raises(PackageNotFoundError):
                    run_command(Commands.INSTALL, prefix, "-c", channel,
                                "flask", "--json", "--offline")

                # The mock should have been called with our local channel URL though.
                assert result_dict.get('local_channel_seen')

    def test_clean_tarballs_and_packages(self):
        pkgs_dir = PackageCache.first_writable().pkgs_dir
        mkdir_p(pkgs_dir)
        pkgs_dir_hold = pkgs_dir + '_hold'
        try:
            shutil.move(pkgs_dir, pkgs_dir_hold)
            with make_temp_env("flask") as prefix:
                pkgs_dir_contents = [join(pkgs_dir, d) for d in os.listdir(pkgs_dir)]
                pkgs_dir_dirs = [d for d in pkgs_dir_contents if isdir(d)]
                pkgs_dir_tarballs = [f for f in pkgs_dir_contents if f.endswith('.tar.bz2')]
                assert any(basename(d).startswith('flask-') for d in pkgs_dir_dirs)
                assert any(basename(f).startswith('flask-') for f in pkgs_dir_tarballs)

                # --json flag is regression test for #5451
                run_command(Commands.CLEAN, prefix, "--packages --yes --json")

                # --json flag is regression test for #5451
                run_command(Commands.CLEAN, prefix, "--tarballs --yes --json")

                pkgs_dir_contents = [join(pkgs_dir, d) for d in os.listdir(pkgs_dir)]
                pkgs_dir_dirs = [d for d in pkgs_dir_contents if isdir(d)]
                pkgs_dir_tarballs = [f for f in pkgs_dir_contents if f.endswith('.tar.bz2')]

                assert any(basename(d).startswith('flask-') for d in pkgs_dir_dirs)
                assert not any(basename(f).startswith('flask-') for f in pkgs_dir_tarballs)

            run_command(Commands.CLEAN, prefix, "--packages --yes")

            pkgs_dir_contents = [join(pkgs_dir, d) for d in os.listdir(pkgs_dir)]
            pkgs_dir_dirs = [d for d in pkgs_dir_contents if isdir(d)]
            assert not any(basename(d).startswith('flask-') for d in pkgs_dir_dirs)
        finally:
            rm_rf(pkgs_dir)
            shutil.move(pkgs_dir_hold, pkgs_dir)
            PackageCache.clear()

    def test_clean_source_cache(self):
        cache_dirs = {
            'source cache': text_type(context.src_cache),
            'git cache': text_type(context.git_cache),
            'hg cache': text_type(context.hg_cache),
            'svn cache': text_type(context.svn_cache),
        }

        assert all(isdir(d) for d in itervalues(cache_dirs))

        # --json flag is regression test for #5451
        run_command(Commands.CLEAN, '', "--source-cache --yes  --json")

        assert not all(isdir(d) for d in itervalues(cache_dirs))

    def test_install_mkdir(self):
        try:
            prefix = make_temp_prefix()
            assert isdir(prefix)
            run_command(Commands.INSTALL, prefix, "python=3.5.2", "--mkdir")
            assert_package_is_installed(prefix, "python-3.5.2")

            rm_rf(prefix)
            assert not isdir(prefix)

            # this part also a regression test for #4849
            run_command(Commands.INSTALL, prefix, "python-dateutil=2.6.0", "python=3.5.2", "--mkdir")
            assert_package_is_installed(prefix, "python-3.5.2")
            assert_package_is_installed(prefix, "python-dateutil-2.6.0")

        finally:
            rmtree(prefix, ignore_errors=True)

    def test_force_remove(self):
        prefix = make_temp_prefix("_" + str(uuid4())[:7])
        with make_temp_env(prefix=prefix):
            stdout, stderr = run_command(Commands.INSTALL, prefix, "conda")
            assert_package_is_installed(prefix, "conda-")
            assert_package_is_installed(prefix, "pycosat-")

            self.assertRaises(RemoveError, run_command, Commands.REMOVE, prefix, 'conda')
            assert_package_is_installed(prefix, "conda-")
            assert_package_is_installed(prefix, "pycosat-")

            stdout, stderr = run_command(Commands.REMOVE, prefix, "conda", "--force")

            # assert conda is no longer in conda list
            stdout, stderr = run_command(Commands.LIST, prefix)
            stdout_lines = stdout.split('\n')
            assert not any([line.startswith("conda   ") for line in stdout_lines])

            assert package_is_installed(prefix, "pycosat-")

    def test_transactional_rollback_simple(self):
        from conda.core.path_actions import CreateLinkedPackageRecordAction
        with patch.object(CreateLinkedPackageRecordAction, 'execute') as mock_method:
            with make_temp_env() as prefix:
                mock_method.side_effect = KeyError('Bang bang!!')
                with pytest.raises(CondaMultiError):
                    run_command(Commands.INSTALL, prefix, 'openssl')
                assert not package_is_installed(prefix, 'openssl')

    def test_transactional_rollback_upgrade_downgrade(self):
        with make_temp_env("python=3.5") as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            assert_package_is_installed(prefix, 'python-3')

            run_command(Commands.INSTALL, prefix, 'flask=0.10.1')
            assert_package_is_installed(prefix, 'flask-0.10.1')

            from conda.core.path_actions import CreateLinkedPackageRecordAction
            with patch.object(CreateLinkedPackageRecordAction, 'execute') as mock_method:
                mock_method.side_effect = KeyError('Bang bang!!')
                with pytest.raises(CondaMultiError):
                    run_command(Commands.INSTALL, prefix, 'flask=0.11.1')
                assert_package_is_installed(prefix, 'flask-0.10.1')

    def test_conda_downgrade(self):
        # Create an environment with the current conda under test, but include an earlier
        # version of conda and other packages in that environment.
        # Make sure we can flip back and forth.
        conda_exe = join('Scripts', 'conda.exe') if on_win else join('bin', 'conda')
        with env_var("CONDA_AUTO_UPDATE_CONDA", "false", reset_context):
            with make_temp_env("conda=4.3.27 python=%s" % sys.version_info[0],
                               name='_' + str(uuid4())[:8]) as prefix:  # rev 0
                assert package_is_installed(prefix, "conda")

                run_command(Commands.INSTALL, prefix, "mccabe")  # rev 1
                assert package_is_installed(prefix, "mccabe")

                subprocess_call("%s install -p %s -y itsdangerous" % (join(prefix, conda_exe), prefix))  # rev 2
                linked_data_.clear()
                assert package_is_installed(prefix, "itsdangerous")

                run_command(Commands.INSTALL, prefix, "lockfile")  # rev 3
                assert package_is_installed(prefix, "lockfile")

                subprocess_call("%s install -p %s -y conda=4.3" % (join(prefix, conda_exe), prefix))  # rev 4
                linked_data_.clear()
                assert not package_is_installed(prefix, "conda-4.3.27")

                subprocess_call("%s install -p %s -y colorama" % (join(prefix, conda_exe), prefix))  # rev 5
                linked_data_.clear()
                assert package_is_installed(prefix, "colorama")

                stdout, stderr = run_command(Commands.LIST, prefix, "--revisions")
                print(stdout)

                run_command(Commands.INSTALL, prefix, "--rev 3")
                linked_data_.clear()
                assert package_is_installed(prefix, "conda-4.3.27")
                assert not package_is_installed(prefix, "colorama")

                subprocess_call("%s install -y -p %s --rev 1" % (join(prefix, conda_exe), prefix))
                linked_data_.clear()
                assert not package_is_installed(prefix, "itsdangerous")
                linked_data_.clear()
                assert package_is_installed(prefix, "conda-4.3.27")
                assert package_is_installed(prefix, "python-%s" % sys.version_info[0])

                result = subprocess_call("%s info --json" % join(prefix, conda_exe))
                conda_info = json.loads(result.stdout)
                assert conda_info["conda_version"] == "4.3.27"

    @pytest.mark.skipif(on_win, reason="openssl only has a postlink script on unix")
    def test_run_script_called(self):
        import conda.core.link
        with patch.object(conda.core.link, 'subprocess_call') as rs:
            with make_temp_env("openssl=1.0.2j --no-deps") as prefix:
                assert_package_is_installed(prefix, 'openssl-')
                assert rs.call_count == 1

    def test_conda_info_python(self):
        stdout, stderr = run_command(Commands.INFO, None, "python=3.5")
        assert "python 3.5.1 0" in stdout

    def test_toolz_cytoolz_package_cache_regression(self):
        with make_temp_env("python=3.5") as prefix:
            pkgs_dir = join(prefix, 'pkgs')
            with env_var('CONDA_PKGS_DIRS', pkgs_dir, reset_context):
                assert context.pkgs_dirs == (pkgs_dir,)
                run_command(Commands.INSTALL, prefix, "-c conda-forge toolz cytoolz")
                assert_package_is_installed(prefix, 'toolz-')

    def test_remove_spellcheck(self):
        with make_temp_env("numpy=1.12") as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            assert_package_is_installed(prefix, 'numpy')

            with pytest.raises(PackageNotFoundError) as exc:
                run_command(Commands.REMOVE, prefix, 'numpi')

            exc_string = '%r' % exc.value
            assert exc_string.strip() == """PackageNotFoundError: Package(s) is missing from the environment:
            numpi """.strip()
            assert_package_is_installed(prefix, 'numpy')


    def test_conda_list_json(self):
        def pkg_info(s):
            # function from nb_conda/envmanager.py
            if hasattr(s, 'rsplit'):  # proxy for isinstance(s, six.string_types)
                name, version, build = s.rsplit('-', 2)
                return {
                    'name': name,
                    'version': version,
                    'build': build
                }
            else:
                return {
                    'name': s['name'],
                    'version': s['version'],
                    'build': s.get('build_string') or s['build']
                }

        with make_temp_env("python=3.5.2") as prefix:
            stdout, stderr = run_command(Commands.LIST, prefix, '--json')
            stdout_json = json.loads(stdout)
            packages = [pkg_info(package) for package in stdout_json]
            python_package = next((p for p in packages if p['name'] == 'python'), None)
            assert python_package['version'] == '3.5.2'
