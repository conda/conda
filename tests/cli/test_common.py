# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
import os
from unittest import TestCase

import pytest
from pytest import raises

from conda._vendor.auxlib.collection import AttrDict
from conda.base.context import reset_context
from conda.cli.common import check_non_admin
from conda.common.compat import on_win
from conda.common.io import captured, env_var
from conda.exceptions import CondaSystemExit, DryRunExit, OperationNotAllowed

log = getLogger(__name__)


try:
    from unittest.mock import Mock, patch
except ImportError:
    from mock import Mock, patch


def test_check_non_admin_enabled_false():
    with env_var('CONDA_NON_ADMIN_ENABLED', 'false', reset_context):
        if on_win:
            from conda.common.platform import is_admin_on_windows
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
    with env_var('CONDA_NON_ADMIN_ENABLED', 'true', reset_context):
        check_non_admin()
        assert True


class ConfirmTests(TestCase):

    @patch("sys.stdin.readline", side_effect=('blah\n', 'y\n'))
    def test_confirm_yn_yes(self, stdin_mock):
        args = AttrDict({
            'dry_run': False,
        })
        from conda.cli.common import confirm_yn
        with captured() as c:
            choice = confirm_yn()
        assert choice is True
        assert "Invalid choice" in c.stdout

    @patch("sys.stdin.readline", return_value='n\n')
    def test_confirm_yn_no(self, stdin_mock):
        args = AttrDict({
            'dry_run': False,
        })
        from conda.cli.common import confirm_yn
        with pytest.raises(CondaSystemExit):
            confirm_yn(args)

    def test_dry_run_exit(self):
        with env_var('CONDA_DRY_RUN', 'true', reset_context):
            from conda.cli.common import confirm_yn
            with pytest.raises(DryRunExit):
                confirm_yn()

            from conda.cli.common import confirm
            with pytest.raises(DryRunExit):
                confirm()

    def test_always_yes(self):
        with env_var('CONDA_ALWAYS_YES', 'true', reset_context):
            with env_var('CONDA_DRY_RUN', 'false', reset_context):
                from conda.cli.common import confirm_yn
                choice = confirm_yn()
                assert choice is True
