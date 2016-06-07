# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

from contextlib import contextmanager
from logging import getLogger
from os.path import exists, isdir, isfile, join
from shlex import split
from shutil import rmtree
from tempfile import gettempdir
from uuid import uuid1

import pytest

from conda import config
from conda.cli import conda_argparse
from conda.cli.main_create import configure_parser

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
        configure_parser(sub_parsers)

        command = "create -p {0} {1}".format(env_path, " ".join(packages))

        args = p.parse_args(split(command))
        args.func(args, p)

        yield env_path
    finally:
        rmtree(env_path, ignore_errors=True)


@pytest.mark.timeout(600)
def test_just_python3():
    with make_temp_env("python=3") as env_path:
        assert exists(join(env_path, 'bin/python3'))


@pytest.mark.timeout(600)
def test_just_python2():
    with make_temp_env("python=2") as env_path:
        assert exists(join(env_path, 'bin/python2'))


@pytest.mark.timeout(600)
def test_python2_anaconda():
    with make_temp_env("python=2 anaconda") as env_path:
        assert isfile(join(env_path, 'bin/python2'))
        assert isfile(join(env_path, 'bin/numba'))


if __name__ == '__main__':
    test_just_python3()
    test_just_python2()
