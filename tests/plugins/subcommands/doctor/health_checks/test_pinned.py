# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the pinned file format health check."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda.base.constants import OK_MARK, PREFIX_PINNED_FILE, X_MARK

if TYPE_CHECKING:
    from conda.testing.fixtures import CondaCLIFixture, TmpEnvFixture


@pytest.mark.parametrize(
    "pinned_file,expected_output",
    [
        ("", OK_MARK),
        ("conda 1.11", OK_MARK),
        ("conda 1.11, otherpackages==1", X_MARK),
        ('"conda"', X_MARK),
        ("imnotinstalledyet", X_MARK),
    ],
)
def test_pinned_will_formatted_check(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    pinned_file: str,
    expected_output: str,
):
    """Test pinned file format validation with various inputs."""
    with tmp_env() as prefix:
        (prefix / PREFIX_PINNED_FILE).write_text(pinned_file)

        out, _, _ = conda_cli("doctor", "--verbose", "--prefix", prefix)
        assert expected_output in out
