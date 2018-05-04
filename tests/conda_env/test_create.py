# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

from argparse import ArgumentParser
from contextlib import contextmanager
from logging import Handler, getLogger
from os.path import exists, join
from shlex import split
from shutil import rmtree
from tempfile import mkdtemp
from unittest import TestCase
from uuid import uuid4

import pytest

from conda.base.context import reset_context
from conda.common.io import dashlist, env_var
from conda.core.prefix_data import PrefixData
from conda.install import on_win
from conda.models.enums import PackageType
from conda.models.match_spec import MatchSpec
from conda_env.cli.main import do_call as do_call_conda_env
from conda_env.cli.main_create import configure_parser as create_configure_parser
from conda_env.cli.main_update import configure_parser as update_configure_parser
from . import support_file

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


def package_is_installed(prefix, spec, pip=None):
    spec = MatchSpec(spec)
    prefix_recs = tuple(PrefixData(prefix).query(spec))
    if len(prefix_recs) > 1:
        raise AssertionError("Multiple packages installed.%s"
                             % (dashlist(prec.dist_str() for prec in prefix_recs)))
    is_installed = bool(len(prefix_recs))
    if is_installed and pip is True:
        assert prefix_recs[0].package_type in (
            PackageType.SHADOW_PYTHON_DIST_INFO,
            PackageType.SHADOW_PYTHON_EGG_INFO_DIR,
            PackageType.SHADOW_PYTHON_EGG_INFO_FILE,
            PackageType.SHADOW_PYTHON_EGG_LINK,
        )
    if is_installed and pip is False:
        assert prefix_recs[0].package_type in (
            None,
            PackageType.NOARCH_GENERIC,
            PackageType.NOARCH_PYTHON,
        )
    return is_installed


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

                run_command(Commands.CREATE, env_name, support_file('example/environment_pinned.yml'))
                assert exists(python_path)
                assert package_is_installed(prefix, 'flask=0.9')

                run_command(Commands.UPDATE, env_name, support_file('example/environment_pinned_updated.yml'))
                assert package_is_installed(prefix, 'flask=0.10.1')
                assert not package_is_installed(prefix, 'flask=0.9')

    def test_create_advanced_pip(self):
        with make_temp_envs_dir() as envs_dir:
            with env_var('CONDA_ENVS_DIRS', envs_dir, reset_context):
                env_name = str(uuid4())[:8]
                prefix = join(envs_dir, env_name)
                python_path = join(prefix, PYTHON_BINARY)

                run_command(Commands.CREATE, env_name,
                            support_file('advanced-pip/environment.yml'))
                assert exists(python_path)
                PrefixData._cache_.clear()
                assert package_is_installed(prefix, 'argh', pip=True)
                assert package_is_installed(prefix, 'module-to-install-in-editable-mode', pip=True)
                try:
                    assert package_is_installed(prefix, 'six', pip=True)
                except AssertionError:
                    # six may now be conda-installed because of packaging changes
                    assert package_is_installed(prefix, 'six', pip=False)
                assert package_is_installed(prefix, 'xmltodict=0.10.2', pip=True)
