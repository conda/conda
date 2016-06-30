# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import json
import os
import sys
import bz2
from contextlib import contextmanager
from glob import glob
from logging import getLogger, Handler
from os.path import exists, isdir, isfile, join, relpath, basename
from shlex import split
from shutil import rmtree, copyfile
from subprocess import check_call, Popen, PIPE
from tempfile import gettempdir
from unittest import TestCase
from uuid import uuid4
from json import loads as json_loads

import pytest
from requests import Session
from requests.adapters import BaseAdapter

from conda import config
from conda.cli import conda_argparse
from conda.cli.main_config import configure_parser as config_configure_parser
from conda.cli.main_create import configure_parser as create_configure_parser
from conda.cli.main_install import configure_parser as install_configure_parser
from conda.cli.main_list import configure_parser as list_configure_parser
from conda.cli.main_remove import configure_parser as remove_configure_parser
from conda.cli.main_search import configure_parser as search_configure_parser
from conda.cli.main_update import configure_parser as update_configure_parser
from conda.compat import PY3, TemporaryDirectory, itervalues
from conda.config import bits, subdir
from conda.connection import LocalFSAdapter
from conda.install import linked as install_linked, linked_data_, dist2dirname, package_cache
from conda.install import on_win, linked_data
from conda.utils import url_path
from tests.helpers import captured

log = getLogger(__name__)
PYTHON_BINARY = 'python.exe' if on_win else 'bin/python'


def escape_for_winpath(p):
    return p.replace('\\', '\\\\')


def make_temp_prefix():
    tempdir = gettempdir()
    dirname = str(uuid4())[:8]
    prefix = join(tempdir, dirname)
    if exists(prefix):
        # rm here because create complains if directory exists
        rmtree(prefix)
    assert isdir(tempdir)
    return prefix


def disable_dotlog():
    class NullHandler(Handler):
        def emit(self, record):
            pass
    dotlogger = getLogger('dotupdate')
    saved_handlers = dotlogger.handlers
    dotlogger.handlers = []
    dotlogger.addHandler(NullHandler())
    return saved_handlers


def reenable_dotlog(handlers):
    dotlogger = getLogger('dotupdate')
    dotlogger.handlers = handlers


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


def run_command(command, prefix, *arguments):
    p = conda_argparse.ArgumentParser()
    sub_parsers = p.add_subparsers(metavar='command', dest='cmd')
    parser_config[command](sub_parsers)

    prefix = escape_for_winpath(prefix)
    arguments = list(map(escape_for_winpath, arguments))
    if command is Commands.CONFIG:
        command_line = "{0} --file {1} {2}".format(command, join(prefix, 'condarc'), " ".join(arguments))
    elif command is Commands.SEARCH:
        command_line = "{0} {1}".format(command, " ".join(arguments))
    elif command is Commands.LIST:
        command_line = "{0} -p {1} {2}".format(command, prefix, " ".join(arguments))
    else:  # CREATE, INSTALL, REMOVE, UPDATE
        command_line = "{0} -y -q -p {1} {2}".format(command, prefix, " ".join(arguments))

    args = p.parse_args(split(command_line))
    with captured(disallow_stderr=False) as c:
        args.func(args, p)
    print(c.stdout)
    print(c.stderr, file=sys.stderr)
    if command is Commands.CONFIG:
        reload_config(prefix)
    return c.stdout, c.stderr


@contextmanager
def make_temp_env(*packages):
    prefix = make_temp_prefix()
    prefix_condarc = join(prefix, 'condarc')
    try:
        # try to clear any config that's been set by other tests
        if packages:
            config.load_condarc(prefix_condarc)
            run_command(Commands.CREATE, prefix, *packages)
        yield prefix
    finally:
        rmtree(prefix, ignore_errors=True)


def reload_config(prefix):
    prefix_condarc = join(prefix, 'condarc')
    config.load_condarc(prefix_condarc)


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

    def setUp(self):
        self.saved_dotlog_handlers = disable_dotlog()

    def tearDown(self):
        reenable_dotlog(self.saved_dotlog_handlers)

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

    @pytest.mark.timeout(300)
    def test_tarball_install_and_bad_metadata(self):
        with make_temp_env("python flask=0.10.1") as prefix:
            assert_package_is_installed(prefix, 'flask-0.10.1')
            flask_data = [p for p in itervalues(linked_data(prefix)) if p['name'] == 'flask'][0]
            run_command(Commands.REMOVE, prefix, 'flask')
            assert not package_is_installed(prefix, 'flask-0.10.1')
            assert_package_is_installed(prefix, 'python')

            from conda.config import pkgs_dirs
            flask_fname = flask_data['fn']
            tar_old_path = join(pkgs_dirs[0], flask_fname)

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

            # Regression test for 2812
            # install from local channel
            for field in ('url', 'channel', 'schannel'):
                del flask_data[field]
            repodata = {'info': {}, 'packages':{flask_fname: flask_data}}
            with make_temp_env() as channel:
                subchan = join(channel, subdir)
                channel = url_path(channel)
                os.makedirs(subchan)
                tar_new_path = join(subchan, flask_fname)
                copyfile(tar_old_path, tar_new_path)
                with bz2.BZ2File(join(subchan, 'repodata.json.bz2'), 'w') as f:
                    f.write(json.dumps(repodata).encode('utf-8'))
                run_command(Commands.INSTALL, prefix, '-c', channel, 'flask')
                assert_package_is_installed(prefix, channel + '::' + 'flask-')

            # regression test for #2886 (part 2 of 2)
            # install tarball from package cache, local channel
            run_command(Commands.REMOVE, prefix, 'flask')
            assert not package_is_installed(prefix, 'flask-0')
            run_command(Commands.INSTALL, prefix, tar_old_path)
            assert_package_is_installed(prefix, channel + '::' + 'flask-')

            # regression test for #2599
            linked_data_.clear()
            flask_metadata = glob(join(prefix, 'conda-meta', flask_fname[:-8] + '.json'))[-1]
            bad_metadata = join(prefix, 'conda-meta', 'flask.json')
            copyfile(flask_metadata, bad_metadata)
            assert not package_is_installed(prefix, 'flask', exact=True)
            assert_package_is_installed(prefix, 'flask-0.')

    @pytest.mark.timeout(600)
    def test_install_python2(self):
        with make_temp_env("python=2") as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            assert_package_is_installed(prefix, 'python-2')

    @pytest.mark.timeout(300)
    def test_remove_all(self):
        with make_temp_env("python=2") as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            assert_package_is_installed(prefix, 'python-2')

            run_command(Commands.REMOVE, prefix, '--all')
            assert not exists(prefix)

    @pytest.mark.skipif(on_win and bits == 32, reason="no 32-bit windows python on conda-forge")
    @pytest.mark.xfail(reason="pending resolution of #2926")
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

    @pytest.mark.skipif(on_win, reason="r packages aren't prime-time on windows just yet")
    @pytest.mark.timeout(600)
    def test_clone_offline_multichannel_with_untracked(self):
        with make_temp_env("python") as prefix:
            assert_package_is_installed(prefix, 'python')
            from conda.config import get_rc_urls
            assert 'r' not in get_rc_urls()

            # assert conda search cannot find rpy2
            stdout, stderr = run_command(Commands.SEARCH, prefix, "rpy2", "--json")
            json_obj = json_loads(stdout.replace("Fetching package metadata ...", "").strip())
            assert bool(json_obj) is False

            run_command(Commands.CONFIG, prefix, "--add channels r")

            # assert conda search cannot find rpy2
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


@pytest.mark.skipif(not on_win, reason="shortcuts only relevant on Windows")
def test_shortcut_in_underscore_env_shows_message():
    with TemporaryDirectory() as tmp:
        cmd = ["conda", "create", '-y', '--shortcuts', '-p', join(tmp, '_conda'), "console_shortcut"]
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        output, error = p.communicate()
        if PY3:
            error = error.decode("UTF-8")
        assert "Environment name starts with underscore '_'.  Skipping menu installation." in error


@pytest.mark.skipif(not on_win, reason="shortcuts only relevant on Windows")
def test_shortcut_not_attempted_without_shortcuts_arg():
    with TemporaryDirectory() as tmp:
        cmd = ["conda", "create", '-y', '-p', join(tmp, '_conda'), "console_shortcut"]
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        output, error = p.communicate()
        if PY3:
            error = error.decode("UTF-8")
        # This test is sufficient, because it effectively verifies that the code
        #  path was not visited.
        assert "Environment name starts with underscore '_'.  Skipping menu installation." not in error


@pytest.mark.skipif(not on_win, reason="shortcuts only relevant on Windows")
def test_shortcut_creation_installs_shortcut():
    from menuinst.win32 import dirs as win_locations
    with TemporaryDirectory() as tmp:
        check_call(["conda", "create", '-y', '--shortcuts', '-p',
                    join(tmp, 'conda'), "console_shortcut"])

        user_mode = 'user' if exists(join(sys.prefix, u'.nonadmin')) else 'system'
        shortcut_dir = win_locations[user_mode]["start"]
        shortcut_dir = join(shortcut_dir, "Anaconda{} ({}-bit)".format(sys.version_info.major, config.bits))
        shortcut_file = join(shortcut_dir, "Anaconda Prompt (conda).lnk")

        try:
            assert isfile(shortcut_file)
        except AssertionError:
            print("Shortcut not found in menu dir.  Contents of dir:")
            print(os.listdir(shortcut_dir))
            raise

        # make sure that cleanup without specifying --shortcuts still removes shortcuts
        check_call(["conda", "remove", '-y', '-p', join(tmp, 'conda'), "console_shortcut"])
        try:
            assert not isfile(shortcut_file)
        finally:
            if isfile(shortcut_file):
                os.remove(shortcut_file)


@pytest.mark.skipif(not on_win, reason="shortcuts only relevant on Windows")
def test_shortcut_absent_does_not_barf_on_uninstall():
    from menuinst.win32 import dirs as win_locations

    user_mode = 'user' if exists(join(sys.prefix, u'.nonadmin')) else 'system'
    shortcut_dir = win_locations[user_mode]["start"]
    shortcut_dir = join(shortcut_dir, "Anaconda{} ({}-bit)".format(sys.version_info.major, config.bits))
    shortcut_file = join(shortcut_dir, "Anaconda Prompt (conda).lnk")

    # kill shortcut from any other misbehaving test
    if isfile(shortcut_file):
        os.remove(shortcut_file)

    assert not isfile(shortcut_file)

    with TemporaryDirectory() as tmp:
        # not including --shortcuts, should not get shortcuts installed
        check_call(["conda", "create", '-y', '-p', join(tmp, 'conda'), "console_shortcut"])

        # make sure it didn't get created
        assert not isfile(shortcut_file)

        # make sure that cleanup does not barf trying to remove non-existent shortcuts
        check_call(["conda", "remove", '-y', '-p', join(tmp, 'conda'), "console_shortcut"])


def test_symlinks_created_with_env():
    bindir = 'Scripts' if on_win else 'bin'

    with TemporaryDirectory() as tmp:
        check_call(["conda", "create", '-y', '-p', join(tmp, 'conda'), "python=2.7"])
        assert isfile(join(tmp, 'conda', bindir, 'activate'))
        assert isfile(join(tmp, 'conda', bindir, 'deactivate'))
        assert isfile(join(tmp, 'conda', bindir, 'conda'))
        if on_win:
            assert isfile(join(tmp, 'conda', bindir, 'activate.bat'))
            assert isfile(join(tmp, 'conda', bindir, 'deactivate.bat'))
            assert isfile(join(tmp, 'conda', bindir, 'conda.bat'))
