# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from contextlib import nullcontext
from io import StringIO
from typing import TYPE_CHECKING

import pytest

from conda.base.context import conda_tests_ctxt_mgmt_def_pol, context
from conda.common.io import captured, env_vars
from conda.exceptions import CondaSystemExit, DryRunExit
from conda.plugins.reporter_backends.console import TQDMProgressBar
from conda.reporters import (
    confirm_yn,
    get_progress_bar,
    get_progress_bar_context_manager,
    render,
)

if TYPE_CHECKING:
    from pytest import CaptureFixture, MonkeyPatch


def test_render(capsys: CaptureFixture):
    """
    Ensure basic coverage of the :func:`~conda.reporters.render` function.
    """
    # Test simple rendering of object
    render("test-string")

    stdout, stderr = capsys.readouterr()
    assert stdout == "test-string"
    assert not stderr

    # Test rendering of object with a style
    render(["test-string"], style="envs_list")

    stdout, stderr = capsys.readouterr()
    assert "conda environments" in stdout
    assert "test-string" in stdout
    assert not stderr

    # Test error when style cannot be found
    with pytest.raises(
        AttributeError,
        match="'non_existent_view' is not a valid reporter backend style",
    ):
        render({"test": "data"}, style="non_existent_view")


def test_get_progress_bar():
    """
    Ensure basic coverage of the :func:`~conda.reporters.get_progress_bar~` function
    """
    progress_bar_manager = get_progress_bar("test")

    assert isinstance(progress_bar_manager, TQDMProgressBar)


def test_get_progress_bar_context_managers():
    """
    Ensure basic coverage of the
    :func:`~conda.reporters.get_progress_bar_context_manager~` function
    """
    progress_bar_context_manager = get_progress_bar_context_manager()

    assert isinstance(progress_bar_context_manager, nullcontext)


def test_confirm_yn_dry_run_exit():
    with (
        env_vars(
            {"CONDA_DRY_RUN": "true"},
            stack_callback=conda_tests_ctxt_mgmt_def_pol,
        ),
        pytest.raises(DryRunExit),
    ):
        confirm_yn()


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

        confirm_yn()


def test_confirm_yn_yes(monkeypatch: MonkeyPatch):
    monkeypatch.setattr("sys.stdin", StringIO("blah\ny\n"))

    with (
        env_vars(
            {
                "CONDA_ALWAYS_YES": "false",
                "CONDA_DRY_RUN": "false",
            },
            stack_callback=conda_tests_ctxt_mgmt_def_pol,
        ),
        captured() as cap,
    ):
        assert not context.always_yes
        assert not context.dry_run

        assert confirm_yn()

    assert "Invalid choice" in cap.stdout


def test_confirm_yn_no(monkeypatch: MonkeyPatch):
    monkeypatch.setattr("sys.stdin", StringIO("n\n"))

    with (
        env_vars(
            {
                "CONDA_ALWAYS_YES": "false",
                "CONDA_DRY_RUN": "false",
            },
            stack_callback=conda_tests_ctxt_mgmt_def_pol,
        ),
        pytest.raises(CondaSystemExit),
    ):
        assert not context.always_yes
        assert not context.dry_run

        confirm_yn()
