# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import pytest
from contextlib import contextmanager
import os
from logging import getLogger
from shlex import split
from shutil import rmtree
from tempfile import mkdtemp

from conda.cli import conda_argparse
from conda.cli.main_create import configure_parser
from conda import config

log = getLogger(__name__)


@contextmanager
def make_env(*packages):
    try:
        # try to clear any config that's been set by other tests
        config.rc = config.load_condarc('')

        env_path = mkdtemp()
        try:
            rmtree(env_path)  # rm here because create complains if directory exists
        except OSError as e:
            print("OSError", e)
        if not os.path.exists(os.path.dirname(env_path)):
            os.mkdir(os.path.dirname(env_path))

        p = conda_argparse.ArgumentParser()
        sub_parsers = p.add_subparsers(metavar='command', dest='cmd')
        configure_parser(sub_parsers)

        command = "create -p {0} {1}".format(env_path, " ".join(packages))

        args = p.parse_args(split(command))
        args.func(args, p)

        yield env_path
    finally:
        try:
            rmtree(env_path)
        except OSError:
            print("{0} does not exist".format(env_path))
        print(env_path)


@pytest.mark.timeout(600)
def test_just_python3():
    with make_env("python=3") as env_path:
        assert os.path.exists(os.path.join(env_path, 'bin/python3'))


@pytest.mark.timeout(600)
def test_just_python2():
    with make_env("python=2") as env_path:
        assert os.path.exists(os.path.join(env_path, 'bin/python2'))


@pytest.mark.timeout(600)
def test_python2_anaconda():
    with make_env("python=2 anaconda") as env_path:
        assert os.path.isfile(os.path.join(env_path, 'bin/python2'))
        assert os.path.isfile(os.path.join(env_path, 'bin/numba'))


if __name__ == '__main__':
    test_just_python3()
    test_just_python2()
    # test_python2_anaconda()
