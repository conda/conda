# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from contextlib import nullcontext
from io import StringIO
from typing import TYPE_CHECKING

import pytest

from conda.base.context import context, reset_context
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


def test_confirm_yn_dry_run_exit(monkeypatch: MonkeyPatch):
    with pytest.raises(DryRunExit):
        monkeypatch.setenv("CONDA_DRY_RUN", "true")
        reset_context()

        confirm_yn()


def test_confirm_yn_always_yes(monkeypatch: MonkeyPatch):
    monkeypatch.setenv("CONDA_ALWAYS_YES", "true")
    monkeypatch.setenv("CONDA_DRY_RUN", "false")
    reset_context()
    assert context.always_yes
    assert not context.dry_run

    confirm_yn()


def test_confirm_yn_yes(monkeypatch: MonkeyPatch, capsys: CaptureFixture):
    monkeypatch.setattr("sys.stdin", StringIO("blah\ny\n"))

    monkeypatch.setenv("CONDA_ALWAYS_YES", "false")
    monkeypatch.setenv("CONDA_DRY_RUN", "false")
    reset_context()
    assert not context.always_yes
    assert not context.dry_run

    assert confirm_yn()

    stdout, stderr = capsys.readouterr()
    assert "Invalid choice" in stdout


def test_confirm_yn_no(monkeypatch: MonkeyPatch):
    monkeypatch.setattr("sys.stdin", StringIO("n\n"))

    with pytest.raises(CondaSystemExit):
        monkeypatch.setenv("CONDA_ALWAYS_YES", "false")
        monkeypatch.setenv("CONDA_DRY_RUN", "false")
        reset_context()

        assert not context.always_yes
        assert not context.dry_run

        confirm_yn()
