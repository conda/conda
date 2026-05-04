# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Integration tests for conda/_preview/env_setup/cli/main_create.py.

These tests verify that:
- When the env-setup preview is NOT enabled, `conda create` runs via the standard path.
- When the env-setup preview IS enabled, `conda create` is routed to the stub and
  raises OperationNotAllowed.
- An unrecognized preview label does not crash `conda create`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda.exceptions import OperationNotAllowed

if TYPE_CHECKING:
    from conda.testing.fixtures import CondaCLIFixture


def test_create_preview_disabled(conda_cli: CondaCLIFixture):
    """conda create without CONDA_PREVIEW set routes to the standard implementation."""
    # --help exits cleanly via SystemExit(0); if routing had fired it would raise
    # OperationNotAllowed instead, so a clean SystemExit proves no redirection occurred.
    with pytest.raises(SystemExit, match="0"):
        conda_cli("create", "--help")


def test_create_preview_enabled(
    conda_cli: CondaCLIFixture,
    monkeypatch,
):
    """conda create with CONDA_PREVIEW=env-setup is routed to the stub."""
    monkeypatch.setenv("CONDA_PREVIEW", "env-setup")

    out, err, exc = conda_cli(
        "create", "--name", "test-env", raises=OperationNotAllowed
    )

    assert exc.value is not None
    assert "env-setup" in str(exc.value)
    assert "conda create" in str(exc.value)


def test_unknown_preview_label_no_crash(conda_cli: CondaCLIFixture, monkeypatch):
    """An unrecognized preview label produces no crash; the normal path is used."""
    monkeypatch.setenv("CONDA_PREVIEW", "typo-label")

    # --help exits cleanly; proves normal path was followed despite unknown label
    with pytest.raises(SystemExit, match="0"):
        conda_cli("create", "--help")
