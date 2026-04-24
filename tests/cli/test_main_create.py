# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for `conda create` help text."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from conda.testing.fixtures import CondaCLIFixture


@pytest.mark.parametrize(
    "line",
    [
        "Create from package specs:",
        "conda create -n myenv python=3.12 numpy",
        "Create from an environment spec (solved at install time):",
        "Create from a lockfile (no solve, exact reproduction):",
        "Clone an existing environment:",
        "conda create -n env2 --clone env1",
        "Available input formats:",
        "Environment specs:",
    ],
)
def test_create_help_shows_examples_and_available_formats(
    conda_cli: CondaCLIFixture, line: str
) -> None:
    """The rewritten `conda create --help` renders the command's example
    sections and a dynamic listing of available input formats grouped by
    category."""
    stdout, _, _ = conda_cli("create", "--help", raises=SystemExit)
    assert line in stdout
