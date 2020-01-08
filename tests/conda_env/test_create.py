# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

from logging import Handler, getLogger
from os.path import exists, join
from unittest import TestCase
from uuid import uuid4

import pytest

from conda.base.context import conda_tests_ctxt_mgmt_def_pol
from conda.common.io import dashlist, env_var, env_vars
from conda.core.prefix_data import PrefixData
from conda.install import on_win
from conda.models.enums import PackageType
from conda.models.match_spec import MatchSpec
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

                run_command(Commands.UPDATE, env_name, support_file('example/environment_pinned_updated.yml'))
                assert package_is_installed(prefix, 'flask=1.0.2')
                assert not package_is_installed(prefix, 'flask=0.12.2')


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

