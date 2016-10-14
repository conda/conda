# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import bz2
import json
import os
import pytest
import requests
import sys
from conda import CondaError, plan
from conda.base.context import context, reset_context
from conda.cli.common import get_index_trap
from conda.cli.main import generate_parser
from conda.cli.main_config import configure_parser as config_configure_parser
from conda.cli.main_create import configure_parser as create_configure_parser
from conda.cli.main_install import configure_parser as install_configure_parser
from conda.cli.main_list import configure_parser as list_configure_parser
from conda.cli.main_remove import configure_parser as remove_configure_parser
from conda.cli.main_search import configure_parser as search_configure_parser
from conda.cli.main_update import configure_parser as update_configure_parser
from conda.common.io import captured, disable_logger, stderr_log_level, replace_log_streams
from conda.common.url import path_to_url
from conda.common.yaml import yaml_load
from conda.compat import itervalues
from conda.connection import LocalFSAdapter
from conda.exceptions import DryRunExit, conda_exception_handler, CondaHTTPError
from conda.install import dist2dirname, linked as install_linked, linked_data, linked_data_, on_win
from contextlib import contextmanager
from datetime import datetime
from glob import glob
from json import loads as json_loads
from logging import DEBUG, getLogger
from os.path import basename, exists, isdir, isfile, islink, join, relpath
from requests import Session
from requests.adapters import BaseAdapter
from shlex import split
from shutil import copyfile, rmtree
from subprocess import check_call
from tempfile import gettempdir
from unittest import TestCase
from uuid import uuid4

log = getLogger(__name__)
PYTHON_BINARY = 'python.exe' if on_win else 'bin/python'
BIN_DIRECTORY = 'Scripts' if on_win else 'bin'


def escape_for_winpath(p):
    return p.replace('\\', '\\\\')


def make_temp_prefix(name=None, create_directory=True):
    tempdir = gettempdir()
    dirname = str(uuid4())[:8] if name is None else name
    prefix = join(tempdir, dirname)
    os.makedirs(prefix)
    if create_directory:
        assert isdir(prefix)
    else:
        os.removedirs(prefix)
    return prefix


class Commands:
    CONFIG = "config"
    CREATE = "create"
    INSTALL = "install"
    LIST = "list"
    REMOVE = "remove"
    SEARCH = "search"
    UPDATE = "update"


parser_config = {
    Commands.CONFIG: config_configure_parser,
    Commands.CREATE: create_configure_parser,
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
        arguments.append("--file {0}".format(join(prefix, 'condarc')))
    if command in (Commands.LIST, Commands.CREATE, Commands.INSTALL,
                   Commands.REMOVE, Commands.UPDATE):
        arguments.append("-p {0}".format(prefix))
    if command in (Commands.CREATE, Commands.INSTALL, Commands.REMOVE, Commands.UPDATE):
        arguments.extend(["-y", "-q"])

    arguments = list(map(escape_for_winpath, arguments))
    command_line = "{0} {1}".format(command, " ".join(arguments))

    args = p.parse_args(split(command_line))
    context._add_argparse_args(args)
    print("executing command >>>", command_line)
    with captured() as c, replace_log_streams():
        if use_exception_handler:
            conda_exception_handler(args.func, args, p)
        else:
            args.func(args, p)
    print(c.stderr, file=sys.stderr)
    print(c.stdout)
    if command is Commands.CONFIG:
        reload_config(prefix)
    return c.stdout, c.stderr


@contextmanager
def make_temp_env(*packages, **kwargs):
    prefix = kwargs.pop('prefix', None) or make_temp_prefix()
    assert isdir(prefix), prefix
    with stderr_log_level(DEBUG, 'conda'), stderr_log_level(DEBUG, 'requests'):
        with disable_logger('fetch'), disable_logger('dotupdate'):
            try:
                # try to clear any config that's been set by other tests
                reset_context([os.path.join(prefix+os.sep, 'condarc')])
                run_command(Commands.CREATE, prefix, *packages)
                yield prefix
            finally:
                rmtree(prefix, ignore_errors=True)


def reload_config(prefix):
    prefix_condarc = join(prefix+os.sep, 'condarc')
    reset_context([prefix_condarc])


class EnforceUnusedAdapter(BaseAdapter):

    def send(self, request, *args, **kwargs):
        raise RuntimeError("EnforceUnusedAdapter called with url {0}".format(request.url))


class OfflineCondaSession(Session):

    timeout = None

    def __init__(self, *args, **kwargs):
        super(OfflineCondaSession, self).__init__()
        unused_adapter = EnforceUnusedAdapter()
        self.mount("http://", unused_adapter)
        self.mount("https://", unused_adapter)
        self.mount("ftp://", unused_adapter)
        self.mount("s3://", unused_adapter)

        # Enable file:// urls
        self.mount("file://", LocalFSAdapter())


@contextmanager
def enforce_offline():
    class NadaCondaSession(object):
        def __init__(self, *args, **kwargs):
            pass
    import conda.connection
    saved_conda_session = conda.connection.CondaSession
    try:
        conda.connection.CondaSession = OfflineCondaSession
        yield
    finally:
        conda.connection.CondaSession = saved_conda_session


def package_is_installed(prefix, package, exact=False):
    packages = list(install_linked(prefix))
    if '::' not in package:
        packages = list(map(dist2dirname, packages))
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


class IntegrationTests(TestCase):

    @pytest.mark.timeout(900)
    def test_create_install_update_remove(self):
        with make_temp_env("python=3") as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            assert_package_is_installed(prefix, 'python-3')

            run_command(Commands.INSTALL, prefix, 'flask=0.10')
            assert_package_is_installed(prefix, 'flask-0.10.1')

            # Test force reinstall
            run_command(Commands.INSTALL, prefix, '--force', 'flask=0.10')
            assert_package_is_installed(prefix, 'flask-0.10.1')

            run_command(Commands.UPDATE, prefix, 'flask')
            assert not package_is_installed(prefix, 'flask-0.10.1')
            assert_package_is_installed(prefix, 'flask')

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

    @pytest.mark.timeout(300)
    def test_create_empty_env(self):
        with make_temp_env() as prefix:
            assert exists(join(prefix, BIN_DIRECTORY))
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

    @pytest.mark.timeout(300)
    def test_list_with_pip_egg(self):
        with make_temp_env("python=3 pip") as prefix:
            check_call(PYTHON_BINARY + " -m pip install --egg --no-binary flask flask==0.10.1",
                       cwd=prefix, shell=True)
            stdout, stderr = run_command(Commands.LIST, prefix)
            stdout_lines = stdout.split('\n')
            assert any(line.endswith("<pip>") for line in stdout_lines
                       if line.lower().startswith("flask"))

    @pytest.mark.timeout(300)
    def test_list_with_pip_wheel(self):
        with make_temp_env("python=3 pip") as prefix:
            check_call(PYTHON_BINARY + " -m pip install flask==0.10.1",
                       cwd=prefix, shell=True)
            stdout, stderr = run_command(Commands.LIST, prefix)
            stdout_lines = stdout.split('\n')
            assert any(line.endswith("<pip>") for line in stdout_lines
                       if line.lower().startswith("flask"))

            # regression test for #3433
            run_command(Commands.INSTALL, prefix, "python=3.4")
            assert_package_is_installed(prefix, 'python-3.4.')

    @pytest.mark.timeout(300)
    def test_install_tarball_from_local_channel(self):
        with make_temp_env("python flask=0.10.1") as prefix:
            assert_package_is_installed(prefix, 'flask-0.10.1')
            flask_data = [p for p in itervalues(linked_data(prefix)) if p['name'] == 'flask'][0]
            run_command(Commands.REMOVE, prefix, 'flask')
            assert not package_is_installed(prefix, 'flask-0.10.1')
            assert_package_is_installed(prefix, 'python')

            flask_fname = flask_data['fn']
            tar_old_path = join(context.pkgs_dirs[0], flask_fname)

            # Regression test for #2812
            # install from local channel
            for field in ('url', 'channel', 'schannel'):
                del flask_data[field]
            repodata = {'info': {}, 'packages': {flask_fname: flask_data}}
            with make_temp_env() as channel:
                subchan = join(channel, context.subdir)
                channel = path_to_url(channel)
                os.makedirs(subchan)
                tar_new_path = join(subchan, flask_fname)
                copyfile(tar_old_path, tar_new_path)
                with bz2.BZ2File(join(subchan, 'repodata.json.bz2'), 'w') as f:
                    f.write(json.dumps(repodata).encode('utf-8'))
                run_command(Commands.INSTALL, prefix, '-c', channel, 'flask')
                assert_package_is_installed(prefix, channel + '::' + 'flask-')

                run_command(Commands.REMOVE, prefix, 'flask')
                assert not package_is_installed(prefix, 'flask-0')

                # Regression test for 2970
                # install from build channel as a tarball
                conda_bld = join(sys.prefix, 'conda-bld')
                conda_bld_sub = join(conda_bld, context.subdir)

                tar_bld_path = join(conda_bld_sub, flask_fname)
                if os.path.exists(conda_bld):
                    try:
                        os.rename(tar_new_path, tar_bld_path)
                    except OSError:
                        pass
                else:
                    os.makedirs(conda_bld)
                    os.rename(subchan, conda_bld_sub)
                run_command(Commands.INSTALL, prefix, tar_bld_path)
                assert_package_is_installed(prefix, 'flask-')

    @pytest.mark.timeout(300)
    def test_tarball_install_and_bad_metadata(self):
        with make_temp_env("python flask=0.10.1") as prefix:
            assert_package_is_installed(prefix, 'flask-0.10.1')
            flask_data = [p for p in itervalues(linked_data(prefix)) if p['name'] == 'flask'][0]
            run_command(Commands.REMOVE, prefix, 'flask')
            assert not package_is_installed(prefix, 'flask-0.10.1')
            assert_package_is_installed(prefix, 'python')

            flask_fname = flask_data['fn']
            tar_old_path = join(context.pkgs_dirs[0], flask_fname)

            # regression test for #2886 (part 1 of 2)
            # install tarball from package cache, default channel
            run_command(Commands.INSTALL, prefix, tar_old_path)
            assert_package_is_installed(prefix, 'flask-0.')

            # regression test for #2626
            # install tarball with full path, outside channel
            tar_new_path = join(prefix, flask_fname)
            copyfile(tar_old_path, tar_new_path)
            run_command(Commands.INSTALL, prefix, tar_new_path)
            assert_package_is_installed(prefix, 'flask-0')

            # regression test for #2626
            # install tarball with relative path, outside channel
            run_command(Commands.REMOVE, prefix, 'flask')
            assert not package_is_installed(prefix, 'flask-0.10.1')
            tar_new_path = relpath(tar_new_path)
            run_command(Commands.INSTALL, prefix, tar_new_path)
            assert_package_is_installed(prefix, 'flask-0.')

            # regression test for #2886 (part 2 of 2)
            # install tarball from package cache, local channel
            run_command(Commands.REMOVE, prefix, 'flask')
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

    @pytest.mark.timeout(600)
    def test_install_python2_and_env_symlinks(self):
        with make_temp_env("python=2") as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            assert_package_is_installed(prefix, 'python-2')

            # test symlinks created with env
            print(os.listdir(join(prefix, BIN_DIRECTORY)))
            if on_win:
                assert isfile(join(prefix, BIN_DIRECTORY, 'activate'))
                assert isfile(join(prefix, BIN_DIRECTORY, 'deactivate'))
                assert isfile(join(prefix, BIN_DIRECTORY, 'conda'))
                assert isfile(join(prefix, BIN_DIRECTORY, 'activate.bat'))
                assert isfile(join(prefix, BIN_DIRECTORY, 'deactivate.bat'))
                assert isfile(join(prefix, BIN_DIRECTORY, 'conda.bat'))
            else:
                assert islink(join(prefix, BIN_DIRECTORY, 'activate'))
                assert islink(join(prefix, BIN_DIRECTORY, 'deactivate'))
                assert islink(join(prefix, BIN_DIRECTORY, 'conda'))

    @pytest.mark.timeout(300)
    def test_remove_all(self):
        with make_temp_env("python=2") as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            assert_package_is_installed(prefix, 'python-2')

            run_command(Commands.REMOVE, prefix, '--all')
            assert not exists(prefix)

    @pytest.mark.skipif(on_win and context.bits == 32, reason="no 32-bit windows python on conda-forge")
    @pytest.mark.timeout(600)
    def test_dash_c_usage_replacing_python(self):
        # Regression test for #2606
        with make_temp_env("-c conda-forge python=3.5") as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            run_command(Commands.INSTALL, prefix, "decorator")
            assert_package_is_installed(prefix, 'conda-forge::python-3.5')

            with make_temp_env("--clone", prefix) as clone_prefix:
                assert_package_is_installed(clone_prefix, 'conda-forge::python-3.5')
                assert_package_is_installed(clone_prefix, "decorator")

            # Regression test for 2645
            fn = glob(join(prefix, 'conda-meta', 'python-3.5*.json'))[-1]
            with open(fn) as f:
                data = json.load(f)
            for field in ('url', 'channel', 'schannel'):
                if field in data:
                    del data[field]
            with open(fn, 'w') as f:
                json.dump(data, f)
            linked_data_.clear()

            with make_temp_env("-c conda-forge --clone", prefix) as clone_prefix:
                assert_package_is_installed(clone_prefix, 'python-3.5')
                assert_package_is_installed(clone_prefix, 'decorator')

    @pytest.mark.timeout(600)
    def test_python2_pandas(self):
        with make_temp_env("python=2 pandas") as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            assert_package_is_installed(prefix, 'numpy')

    @pytest.mark.timeout(300)
    def test_install_prune(self):
        with make_temp_env("python=2 decorator") as prefix:
            assert_package_is_installed(prefix, 'decorator')

            # prune is a feature used by conda-env
            # conda itself does not provide a public API for it
            index = get_index_trap(prefix=prefix)
            actions = plan.install_actions(prefix,
                                           index,
                                           specs=['flask'],
                                           prune=True)
            plan.execute_actions(actions, index, verbose=True)

            assert_package_is_installed(prefix, 'flask')
            assert not package_is_installed(prefix, 'decorator')

    @pytest.mark.skipif(on_win, reason="mkl package not available on Windows")
    @pytest.mark.timeout(300)
    def test_install_features(self):
        with make_temp_env("python=2 numpy") as prefix:
            numpy_details = get_conda_list_tuple(prefix, "numpy")
            assert len(numpy_details) == 3 or 'nomkl' not in numpy_details[3]

            run_command(Commands.INSTALL, prefix, "nomkl")
            numpy_details = get_conda_list_tuple(prefix, "numpy")
            assert len(numpy_details) == 4 and 'nomkl' in numpy_details[3]

    @pytest.mark.timeout(300)
    def test_clone_offline(self):
        with make_temp_env("python flask=0.10.1") as prefix:
            assert_package_is_installed(prefix, 'flask-0.10.1')
            assert_package_is_installed(prefix, 'python')

            with enforce_offline():
                with make_temp_env("--clone", prefix, "--offline") as clone_prefix:
                    assert_package_is_installed(clone_prefix, 'flask-0.10.1')
                    assert_package_is_installed(clone_prefix, 'python')

    @pytest.mark.xfail(datetime.now() < datetime(2016, 11, 1), reason="configs are borked")
    @pytest.mark.skipif(on_win, reason="r packages aren't prime-time on windows just yet")
    @pytest.mark.timeout(600)
    def test_clone_offline_multichannel_with_untracked(self):
        with make_temp_env("python") as prefix:
            assert_package_is_installed(prefix, 'python')
            assert 'r' not in context.channels

            # assert conda search cannot find rpy2
            stdout, stderr = run_command(Commands.SEARCH, prefix, "rpy2", "--json")
            json_obj = json_loads(stdout.replace("Fetching package metadata ...", "").strip())
            assert bool(json_obj) is False

            # add r channel
            run_command(Commands.CONFIG, prefix, "--add channels r")
            stdout, stderr = run_command(Commands.CONFIG, prefix, "--get", "--json")
            json_obj = json_loads(stdout)
            assert json_obj['rc_path'] == join(prefix, 'condarc')
            assert json_obj['get']['channels']

            # assert conda search can now find rpy2
            stdout, stderr = run_command(Commands.SEARCH, prefix, "rpy2", "--json")
            json_obj = json_loads(stdout.replace("Fetching package metadata ...", "").strip())
            assert len(json_obj['rpy2']) > 1

            run_command(Commands.INSTALL, prefix, "rpy2")
            assert_package_is_installed(prefix, 'rpy2')
            run_command(Commands.LIST, prefix)

            with enforce_offline():
                with make_temp_env("--clone", prefix, "--offline") as clone_prefix:
                    assert_package_is_installed(clone_prefix, 'python')
                    assert_package_is_installed(clone_prefix, 'rpy2')
                    assert isfile(join(clone_prefix, 'condarc'))  # untracked file

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
        with make_temp_env(prefix=prefix):
            stdout, stderr = run_command(Commands.INSTALL, prefix, "console_shortcut",
                                         "--no-shortcuts")
            # This test is sufficient, because it effectively verifies that the code
            #  path was not visited.
            assert ("Environment name starts with underscore '_'.  Skipping menu installation."
                    not in stderr)

    @pytest.mark.skipif(not on_win, reason="shortcuts only relevant on Windows")
    def test_shortcut_creation_installs_shortcut(self):
        from menuinst.win32 import dirs as win_locations
        user_mode = 'user' if exists(join(sys.prefix, u'.nonadmin')) else 'system'
        shortcut_dir = win_locations[user_mode]["start"]
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
        from menuinst.win32 import dirs as win_locations

        user_mode = 'user' if exists(join(sys.prefix, u'.nonadmin')) else 'system'
        shortcut_dir = win_locations[user_mode]["start"]
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
    @pytest.mark.xfail(datetime.now() < datetime(2016, 11, 1), reason="deal with this later")
    def test_shortcut_absent_when_condarc_set(self):
        from menuinst.win32 import dirs as win_locations
        user_mode = 'user' if exists(join(sys.prefix, u'.nonadmin')) else 'system'
        shortcut_dir = win_locations[user_mode]["start"]
        shortcut_dir = join(shortcut_dir, "Anaconda{0} ({1}-bit)"
                                          "".format(sys.version_info.major, context.bits))

        prefix = make_temp_prefix(str(uuid4())[:7])
        shortcut_file = join(shortcut_dir, "Anaconda Prompt ({0}).lnk".format(basename(prefix)))
        assert not isfile(shortcut_file)

        # set condarc shortcuts: False
        run_command(Commands.CONFIG, prefix, "--set shortcuts false")
        stdout, stderr = run_command(Commands.CONFIG, prefix, "--get", "--json")
        json_obj = json_loads(stdout)
        # assert json_obj['rc_path'] == join(prefix, 'condarc')
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
            run_command(Commands.CONFIG, prefix, "--add create_default_packages python")
            run_command(Commands.CONFIG, prefix, "--add create_default_packages pip")
            run_command(Commands.CONFIG, prefix, "--add create_default_packages flask")
            stdout, stderr = run_command(Commands.CONFIG, prefix, "--show")
            yml_obj = yaml_load(stdout)
            assert yml_obj['create_default_packages'] == ['flask', 'pip', 'python']

            assert not package_is_installed(prefix, 'python-2')
            assert not package_is_installed(prefix, 'numpy')
            assert not package_is_installed(prefix, 'flask')

            with make_temp_env("python=2", "numpy", prefix=prefix):
                assert_package_is_installed(prefix, 'python-2')
                assert_package_is_installed(prefix, 'numpy')
                assert_package_is_installed(prefix, 'flask')

        finally:
            rmtree(prefix, ignore_errors=True)

    def test_create_default_packages_no_default_packages(self):
        try:
            prefix = make_temp_prefix(str(uuid4())[:7])

            # set packages
            run_command(Commands.CONFIG, prefix, "--add create_default_packages python")
            run_command(Commands.CONFIG, prefix, "--add create_default_packages pip")
            run_command(Commands.CONFIG, prefix, "--add create_default_packages flask")
            stdout, stderr = run_command(Commands.CONFIG, prefix, "--show")
            yml_obj = yaml_load(stdout)
            assert yml_obj['create_default_packages'] == ['flask', 'pip', 'python']

            assert not package_is_installed(prefix, 'python-2')
            assert not package_is_installed(prefix, 'numpy')
            assert not package_is_installed(prefix, 'flask')

            with make_temp_env("python=2", "numpy", "--no-default-packages", prefix=prefix):
                assert_package_is_installed(prefix, 'python-2')
                assert_package_is_installed(prefix, 'numpy')
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

    @pytest.mark.skipif(on_win, reason="gawk is a windows only package")
    def test_search_gawk_not_win(self):
        with make_temp_env() as prefix:
            stdout, stderr = run_command(Commands.SEARCH, prefix, "gawk", "--json")
            json_obj = json_loads(stdout.replace("Fetching package metadata ...", "").strip())
            assert len(json_obj.keys()) == 0

    @pytest.mark.skipif(on_win, reason="gawk is a windows only package")
    def test_search_gawk_not_win_filter(self):
        with make_temp_env() as prefix:
            stdout, stderr = run_command(
                Commands.SEARCH, prefix, "gawk", "--platform", "win-64", "--json")
            json_obj = json_loads(stdout.replace("Fetching package metadata ...", "").strip())
            assert "gawk" in json_obj.keys()
            assert "m2-gawk" in json_obj.keys()
            assert len(json_obj.keys()) == 2

    @pytest.mark.skipif(not on_win, reason="gawk is a windows only package")
    def test_search_gawk_on_win(self):
        with make_temp_env() as prefix:
            stdout, stderr = run_command(Commands.SEARCH, prefix, "gawk", "--json")
            json_obj = json_loads(stdout.replace("Fetching package metadata ...", "").strip())
            assert "gawk" in json_obj.keys()
            assert "m2-gawk" in json_obj.keys()
            assert len(json_obj.keys()) == 2

    @pytest.mark.skipif(not on_win, reason="gawk is a windows only package")
    def test_search_gawk_on_win_filter(self):
        with make_temp_env() as prefix:
            stdout, stderr = run_command(Commands.SEARCH, prefix, "gawk", "--platform",
                                         "linux-64", "--json")
            json_obj = json_loads(stdout.replace("Fetching package metadata ...", "").strip())
            assert len(json_obj.keys()) == 0

    @pytest.mark.timeout(30)
    def test_bad_anaconda_token_infinite_loop(self):
        # First, confirm we get a 401 UNAUTHORIZED response from anaconda.org
        response = requests.get("https://conda.anaconda.org/t/cqgccfm1mfma/data-portal/"
                                "%s/repodata.json" % context.subdir)
        assert response.status_code == 401

        try:
            prefix = make_temp_prefix(str(uuid4())[:7])
            channel_url = "https://conda.anaconda.org/t/cqgccfm1mfma/data-portal"
            run_command(Commands.CONFIG, prefix, "--add channels %s" % channel_url)
            stdout, stderr = run_command(Commands.CONFIG, prefix, "--show")
            yml_obj = yaml_load(stdout)
            assert yml_obj['channels'] == [channel_url, 'defaults']

            with pytest.raises(CondaHTTPError):
                run_command(Commands.SEARCH, prefix, "boltons", "--json")

            stdout, stderr = run_command(Commands.SEARCH, prefix, "boltons", "--json",
                                         use_exception_handler=True)
            json_obj = json.loads(stdout)
            assert json_obj['status_code'] == 401

        finally:
            rmtree(prefix, ignore_errors=True)

    def test_anaconda_token_with_private_package(self):
        "https://conda.anaconda.org/t/zlZvSlMGN7CB/kalefranz"
        # TODO: write test for anyjson once #3602 is merged and available
        # TODO: should also write a test to use binstar_client to set the token, then let conda load the token

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
                                         "linux-64", "--json")
            json_obj = json_loads(stdout)
            assert len(json_obj) == 0

        finally:
            rmtree(prefix, ignore_errors=True)

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
