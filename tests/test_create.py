# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import pytest
from contextlib import contextmanager
from logging import getLogger
from os.path import exists, isdir, isfile, join
from shlex import split
from shutil import rmtree
from tempfile import gettempdir
from uuid import uuid1

from conda import config
from conda.cli import conda_argparse
from conda.cli.main_create import configure_parser as create_configure_parser
from conda.cli.main_install import configure_parser as install_configure_parser

log = getLogger(__name__)


def make_temp_env_path():
    tempdir = gettempdir()
    dirname = str(uuid1())[:8]
    env_path = join(tempdir, dirname)
    if exists(env_path):
        # rm here because create complains if directory exists
        rmtree(env_path)
    assert isdir(tempdir)
    return env_path


@contextmanager
def make_temp_env(*packages):
    env_path = make_temp_env_path()
    try:
        # try to clear any config that's been set by other tests
        config.rc = config.load_condarc('')
        
        p = conda_argparse.ArgumentParser()
        sub_parsers = p.add_subparsers(metavar='command', dest='cmd')
        create_configure_parser(sub_parsers)

        command = "create -y -p {0} {1}".format(env_path, " ".join(packages))

        args = p.parse_args(split(command))
        args.func(args, p)

        yield env_path
    finally:
        rmtree(env_path, ignore_errors=True)


def install_in_env(env_path, *packages):
    p = conda_argparse.ArgumentParser()
    sub_parsers = p.add_subparsers(metavar='command', dest='cmd')
    install_configure_parser(sub_parsers)

    command = "install -y -p {0} {1}".format(env_path, " ".join(packages))

    args = p.parse_args(split(command))
    args.func(args, p)


def test_just_python3():
    with make_temp_env("python=3") as env_path:
        assert exists(join(env_path, 'bin/python3'))


def test_just_python2():
    with make_temp_env("python=2") as env_path:
        assert exists(join(env_path, 'bin/python2'))


def test_python2_install_numba():
    with make_temp_env("python=2") as env_path:
        assert exists(join(env_path, 'bin/python2'))
        install_in_env(env_path, "numba")
        assert isfile(join(env_path, 'bin/numba'))


def test_dash_c_usage_replacing_python():
    with make_temp_env("-c conda-forge python=3.5") as env_path:
        assert exists(join(env_path, 'bin/python3.5'))
        install_in_env(env_path, "decorator")
        # TODO @mcg1969: now what?


@pytest.mark.timeout(600)
def test_python2_anaconda():
    with make_temp_env("python=2 anaconda") as env_path:
        assert isfile(join(env_path, 'bin/python2'))
        assert isfile(join(env_path, 'bin/numba'))


if __name__ == '__main__':
    test_python2_install_numba()
