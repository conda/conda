# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os

import pytest
from pytest import raises

from conda.base.context import conda_tests_ctxt_mgmt_def_pol, context
from conda.cli.common import (
    check_non_admin,
    is_active_prefix,
    print_envs_list,
)
from conda.common.compat import on_win
from conda.common.io import env_vars
from conda.exceptions import OperationNotAllowed


def test_check_non_admin_enabled_false():
    with env_vars(
        {"CONDA_NON_ADMIN_ENABLED": "false"},
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
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
    with env_vars(
        {"CONDA_NON_ADMIN_ENABLED": "true"},
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        check_non_admin()
        assert True


@pytest.mark.parametrize("prefix,active", [("", False), ("active_prefix", True)])
def test_is_active_prefix(prefix, active):
    if prefix == "active_prefix":
        prefix = context.active_prefix
    assert is_active_prefix(prefix) is active


def test_print_envs_list(capsys):
    """
    Test the case for print_envs_list when output=True

    TODO: this function is deprecated and this test should be remove when this function is removed
    """
    with pytest.deprecated_call():
        print_envs_list(["test"])

    capture = capsys.readouterr()

    assert "test" in capture.out


def test_print_envs_list_output_false(capsys):
    """
    Test the case for print_envs_list when output=False

    TODO: this function is deprecated and this test should be remove when this function is removed
    """

    with pytest.deprecated_call():
        print_envs_list(["test"], output=False)

    capture = capsys.readouterr()

    assert capture.out == ""
