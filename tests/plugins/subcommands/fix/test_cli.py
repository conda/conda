# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the `conda fix` subcommand."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from conda.testing.fixtures import CondaCLIFixture


def test_conda_fix_help(conda_cli: CondaCLIFixture):
    """Make sure that we are able to run `conda fix --help`."""
    with pytest.raises(SystemExit, match="0"):
        conda_cli("fix", "--help")


def test_conda_fix_list(conda_cli: CondaCLIFixture):
    """Make sure that we are able to run `conda fix --list`."""
    out, err, code = conda_cli("fix", "--list")

    assert "Available fix tasks:" in out
    assert not err
    assert not code


def test_conda_fix_list_json(conda_cli: CondaCLIFixture):
    """Make sure that `conda fix --list --json` returns valid JSON."""
    import json

    out, err, code = conda_cli("fix", "--list", "--json")

    # Should be valid JSON (list of tasks)
    tasks = json.loads(out)
    assert isinstance(tasks, list)
    assert not code


def test_conda_fix_no_task_error(conda_cli: CondaCLIFixture):
    """Make sure that `conda fix` without a task shows an error."""
    from conda.exceptions import CondaError

    out, err, exc = conda_cli("fix", raises=CondaError)

    assert exc
    assert "No fix task specified" in str(exc)

