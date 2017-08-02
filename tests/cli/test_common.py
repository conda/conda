# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
import os

from pytest import raises

from conda.base.context import reset_context

from conda.cli.common import check_non_admin
from conda.common.compat import on_win
from conda.common.io import env_var
from conda.exceptions import OperationNotAllowed

log = getLogger(__name__)


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
