# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for external packages health check."""

from __future__ import annotations

from typing import TYPE_CHECKING

from conda.plugins.subcommands.doctor.health_checks.external_packages import (
    find_external_packages,
)

if TYPE_CHECKING:
    from conda.testing.fixtures import TmpEnvFixture


def test_no_external_packages(tmp_env: TmpEnvFixture):
    with tmp_env() as prefix:
        assert find_external_packages(prefix) == []
