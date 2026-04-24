# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for external packages health check."""

from __future__ import annotations

from typing import TYPE_CHECKING

from conda.plugins.subcommands.doctor.health_checks.external_packages import (
    find_external_packages,
)

if TYPE_CHECKING:
    from pathlib import Path

    from conda.testing.fixtures import PipCLIFixture, TmpEnvFixture


def test_no_external_packages(tmp_env: TmpEnvFixture):
    with tmp_env() as prefix:
        assert find_external_packages(prefix) == []


py_ver = "3.10"


def test_external_packages(
    tmp_env: TmpEnvFixture, pip_cli: PipCLIFixture, wheelhouse: Path
):
    with tmp_env(f"python={py_ver}", "pip") as prefix:
        wheel_path = wheelhouse / "small_python_package-1.0.0-py3-none-any.whl"
        _, _, _ = pip_cli("install", wheel_path, prefix=prefix)

        packages = find_external_packages(prefix)

        assert packages != []
        assert "small-python-package" == packages[0].name
