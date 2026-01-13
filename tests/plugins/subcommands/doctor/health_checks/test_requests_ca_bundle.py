# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the REQUESTS_CA_BUNDLE health check.

Note: env_ok fixture is defined in tests/plugins/subcommands/conftest.py
and shared with health fix tests.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from requests import Response

from conda.base.constants import OK_MARK, X_MARK
from conda.plugins.subcommands.doctor.health_checks.requests_ca_bundle import (
    requests_ca_bundle_check,
)

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import CaptureFixture, MonkeyPatch
    from pytest_mock import MockerFixture

    from tests.plugins.subcommands.conftest import EnvFixture


def test_requests_ca_bundle_check_action_passes(
    env_ok: EnvFixture,
    capsys: CaptureFixture,
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    mocker: MockerFixture,
):
    """Test REQUESTS_CA_BUNDLE check when the bundle is valid."""
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(tmp_path))
    response = Response()
    response.status_code = 200
    mocker.patch(
        "conda.gateways.connection.session.CondaSession.get", return_value=response
    )
    requests_ca_bundle_check(env_ok.prefix, verbose=True)
    captured = capsys.readouterr()
    assert f"{OK_MARK} `REQUESTS_CA_BUNDLE` was verified.\n" in captured.out


def test_requests_ca_bundle_check_action_non_existent_path(
    env_ok: EnvFixture, capsys: CaptureFixture, monkeypatch: MonkeyPatch
):
    """Test REQUESTS_CA_BUNDLE check when the path doesn't exist."""
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", "non/existent/path")
    requests_ca_bundle_check(env_ok.prefix, verbose=True)
    captured = capsys.readouterr()
    assert (
        f"{X_MARK} Env var `REQUESTS_CA_BUNDLE` is pointing to a non existent file.\n"
        in captured.out
    )


def test_requests_ca_bundle_check_action_fails(
    env_ok: EnvFixture,
    capsys: CaptureFixture,
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
):
    """Test REQUESTS_CA_BUNDLE check when verification fails."""
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(tmp_path))
    requests_ca_bundle_check(env_ok.prefix, verbose=True)
    captured = capsys.readouterr()
    assert (
        f"{X_MARK} The following error occured while verifying `REQUESTS_CA_BUNDLE`:"
        in captured.out
    )
