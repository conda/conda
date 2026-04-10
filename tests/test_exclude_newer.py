# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the exclude-newer feature."""

from __future__ import annotations

from argparse import ArgumentTypeError
from datetime import datetime, timezone
from os.path import join
from time import time
from typing import TYPE_CHECKING

import pytest

from conda.base.context import context, reset_context
from conda.cli.helpers import parse_duration_to_seconds
from conda.common.serialize import json
from conda.core.subdir_data import SubdirData
from conda.models.channel import Channel
from conda.testing.helpers import CHANNEL_DIR_V1

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MonkeyPatch


PLATFORM = "linux-64"

PKG_BASE = {
    "build": "0",
    "build_number": 0,
    "depends": [],
    "md5": "d41d8cd98f00b204e9800998ecf8427e",
    "size": 100,
    "subdir": PLATFORM,
    "version": "1.0",
}


@pytest.mark.parametrize(
    "value, expected",
    [
        pytest.param("0", 0, id="zero"),
        pytest.param("3600", 3600, id="plain-seconds"),
        pytest.param("604800", 604800, id="plain-large"),
        pytest.param("30s", 30, id="seconds"),
        pytest.param("5m", 300, id="minutes"),
        pytest.param("24h", 86400, id="hours"),
        pytest.param("7d", 604800, id="days"),
        pytest.param("1w", 604800, id="one-week"),
        pytest.param("2w", 1209600, id="two-weeks"),
        pytest.param("3d12h", 3 * 86400 + 12 * 3600, id="combined-days-hours"),
        pytest.param("1w2d", 9 * 86400, id="combined-weeks-days"),
        pytest.param("7D", 604800, id="uppercase-D"),
        pytest.param("1W", 604800, id="uppercase-W"),
        pytest.param("  7d  ", 604800, id="whitespace"),
        pytest.param("P7D", 604800, id="iso8601-days"),
        pytest.param("PT24H", 86400, id="iso8601-hours"),
        pytest.param("P1W", 604800, id="iso8601-week"),
        pytest.param("P1DT12H", 1 * 86400 + 12 * 3600, id="iso8601-combined"),
        pytest.param("PT30M", 1800, id="iso8601-minutes"),
        pytest.param("PT3600S", 3600, id="iso8601-seconds"),
        pytest.param("P2W3D", 2 * 604800 + 3 * 86400, id="iso8601-weeks-days"),
    ],
)
def test_parse_duration_valid(value: str, expected: int):
    assert parse_duration_to_seconds(value) == expected


def test_parse_duration_iso_date():
    result = parse_duration_to_seconds("2020-01-01")
    expected_ts = int(
        datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp()
    )
    expected_delta = int(time()) - expected_ts
    assert abs(result - expected_delta) < 2


def test_parse_duration_rfc3339_timestamp():
    result = parse_duration_to_seconds("2020-06-15T12:00:00Z")
    expected_ts = int(
        datetime(2020, 6, 15, 12, 0, 0, tzinfo=timezone.utc).timestamp()
    )
    expected_delta = int(time()) - expected_ts
    assert abs(result - expected_delta) < 2


def test_parse_duration_rfc3339_with_offset():
    result = parse_duration_to_seconds("2020-06-15T12:00:00+02:00")
    expected_ts = int(
        datetime(2020, 6, 15, 10, 0, 0, tzinfo=timezone.utc).timestamp()
    )
    expected_delta = int(time()) - expected_ts
    assert abs(result - expected_delta) < 2


def test_parse_duration_future_timestamp_rejected():
    with pytest.raises(ArgumentTypeError, match="in the future"):
        parse_duration_to_seconds("2099-01-01")


@pytest.mark.parametrize(
    "value, match",
    [
        pytest.param("", "must not be empty", id="empty"),
        pytest.param("abc", "invalid duration", id="garbage"),
        pytest.param("0d", "invalid duration", id="zero-duration"),
        pytest.param("P0D", "invalid duration", id="iso8601-zero"),
        pytest.param("7x", "invalid duration", id="unknown-unit"),
    ],
)
def test_parse_duration_invalid(value: str, match: str):
    with pytest.raises(ArgumentTypeError, match=match):
        parse_duration_to_seconds(value)


@pytest.mark.parametrize(
    "exclude_newer, pkg_overrides, expected_in, expected_out",
    [
        pytest.param(
            "0",
            None,
            {"zlib", "libgcc-ng"},
            set(),
            id="disabled",
        ),
        pytest.param(
            "86400",
            None,
            {"zlib", "libgcc-ng"},
            set(),
            id="short-threshold-old-packages",
        ),
        pytest.param(
            None,
            None,
            set(),
            {"zlib", "libgcc-ng"},
            id="huge-threshold-filters-all",
        ),
        pytest.param(
            None,
            {"zlib": "false", "libgcc-ng": "false"},
            {"zlib", "libgcc-ng"},
            set(),
            id="exempt-bypasses-all",
        ),
        pytest.param(
            None,
            {"zlib": "false"},
            {"zlib"},
            {"libgcc-ng"},
            id="partial-exempt",
        ),
    ],
)
def test_exclude_newer_local_channel(
    monkeypatch: MonkeyPatch,
    exclude_newer: str | None,
    pkg_overrides: dict[str, str] | None,
    expected_in: set[str],
    expected_out: set[str],
):
    if exclude_newer is None:
        exclude_newer = str(int(time()) + 86400)
    monkeypatch.setenv("CONDA_EXCLUDE_NEWER", exclude_newer)
    reset_context()
    if pkg_overrides is not None:
        monkeypatch.setattr(context, "exclude_newer_package", pkg_overrides)

    SubdirData.clear_cached_local_channel_data()
    channel = Channel(join(CHANNEL_DIR_V1, PLATFORM))
    sd = SubdirData(channel=channel)
    names = {rec.name for rec in sd.iter_records()}

    for name in expected_in:
        assert name in names, f"{name} should be included"
    for name in expected_out:
        assert name not in names, f"{name} should be excluded"


@pytest.fixture
def exclude_newer_channel(tmp_path: Path) -> Channel:
    """Create a temporary channel with packages that have and lack timestamps."""
    subdir_path = tmp_path / PLATFORM
    subdir_path.mkdir()

    now_ms = int(time() * 1000)
    repodata = {
        "info": {"subdir": PLATFORM},
        "packages": {
            "has-old-timestamp-1.0-0.tar.bz2": {
                **PKG_BASE,
                "name": "has-old-timestamp",
                "timestamp": 1534516107109,
            },
            "has-new-timestamp-1.0-0.tar.bz2": {
                **PKG_BASE,
                "name": "has-new-timestamp",
                "timestamp": now_ms,
            },
            "no-timestamp-1.0-0.tar.bz2": {
                **PKG_BASE,
                "name": "no-timestamp",
            },
        },
        "packages.conda": {},
    }

    (subdir_path / "repodata.json").write_text(json.dumps(repodata))
    return Channel(str(subdir_path))


@pytest.mark.parametrize(
    "pkg_overrides, expected_in, expected_out",
    [
        pytest.param(
            None,
            {"no-timestamp", "has-old-timestamp"},
            {"has-new-timestamp"},
            id="no-timestamp-passes-through",
        ),
        pytest.param(
            {"has-new-timestamp": "false"},
            {"no-timestamp", "has-old-timestamp", "has-new-timestamp"},
            set(),
            id="exempt-overrides-new-timestamp",
        ),
    ],
)
def test_exclude_newer_synthetic_channel(
    monkeypatch: MonkeyPatch,
    exclude_newer_channel: Channel,
    pkg_overrides: dict[str, str] | None,
    expected_in: set[str],
    expected_out: set[str],
):
    monkeypatch.setenv("CONDA_EXCLUDE_NEWER", "86400")
    reset_context()
    if pkg_overrides is not None:
        monkeypatch.setattr(context, "exclude_newer_package", pkg_overrides)

    SubdirData.clear_cached_local_channel_data()
    sd = SubdirData(channel=exclude_newer_channel)
    names = {rec.name for rec in sd.iter_records()}

    for name in expected_in:
        assert name in names, f"{name} should be included"
    for name in expected_out:
        assert name not in names, f"{name} should be excluded"


def test_exclude_newer_prefers_indexed_timestamp(
    tmp_path: Path, monkeypatch: MonkeyPatch
):
    subdir_path = tmp_path / PLATFORM
    subdir_path.mkdir()

    old_ms = 1534516107109
    now_ms = int(time() * 1000)

    repodata = {
        "info": {"subdir": PLATFORM},
        "packages": {
            "old-indexed-1.0-0.tar.bz2": {
                **PKG_BASE,
                "name": "old-indexed",
                "timestamp": now_ms,
                "indexed_timestamp": old_ms,
            },
            "new-indexed-1.0-0.tar.bz2": {
                **PKG_BASE,
                "name": "new-indexed",
                "timestamp": old_ms,
                "indexed_timestamp": now_ms,
            },
        },
        "packages.conda": {},
    }

    (subdir_path / "repodata.json").write_text(json.dumps(repodata))

    monkeypatch.setenv("CONDA_EXCLUDE_NEWER", "86400")
    reset_context()

    SubdirData.clear_cached_local_channel_data()
    sd = SubdirData(channel=Channel(str(subdir_path)))
    names = {rec.name for rec in sd.iter_records()}

    assert "old-indexed" in names, (
        "old indexed_timestamp should pass despite new build timestamp"
    )
    assert "new-indexed" not in names, (
        "new indexed_timestamp should be filtered despite old build timestamp"
    )


def test_exclude_newer_per_package_duration(
    tmp_path: Path, monkeypatch: MonkeyPatch
):
    """Per-package override with a custom duration."""
    subdir_path = tmp_path / PLATFORM
    subdir_path.mkdir()

    now_ms = int(time() * 1000)
    two_days_ago_ms = int((time() - 2 * 86400) * 1000)

    repodata = {
        "info": {"subdir": PLATFORM},
        "packages": {
            "recent-pkg-1.0-0.tar.bz2": {
                **PKG_BASE,
                "name": "recent-pkg",
                "timestamp": now_ms,
            },
            "two-day-old-pkg-1.0-0.tar.bz2": {
                **PKG_BASE,
                "name": "two-day-old-pkg",
                "timestamp": two_days_ago_ms,
            },
        },
        "packages.conda": {},
    }

    (subdir_path / "repodata.json").write_text(json.dumps(repodata))

    monkeypatch.setenv("CONDA_EXCLUDE_NEWER", "86400")
    reset_context()
    monkeypatch.setattr(context, "exclude_newer_package", {"two-day-old-pkg": "3d"})

    SubdirData.clear_cached_local_channel_data()
    sd = SubdirData(channel=Channel(str(subdir_path)))
    names = {rec.name for rec in sd.iter_records()}

    assert "recent-pkg" not in names, "recent-pkg should be excluded by global 1d threshold"
    assert "two-day-old-pkg" not in names, (
        "two-day-old-pkg should be excluded by its per-package 3d threshold"
    )


def test_exclude_newer_per_package_bool_false(
    tmp_path: Path, monkeypatch: MonkeyPatch
):
    """Boolean False (from YAML parsing) exempts a package, same as string 'false'."""
    subdir_path = tmp_path / PLATFORM
    subdir_path.mkdir()

    now_ms = int(time() * 1000)
    repodata = {
        "info": {"subdir": PLATFORM},
        "packages": {
            "some-pkg-1.0-0.tar.bz2": {
                **PKG_BASE,
                "name": "some-pkg",
                "timestamp": now_ms,
            },
        },
        "packages.conda": {},
    }

    (subdir_path / "repodata.json").write_text(json.dumps(repodata))

    monkeypatch.setenv("CONDA_EXCLUDE_NEWER", "86400")
    reset_context()
    monkeypatch.setattr(context, "exclude_newer_package", {"some-pkg": False})

    SubdirData.clear_cached_local_channel_data()
    sd = SubdirData(channel=Channel(str(subdir_path)))
    names = {rec.name for rec in sd.iter_records()}

    assert "some-pkg" in names, "boolean False should exempt the package"
