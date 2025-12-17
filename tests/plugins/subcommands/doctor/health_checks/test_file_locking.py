# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the file locking health check."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda.base.constants import OK_MARK, X_MARK
from conda.base.context import context, reset_context
from conda.gateways.disk import lock

if TYPE_CHECKING:
    from pytest import MonkeyPatch

    from conda.testing.fixtures import CondaCLIFixture


@pytest.mark.parametrize("no_lock_flag", [True, False])
def test_file_locking_supported(
    conda_cli: CondaCLIFixture,
    no_lock_flag: bool,
    monkeypatch: MonkeyPatch,
):
    """Test file locking check with CONDA_NO_LOCK enabled/disabled."""
    assert lock.locking_supported()

    monkeypatch.setenv("CONDA_NO_LOCK", no_lock_flag)
    reset_context()

    assert context.no_lock == no_lock_flag

    out, _, _ = conda_cli("doctor")
    if no_lock_flag:
        assert (
            f"{X_MARK} File locking is supported but currently disabled using the CONDA_NO_LOCK=1 setting.\n"
            in out
        )
    else:
        assert f"{OK_MARK} File locking is supported." in out


def test_file_locking_not_supported(
    conda_cli: CondaCLIFixture, monkeypatch: MonkeyPatch
):
    """Test file locking check when locking is not supported."""
    monkeypatch.setattr(lock, "_lock_impl", lock._lock_noop)

    assert not lock.locking_supported()

    out, _, _ = conda_cli("doctor")

    assert f"{X_MARK} File locking is not supported." in out
