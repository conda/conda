# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Integration tests for conda/_preview/env_setup/cli/main_install.py.

These tests verify that:
- When the env-setup preview is NOT enabled, `conda install` runs via the standard path.
- When the env-setup preview IS enabled, `conda install` is routed to the stub and
  raises OperationNotAllowed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda.exceptions import OperationNotAllowed

if TYPE_CHECKING:
    from conda.testing.fixtures import CondaCLIFixture


def test_install_preview_disabled(conda_cli: CondaCLIFixture):
    """conda install without CONDA_PREVIEW set routes to the standard implementation."""
    # --help exits cleanly via SystemExit; if routing had fired it would raise
    # OperationNotAllowed instead, so a clean SystemExit proves no redirection occurred.
    with pytest.raises(SystemExit):
        conda_cli("install", "--help")


def test_install_preview_enabled(
    conda_cli: CondaCLIFixture,
    monkeypatch,
):
    """conda install with CONDA_PREVIEW=env-setup is routed to the stub."""
    monkeypatch.setenv("CONDA_PREVIEW", "env-setup")

    out, err, exc = conda_cli("install", raises=OperationNotAllowed)

    assert exc.value is not None
    assert "env-setup" in str(exc.value)
    assert "conda install" in str(exc.value)
