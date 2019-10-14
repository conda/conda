# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
import os
from unittest import TestCase

import pytest
from pytest import raises

from conda._vendor.auxlib.collection import AttrDict
from conda.base.context import conda_tests_ctxt_mgmt_def_pol
from conda.cli.common import check_non_admin
from conda.common.compat import on_win, StringIO
from conda.common.io import captured, env_var
from conda.exceptions import CondaSystemExit, DryRunExit, OperationNotAllowed
from conda.cli.python_api import run_command, Commands

log = getLogger(__name__)


try:
    from unittest.mock import Mock, patch
except ImportError:
    from mock import Mock, patch


def test_check_non_admin_enabled_false():
    with env_var('CONDA_NON_ADMIN_ENABLED', 'false', stack_callback=conda_tests_ctxt_mgmt_def_pol):
        if on_win:
            from conda.common._os.windows import is_admin_on_windows
            if is_admin_on_windows():
                check_non_admin()
            else:
                with raises(OperationNotAllowed):
                    check_non_admin()
        else:
            if os.geteuid() == 0 or os.getegid() == 0:
                check_non_admin()
            else:
                with raises(OperationNotAllowed):
                    check_non_admin()


def test_check_non_admin_enabled_true():
    with env_var('CONDA_NON_ADMIN_ENABLED', 'true', stack_callback=conda_tests_ctxt_mgmt_def_pol):
        check_non_admin()
        assert True


def test_cli_args_as_list():
    with env_var('CONDA_ADD_ANACONDA_TOKEN', 'false'):
        out, err, rc = run_command(Commands.CONFIG, ["--show", "add_anaconda_token"])
    assert out == 'add_anaconda_token: False\n'


def test_cli_args_as_strings():
    with env_var('CONDA_ADD_ANACONDA_TOKEN', 'false'):
        out, err, rc = run_command(Commands.CONFIG, "--show", "add_anaconda_token")
    assert out == 'add_anaconda_token: False\n'


class ConfirmTests(TestCase):

    @patch('sys.stdin', StringIO('blah\ny\n'))
    def test_confirm_yn_yes(self):
        args = AttrDict({
            'dry_run': False,
        })
        from conda.cli.common import confirm_yn
        with captured() as c:
            choice = confirm_yn()
        assert choice is True
        assert "Invalid choice" in c.stdout

    @patch('sys.stdin', StringIO('n\n'))
    def test_confirm_yn_no(self):
        args = AttrDict({
            'dry_run': False,
        })
        from conda.cli.common import confirm_yn
        with pytest.raises(CondaSystemExit):
            confirm_yn(args)

    def test_dry_run_exit(self):
        with env_var('CONDA_DRY_RUN', 'true', stack_callback=conda_tests_ctxt_mgmt_def_pol):
            from conda.cli.common import confirm_yn
            with pytest.raises(DryRunExit):
                confirm_yn()

            from conda.cli.common import confirm
            with pytest.raises(DryRunExit):
                confirm()

    def test_always_yes(self):
        with env_var('CONDA_ALWAYS_YES', 'true', stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with env_var('CONDA_DRY_RUN', 'false', stack_callback=conda_tests_ctxt_mgmt_def_pol):
                from conda.cli.common import confirm_yn
                choice = confirm_yn()
                assert choice is True
