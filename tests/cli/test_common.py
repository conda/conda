# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os
from io import StringIO

import pytest
from pytest import MonkeyPatch, raises

from conda.base.context import conda_tests_ctxt_mgmt_def_pol, context
from conda.cli.common import check_non_admin, confirm, confirm_yn, is_active_prefix
from conda.common.compat import on_win
from conda.common.io import captured, env_vars
from conda.exceptions import CondaSystemExit, DryRunExit, OperationNotAllowed


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


def test_confirm_yn_yes(monkeypatch: MonkeyPatch):
    monkeypatch.setattr("sys.stdin", StringIO("blah\ny\n"))

    with env_vars(
        {
            "CONDA_ALWAYS_YES": "false",
            "CONDA_DRY_RUN": "false",
        },
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ), captured() as cap:
        assert not context.always_yes
        assert not context.dry_run

        assert confirm_yn()

    assert "Invalid choice" in cap.stdout


def test_confirm_yn_no(monkeypatch: MonkeyPatch):
    monkeypatch.setattr("sys.stdin", StringIO("n\n"))

    with env_vars(
        {
            "CONDA_ALWAYS_YES": "false",
            "CONDA_DRY_RUN": "false",
        },
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ), pytest.raises(CondaSystemExit):
        assert not context.always_yes
        assert not context.dry_run

        confirm_yn()


def test_confirm_yn_dry_run_exit():
    with env_vars(
        {"CONDA_DRY_RUN": "true"},
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ), pytest.raises(DryRunExit):
        assert context.dry_run

        confirm_yn()


def test_confirm_dry_run_exit():
    with env_vars(
        {"CONDA_DRY_RUN": "true"},
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ), pytest.raises(DryRunExit):
        assert context.dry_run

        confirm()


def test_confirm_yn_always_yes():
    with env_vars(
        {
            "CONDA_ALWAYS_YES": "true",
            "CONDA_DRY_RUN": "false",
        },
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        assert context.always_yes
        assert not context.dry_run

        assert confirm_yn()


@pytest.mark.parametrize("prefix,active", [("", False), ("active_prefix", True)])
def test_is_active_prefix(prefix, active):
    if prefix == "active_prefix":
        prefix = context.active_prefix
    assert is_active_prefix(prefix) is active
