# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import pytest
from contextlib import contextmanager
from glob import glob
from logging import getLogger, Handler
from os.path import exists, isdir, join, relpath
from shlex import split
from shutil import rmtree
from tempfile import gettempdir
from unittest import TestCase
from uuid import uuid4

from conda import config
from conda.cli import conda_argparse
from conda.cli.main_create import configure_parser as create_configure_parser
from conda.cli.main_install import configure_parser as install_configure_parser
from conda.cli.main_remove import configure_parser as remove_configure_parser
from conda.cli.main_update import configure_parser as update_configure_parser
from conda.config import pkgs_dirs, bits
from conda.install import linked as install_linked
from conda.install import on_win

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


def install_in_env(prefix, *packages):
    p = conda_argparse.ArgumentParser()
    sub_parsers = p.add_subparsers(metavar='command', dest='cmd')
    install_configure_parser(sub_parsers)

    command = "install -y -q -p {0} {1}".format(escape_for_winpath(prefix), " ".join(packages))

    args = p.parse_args(split(command))
    args.func(args, p)


def update_in_env(prefix, *packages):
    p = conda_argparse.ArgumentParser()
    sub_parsers = p.add_subparsers(metavar='command', dest='cmd')
    update_configure_parser(sub_parsers)

    command = "update -y -q -p {0} {1}".format(escape_for_winpath(prefix), " ".join(packages))

    args = p.parse_args(split(command))
    args.func(args, p)


def remove_from_env(prefix, *packages):
    p = conda_argparse.ArgumentParser()
    sub_parsers = p.add_subparsers(metavar='command', dest='cmd')
    remove_configure_parser(sub_parsers)

    command = "remove -y -q -p {0} {1}".format(escape_for_winpath(prefix), " ".join(packages))

    args = p.parse_args(split(command))
    args.func(args, p)


def package_is_installed(prefix, package):
    return any(p.startswith(package) for p in install_linked(prefix))


def assert_package_is_installed(prefix, package):
    if not package_is_installed(prefix, package):
        print([p for p in install_linked(prefix)])
        raise AssertionError("package {0} is not in prefix".format(package))


class IntegrationTests(TestCase):

    def setUp(self):
        self.saved_dotlog_handlers = disable_dotlog()

    def tearDown(self):
        reenable_dotlog(self.saved_dotlog_handlers)

    def test_python3(self):
        with make_temp_env("python=3") as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            assert_package_is_installed(prefix, 'python-3')

            install_in_env(prefix, 'flask=0.10')
            assert_package_is_installed(prefix, 'flask-0.10.1')

            update_in_env(prefix, 'flask')
            assert not package_is_installed(prefix, 'flask-0.10.1')
            assert_package_is_installed(prefix, 'flask')

            remove_from_env(prefix, 'flask')
            assert not package_is_installed(prefix, 'flask-0.')
            assert_package_is_installed(prefix, 'python-3')

            # regression test for #2626
            # install tarball with full path
            flask_tar_file = glob(join(pkgs_dirs[0], 'flask-*.tar.bz2'))[-1]
            install_in_env(prefix, flask_tar_file)
            assert_package_is_installed(prefix, 'flask-0.')

            remove_from_env(prefix, 'flask')
            assert not package_is_installed(prefix, 'flask-0.')

            # regression test for #2626
            # install tarball with relative path
            flask_tar_file = relpath(flask_tar_file)
            install_in_env(prefix, flask_tar_file)
            assert_package_is_installed(prefix, 'flask-0.')

    def test_just_python2(self):
        with make_temp_env("python=2") as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            assert_package_is_installed(prefix, 'python-2')

    def test_python2_install_numba(self):
        with make_temp_env("python=2") as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            assert not package_is_installed(prefix, 'numba')
            install_in_env(prefix, "numba")
            assert_package_is_installed(prefix, 'numba')

    @pytest.mark.skipif(on_win and bits == 32, reason="no 32-bit windows python on conda-forge")
    @pytest.mark.timeout(600)
    def test_dash_c_usage_replacing_python(self):
        # a regression test for #2606
        with make_temp_env("-c conda-forge python=3.5") as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            install_in_env(prefix, "decorator")
            assert_package_is_installed(prefix, 'conda-forge::python-3.5')

            with make_temp_env("--clone {0}".format(prefix)) as clone_prefix:
                assert_package_is_installed(clone_prefix, 'conda-forge::python-3.5')
                assert_package_is_installed(clone_prefix, "decorator")

    @pytest.mark.timeout(600)
    def test_python2_pandas(self):
        with make_temp_env("python=2 pandas") as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            assert_package_is_installed(prefix, 'numpy')
