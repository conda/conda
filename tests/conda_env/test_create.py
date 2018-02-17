# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

from argparse import ArgumentParser
from unittest import TestCase

from conda.base.context import reset_context
from conda.common.io import env_var

from conda.egg_info import get_egg_info
from conda.exports import text_type
from contextlib import contextmanager
from logging import getLogger, Handler
from os.path import exists, join
from shlex import split
from shutil import rmtree
from tempfile import mkdtemp
from uuid import uuid4

import pytest

from conda.install import on_win
from conda_env.cli.main_create import configure_parser as create_configure_parser
from conda_env.cli.main_update import configure_parser as update_configure_parser
from conda_env.cli.main import do_call as do_call_conda_env
from conda.core.prefix_data import linked

from . import utils


PYTHON_BINARY = 'python.exe' if on_win else 'bin/python'


def escape_for_winpath(p):
    return p.replace('\\', '\\\\')


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
    CREATE = "create"
    UPDATE = "update"


parser_config = {
    Commands.CREATE: create_configure_parser,
    Commands.UPDATE: update_configure_parser,
}


def run_command(command, env_name, *arguments):
    p = ArgumentParser()
    sub_parsers = p.add_subparsers(metavar='command', dest='cmd')
    parser_config[command](sub_parsers)

    arguments = list(map(escape_for_winpath, arguments))
    command_line = "{0} -n {1} -f {2}".format(command, env_name, " ".join(arguments))

    args = p.parse_args(split(command_line))
    do_call_conda_env(args, p)


@contextmanager
def make_temp_envs_dir():
    envs_dir = mkdtemp()
    try:
        yield envs_dir
    finally:
        rmtree(envs_dir, ignore_errors=True)


def package_is_installed(prefix, dist, exact=False, pip=False):
    packages = list(get_egg_info(prefix) if pip else linked(prefix))
    if '::' not in text_type(dist):
        packages = [p.dist_name for p in packages]
    if exact:
        return dist in packages
    return any(p.startswith(dist) for p in packages)


def assert_package_is_installed(prefix, package, exact=False, pip=False):
    if not package_is_installed(prefix, package, exact, pip):
        print(list(linked(prefix)))
        raise AssertionError("package {0} is not in prefix".format(package))


@pytest.mark.integration
class IntegrationTests(TestCase):

    def setUp(self):
        self.saved_dotlog_handlers = disable_dotlog()

    def tearDown(self):
        reenable_dotlog(self.saved_dotlog_handlers)

    def test_create_update(self):
        with make_temp_envs_dir() as envs_dir:
            with env_var('CONDA_ENVS_DIRS', envs_dir, reset_context):
                env_name = str(uuid4())[:8]
                prefix = join(envs_dir, env_name)
                python_path = join(prefix, PYTHON_BINARY)

                run_command(Commands.CREATE, env_name, utils.support_file('example/environment_pinned.yml'))
                assert exists(python_path)
                assert_package_is_installed(prefix, 'flask-0.9')

                run_command(Commands.UPDATE, env_name, utils.support_file('example/environment_pinned_updated.yml'))
                assert_package_is_installed(prefix, 'flask-0.10.1')
                assert not package_is_installed(prefix, 'flask-0.9')

    def test_create_advanced_pip(self):
        with make_temp_envs_dir() as envs_dir:
            with env_var('CONDA_ENVS_DIRS', envs_dir, reset_context):
                env_name = str(uuid4())[:8]
                prefix = join(envs_dir, env_name)
                python_path = join(prefix, PYTHON_BINARY)

                run_command(Commands.CREATE, env_name,
                            utils.support_file('advanced-pip/environment.yml'))
                assert exists(python_path)
                assert_package_is_installed(prefix, 'argh', exact=False, pip=True)
                assert_package_is_installed(prefix, 'module-to-install-in-editable-mode', exact=False, pip=True)
                try:
                    assert_package_is_installed(prefix, 'six', exact=False, pip=True)
                except AssertionError:
                    # six may now be conda-installed because of packaging changes
                    assert_package_is_installed(prefix, 'six', exact=False, pip=False)
                assert_package_is_installed(prefix, 'xmltodict-0.10.2-<pip>', exact=True, pip=True)
