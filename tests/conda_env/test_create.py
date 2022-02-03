# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import absolute_import, division, print_function

from logging import Handler, getLogger
from os.path import exists, join
from shutil import rmtree
from unittest import TestCase
from uuid import uuid4

import pytest

from conda.base.context import conda_tests_ctxt_mgmt_def_pol
from conda.common.io import dashlist, env_var, env_vars
from conda.common.serialize import yaml_round_trip_load
from conda.core.prefix_data import PrefixData
from conda.install import on_win
from conda.models.enums import PackageType
from conda.models.match_spec import MatchSpec
from conda.testing.integration import run_command as run_conda_command, \
    Commands as CondaCommands

from . import support_file
from .utils import make_temp_envs_dir, Commands, run_command

PYTHON_BINARY = 'python.exe' if on_win else 'bin/python'
from tests.test_utils import is_prefix_activated_PATHwise


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


def package_is_installed(prefix, spec, pip=None):
    spec = MatchSpec(spec)
    prefix_recs = tuple(PrefixData(prefix, pip_interop_enabled=pip).query(spec))
    if len(prefix_recs) > 1:
        raise AssertionError("Multiple packages installed.%s"
                             % (dashlist(prec.dist_str() for prec in prefix_recs)))
    is_installed = bool(len(prefix_recs))
    if is_installed and pip is True:
        assert prefix_recs[0].package_type in (
            PackageType.VIRTUAL_PYTHON_WHEEL,
            PackageType.VIRTUAL_PYTHON_EGG_MANAGEABLE,
            PackageType.VIRTUAL_PYTHON_EGG_UNMANAGEABLE,
            PackageType.VIRTUAL_PYTHON_EGG_LINK,
        )
    if is_installed and pip is False:
        assert prefix_recs[0].package_type in (
            None,
            PackageType.NOARCH_GENERIC,
            PackageType.NOARCH_PYTHON,
        )
    return is_installed

def get_env_vars(prefix):
    pd = PrefixData(prefix)

    env_vars = pd.get_environment_env_vars()

    return env_vars


@pytest.mark.integration
class IntegrationTests(TestCase):

    def setUp(self):
        self.saved_dotlog_handlers = disable_dotlog()

    def tearDown(self):
        reenable_dotlog(self.saved_dotlog_handlers)

    def test_create_update(self):
        with make_temp_envs_dir() as envs_dir:
            with env_var('CONDA_ENVS_DIRS', envs_dir, stack_callback=conda_tests_ctxt_mgmt_def_pol):
                env_name = str(uuid4())[:8]
                prefix = join(envs_dir, env_name)
                python_path = join(prefix, PYTHON_BINARY)

                run_command(Commands.CREATE, env_name, support_file('example/environment_pinned.yml'))
                assert exists(python_path)
                assert package_is_installed(prefix, 'flask=0.12.2')

                env_vars = get_env_vars(prefix)
                assert env_vars['FIXED'] == 'fixed'
                assert env_vars['CHANGES'] == 'original_value'
                assert env_vars['GETS_DELETED'] == 'not_actually_removed_though'
                assert env_vars.get('NEW_VAR') is None

                run_command(Commands.UPDATE, env_name, support_file('example/environment_pinned_updated.yml'))
                assert package_is_installed(prefix, 'flask=1.0.2')
                assert not package_is_installed(prefix, 'flask=0.12.2')

                env_vars = get_env_vars(prefix)
                assert env_vars['FIXED'] == 'fixed'
                assert env_vars['CHANGES'] == 'updated_value'
                assert env_vars['NEW_VAR'] == 'new_var'

                # This ends up sticking around since there is no real way of knowing that an environment
                # variable _used_ to be in the variables dict, but isn't any more.
                assert env_vars['GETS_DELETED'] == 'not_actually_removed_though'

    def test_create_update_remote_env_file(self):
        with make_temp_envs_dir() as envs_dir:
            with env_var('CONDA_ENVS_DIRS', envs_dir, stack_callback=conda_tests_ctxt_mgmt_def_pol):
                env_name = str(uuid4())[:8]
                prefix = join(envs_dir, env_name)
                python_path = join(prefix, PYTHON_BINARY)

                run_command(Commands.CREATE, env_name, support_file('example/environment_pinned.yml', remote=True))
                assert exists(python_path)
                assert package_is_installed(prefix, 'flask=0.12.2')

                env_vars = get_env_vars(prefix)
                assert env_vars['FIXED'] == 'fixed'
                assert env_vars['CHANGES'] == 'original_value'
                assert env_vars['GETS_DELETED'] == 'not_actually_removed_though'
                assert env_vars.get('NEW_VAR') is None

                run_command(Commands.UPDATE, env_name, support_file('example/environment_pinned_updated.yml', remote=True))
                assert package_is_installed(prefix, 'flask=1.0.2')
                assert not package_is_installed(prefix, 'flask=0.12.2')

                env_vars = get_env_vars(prefix)
                assert env_vars['FIXED'] == 'fixed'
                assert env_vars['CHANGES'] == 'updated_value'
                assert env_vars['NEW_VAR'] == 'new_var'

                # This ends up sticking around since there is no real way of knowing that an environment
                # variable _used_ to be in the variables dict, but isn't any more.
                assert env_vars['GETS_DELETED'] == 'not_actually_removed_though'

    @pytest.mark.skip(reason="Need to find an appropriate server to test this on.")
    def test_create_host_port(self):
        with make_temp_envs_dir() as envs_dir:
            with env_var('CONDA_ENVS_DIRS', envs_dir, stack_callback=conda_tests_ctxt_mgmt_def_pol):
                env_name = str(uuid4())[:8]
                prefix = join(envs_dir, env_name)
                python_path = join(prefix, PYTHON_BINARY)

                run_command(Commands.CREATE, env_name, support_file('example/environment_host_port.yml'))
                assert exists(python_path)
                assert package_is_installed(prefix, 'flask=1.0.2')


    # This test will not run from an unactivated conda in an IDE. You *will* get complaints about being unable
    # to load the SSL module. Never try to test conda from outside an activated env. Maybe this should be a
    # session fixture with autouse=True so we just refuse to run the testsuite in that case?!
    @pytest.mark.skipif(not is_prefix_activated_PATHwise(),
                        reason="You are running `pytest` outside of proper activation. "
                               "The entries necessary for conda to operate correctly "
                               "are not on PATH.  Please use `conda activate`")
    def test_create_advanced_pip(self):
        with make_temp_envs_dir() as envs_dir:
            with env_vars({
                'CONDA_ENVS_DIRS': envs_dir,
            }, stack_callback=conda_tests_ctxt_mgmt_def_pol):
                env_name = str(uuid4())[:8]
                prefix = join(envs_dir, env_name)
                python_path = join(prefix, PYTHON_BINARY)

                run_command(Commands.CREATE, env_name,
                            support_file(join('advanced-pip', 'environment.yml')))
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

    def test_create_empty_env(self):
        with make_temp_envs_dir() as envs_dir:
            with env_var('CONDA_ENVS_DIRS', envs_dir, stack_callback=conda_tests_ctxt_mgmt_def_pol):
                env_name = str(uuid4())[:8]
                prefix = join(envs_dir, env_name)
                run_command(Commands.CREATE, env_name, support_file('empty_env.yml'))
                assert exists(prefix)


    def test_create_env_default_packages(self):
        with make_temp_envs_dir() as envs_dir:
            with env_var('CONDA_ENVS_DIRS', envs_dir, stack_callback=conda_tests_ctxt_mgmt_def_pol):
                # set packages
                run_conda_command(CondaCommands.CONFIG, envs_dir, "--add", "create_default_packages", "pip")
                run_conda_command(CondaCommands.CONFIG, envs_dir, "--add", "create_default_packages", "flask")
                stdout, stderr, _ = run_conda_command(CondaCommands.CONFIG, envs_dir, "--show")
                yml_obj = yaml_round_trip_load(stdout)
                assert yml_obj['create_default_packages'] == ['flask', 'pip']

                assert not package_is_installed(envs_dir, 'python=2')
                assert not package_is_installed(envs_dir, 'pytz')
                assert not package_is_installed(envs_dir, 'flask')

                env_name = str(uuid4())[:8]
                prefix = join(envs_dir, env_name)
                run_command(Commands.CREATE, env_name, support_file('env_with_dependencies.yml'))
                assert exists(prefix)
                assert package_is_installed(prefix, 'python=2')
                assert package_is_installed(prefix, 'pytz')
                assert package_is_installed(prefix, 'flask')

    def test_create_env_no_default_packages(self):
        with make_temp_envs_dir() as envs_dir:
            with env_var('CONDA_ENVS_DIRS', envs_dir, stack_callback=conda_tests_ctxt_mgmt_def_pol):
                # set packages
                run_conda_command(CondaCommands.CONFIG, envs_dir, "--add", "create_default_packages", "pip")
                run_conda_command(CondaCommands.CONFIG, envs_dir, "--add", "create_default_packages", "flask")
                stdout, stderr, _ = run_conda_command(CondaCommands.CONFIG, envs_dir, "--show")
                yml_obj = yaml_round_trip_load(stdout)
                assert yml_obj['create_default_packages'] == ['flask', 'pip']

                assert not package_is_installed(envs_dir, 'python=2')
                assert not package_is_installed(envs_dir, 'pytz')
                assert not package_is_installed(envs_dir, 'flask')

                env_name = str(uuid4())[:8]
                prefix = join(envs_dir, env_name)
                run_command(Commands.CREATE, env_name, support_file('env_with_dependencies.yml'), "--no-default-packages")
                assert exists(prefix)
                assert package_is_installed(prefix, 'python=2')
                assert package_is_installed(prefix, 'pytz')
                assert not package_is_installed(prefix, 'flask')
