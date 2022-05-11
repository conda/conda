# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import absolute_import, division, print_function, unicode_literals

import os
from unittest import TestCase

import pytest
from pytest import raises

from conda.auxlib.collection import AttrDict
from conda.base.context import conda_tests_ctxt_mgmt_def_pol, context
from conda.cli.common import check_non_admin, confirm, confirm_yn
from conda.common.compat import on_win, StringIO
from conda.common.io import captured, env_var
from conda.exceptions import CondaSystemExit, DryRunExit, OperationNotAllowed


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


def test_confirm_yn_yes(monkeypatch):
    monkeypatch.setattr('sys.stdin', StringIO('blah\ny\n'))
    with env_var('CONDA_ALWAYS_YES', 'false', stack_callback=conda_tests_ctxt_mgmt_def_pol):
        with env_var('CONDA_DRY_RUN', 'false', stack_callback=conda_tests_ctxt_mgmt_def_pol):
            assert not context.always_yes
            args = AttrDict({
                'dry_run': False,
            })
            with captured() as cap:
                choice = confirm_yn(args)
            assert choice is True
            assert "Invalid choice" in cap.stdout


def test_confirm_yn_no(monkeypatch):
    monkeypatch.setattr('sys.stdin', StringIO('n\n'))
    args = AttrDict({
        'dry_run': False,
    })
    with pytest.raises(CondaSystemExit):
        confirm_yn(args)


def test_dry_run_exit():
    with env_var('CONDA_DRY_RUN', 'true', stack_callback=conda_tests_ctxt_mgmt_def_pol):
        with pytest.raises(DryRunExit):
            confirm_yn()

        with pytest.raises(DryRunExit):
            confirm()


def test_always_yes():
    with env_var('CONDA_ALWAYS_YES', 'true', stack_callback=conda_tests_ctxt_mgmt_def_pol):
        with env_var('CONDA_DRY_RUN', 'false', stack_callback=conda_tests_ctxt_mgmt_def_pol):
            choice = confirm_yn()
            assert choice is True
