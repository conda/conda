# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from contextlib import nullcontext
from io import StringIO
from typing import TYPE_CHECKING

import pytest

from conda.base.context import context, reset_context
from conda.exceptions import CondaSystemExit, DryRunExit
from conda.reporters import (
    confirm_yn,
    get_progress_bar,
    get_progress_bar_context_manager,
    get_reporter,
    get_spinner,
    render,
    reset_reporter,
)

if TYPE_CHECKING:
    from pytest import CaptureFixture, MonkeyPatch


def test_render(capsys: CaptureFixture):
    """
    Ensure basic coverage of the :func:`~conda.reporters.render` function.
    """
    reset_reporter()

    # Test simple rendering of object
    render("test-string")

    stdout, stderr = capsys.readouterr()
    assert stdout == "test-string\n"
    assert not stderr

    # Test rendering with an unknown style falls back to RenderDataEvent
    render({"test": "data"}, style="non_existent_view")
    stdout, stderr = capsys.readouterr()
    assert "test" in stdout
    assert not stderr


def test_get_progress_bar(monkeypatch):
    """
    Ensure basic coverage of the :func:`~conda.reporters.get_progress_bar~` function
    (deprecated path — exercises the legacy factory via the new deprecated shim).
    """
    import warnings

    monkeypatch.setattr("conda.plugins.reporter_backends.console.is_tty", lambda: True)
    monkeypatch.setattr(
        "conda.plugins.reporter_backends.console.term_dumb", lambda: False
    )
    reset_reporter()
    from conda.plugins.reporter_backends.console import _TQDMProgressBar

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        progress_bar_manager = get_progress_bar("test")

    assert isinstance(progress_bar_manager, _TQDMProgressBar)


def test_get_progress_bar_context_managers():
    """
    Ensure basic coverage of the
    :func:`~conda.reporters.get_progress_bar_context_manager~` function
    (deprecated path).
    """
    import warnings

    reset_reporter()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
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


def test_get_reporter_returns_conda_reporter():
    """get_reporter() returns a CondaReporter instance."""
    from conda.reporters import CondaReporter

    reset_reporter()
    reporter = get_reporter()
    assert isinstance(reporter, CondaReporter)


def test_get_spinner_is_context_manager(capsys):
    """get_spinner() returns a context manager that emits spinner events."""
    reset_reporter()
    with get_spinner("TestOp"):
        pass
    out, _ = capsys.readouterr()
    assert "TestOp" in out
