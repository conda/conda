# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

from contextlib import contextmanager
from glob import glob
import json
from logging import getLogger, Handler
from os.path import exists, isdir, join, relpath
from shlex import split
from shutil import rmtree, copyfile
import subprocess
import sys
from tempfile import gettempdir
from unittest import TestCase
from uuid import uuid4

from menuinst.win32 import dirs as win_locations
import pytest

from conda import config
from conda.cli import conda_argparse
from conda.cli.main_create import configure_parser as create_configure_parser
from conda.cli.main_install import configure_parser as install_configure_parser
from conda.cli.main_remove import configure_parser as remove_configure_parser
from conda.cli.main_update import configure_parser as update_configure_parser
from conda.config import pkgs_dirs, bits
from conda.install import linked as install_linked, linked_data_
from conda.install import on_win
from conda.compat import PY3, TemporaryDirectory

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


@contextmanager
def make_temp_env(*packages):
    prefix = make_temp_prefix()
    try:
        # try to clear any config that's been set by other tests
        config.rc = config.load_condarc('')

        p = conda_argparse.ArgumentParser()
        sub_parsers = p.add_subparsers(metavar='command', dest='cmd')
        create_configure_parser(sub_parsers)

        command = "create -y -q -p {0} {1}".format(escape_for_winpath(prefix), " ".join(packages))

        args = p.parse_args(split(command))
        args.func(args, p)

        yield prefix
    finally:
        rmtree(prefix, ignore_errors=True)


class Commands:
    INSTALL = "install"
    UPDATE = "update"
    REMOVE = "remove"


parser_config = {
    Commands.INSTALL: install_configure_parser,
    Commands.UPDATE: update_configure_parser,
    Commands.REMOVE: remove_configure_parser,
}


def run_command(command, prefix, *arguments):
    p = conda_argparse.ArgumentParser()
    sub_parsers = p.add_subparsers(metavar='command', dest='cmd')
    parser_config[command](sub_parsers)

    command = "{0} -y -q -p {1} {2}".format(command,
                                            escape_for_winpath(prefix),
                                            " ".join(arguments))

    args = p.parse_args(split(command))
    args.func(args, p)


def package_is_installed(prefix, package, exact=False):
    if exact:
        return any(p == package for p in install_linked(prefix))
    return any(p.startswith(package) for p in install_linked(prefix))


def assert_package_is_installed(prefix, package, exact=False):
    if not package_is_installed(prefix, package, exact):
        print([p for p in install_linked(prefix)])
        raise AssertionError("package {0} is not in prefix".format(package))


class IntegrationTests(TestCase):

    def setUp(self):
        self.saved_dotlog_handlers = disable_dotlog()

    def tearDown(self):
        reenable_dotlog(self.saved_dotlog_handlers)

    @pytest.mark.skipif(on_win, reason="get windows passing")
    @pytest.mark.timeout(300)
    def test_python3(self):
        with make_temp_env("python=3") as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            assert_package_is_installed(prefix, 'python-3')

            run_command(Commands.INSTALL, prefix, 'flask=0.10')
            assert_package_is_installed(prefix, 'flask-0.10.1')

            run_command(Commands.UPDATE, prefix, 'flask')
            assert not package_is_installed(prefix, 'flask-0.10.1')
            assert_package_is_installed(prefix, 'flask')

            run_command(Commands.REMOVE, prefix, 'flask')
            assert not package_is_installed(prefix, 'flask-0.')
            assert_package_is_installed(prefix, 'python-3')

            # regression test for #2626
            # install tarball with full path
            flask_tar_file = glob(join(pkgs_dirs[0], 'flask-0.*.tar.bz2'))[-1]
            if not on_win:
                run_command(Commands.INSTALL, prefix, flask_tar_file)
                assert_package_is_installed(prefix, 'flask-0.')

                run_command(Commands.REMOVE, prefix, 'flask')
                assert not package_is_installed(prefix, 'flask-0.')

            # regression test for #2626
            # install tarball with relative path
            flask_tar_file = relpath(flask_tar_file)
            run_command(Commands.INSTALL,  prefix, flask_tar_file)
            assert_package_is_installed(prefix, 'flask-0.')

            # regression test for #2599
            linked_data_.clear()
            flask_metadata = glob(join(prefix, 'conda-meta', 'flask-0.*.json'))[-1]
            bad_metadata = join(prefix, 'conda-meta', 'flask.json')
            copyfile(flask_metadata, bad_metadata)
            assert not package_is_installed(prefix, 'flask', exact=True)
            assert_package_is_installed(prefix, 'flask-0.')

    @pytest.mark.timeout(120)
    def test_just_python2(self):
        with make_temp_env("python=2") as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            assert_package_is_installed(prefix, 'python-2')

            run_command(Commands.REMOVE, prefix, '--all')
            assert not exists(prefix)

    @pytest.mark.skipif(on_win, reason="get windows passing")
    @pytest.mark.timeout(300)
    def test_python2_install_numba(self):
        with make_temp_env("python=2") as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            assert not package_is_installed(prefix, 'numba')
            run_command(Commands.INSTALL, prefix, "numba")
            assert_package_is_installed(prefix, 'numba')

    @pytest.mark.skipif(on_win, reason="no 32-bit windows python on conda-forge")  #  and bits == 32
    @pytest.mark.timeout(300)
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

            with make_temp_env("--clone", prefix) as clone_prefix:
                assert_package_is_installed(clone_prefix, 'python-3.5')
                assert_package_is_installed(clone_prefix, 'decorator')

    @pytest.mark.skipif(on_win, reason="get windows passing")
    @pytest.mark.timeout(600)
    def test_python2_pandas(self):
        with make_temp_env("python=2 pandas") as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            assert_package_is_installed(prefix, 'numpy')


@pytest.mark.skipif(not on_win, reason="shortcuts only relevant on Windows")
def test_shortcut_in_underscore_env_shows_message():
    with TemporaryDirectory() as tmp:
        cmd = ["conda", "create", '-y', '--shortcuts', '-p', join(tmp, '_conda'), "console_shortcut"]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = p.communicate()
        if PY3:
            error = error.decode("UTF-8")
        assert "Environment name starts with underscore '_'.  Skipping menu installation." in error


@pytest.mark.skipif(not on_win, reason="shortcuts only relevant on Windows")
def test_shortcut_not_attempted_without_shortcuts_arg():
    with TemporaryDirectory() as tmp:
        cmd = ["conda", "create", '-y', '-p', join(tmp, '_conda'), "console_shortcut"]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = p.communicate()
        if PY3:
            error = error.decode("UTF-8")
        # This test is sufficient, because it effectively verifies that the code
        #  path was not visited.
        assert "Environment name starts with underscore '_'.  Skipping menu installation." not in error


@pytest.mark.skipif(not on_win, reason="shortcuts only relevant on Windows")
def test_shortcut_creation_installs_shortcut():
    with TemporaryDirectory() as tmp:
        subprocess.check_call(["conda", "create", '-y', '--shortcuts', '-p',
                               join(tmp, 'conda'), "console_shortcut"])

        user_mode = 'user' if exists(join(sys.prefix, u'.nonadmin')) else 'system'
        shortcut_dir = win_locations[user_mode]["start"]
        shortcut_dir = join(shortcut_dir, "Anaconda{} ({}-bit)".format(sys.version_info.major, config.bits))
        shortcut_file = join(shortcut_dir, "Anaconda Prompt (conda).lnk")
        assert isfile(shortcut_file)

        # make sure that cleanup without specifying --shortcuts still removes shortcuts
        subprocess.check_call(["conda", "remove", '-y', '-p', join(tmp, 'conda'), "console_shortcut"])
        try:
            assert not isfile(shortcut_file)
        finally:
            os.remove(shortcut_file)


@pytest.mark.skipif(not on_win, reason="shortcuts only relevant on Windows")
def test_shortcut_absent_does_not_barf_on_uninstall():
    with TemporaryDirectory() as tmp:
        # not including --shortcuts, should not get shortcuts installed
        subprocess.check_call(["conda", "create", '-y', '-p', join(tmp, 'conda'), "console_shortcut"])

        user_mode = 'user' if exists(join(sys.prefix, u'.nonadmin')) else 'system'
        shortcut_dir = win_locations[user_mode]["start"]
        shortcut_dir = join(shortcut_dir, "Anaconda{} ({}-bit)".format(sys.version_info.major, config.bits))
        assert not isfile(join(shortcut_dir, "Anaconda Prompt (conda).lnk"))

        # make sure that cleanup does not barf trying to remove non-existent shortcuts
        subprocess.check_call(["conda", "remove", '-y', '-p', join(tmp, 'conda'), "console_shortcut"])
