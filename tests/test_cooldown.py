# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the dependency cooldown feature."""

from __future__ import annotations

from argparse import ArgumentTypeError
from os.path import join
from time import time
from typing import TYPE_CHECKING

import pytest

from conda.base.context import reset_context
from conda.cli.helpers import parse_duration_to_seconds
from conda.common.serialize import json
from conda.core.subdir_data import SubdirData
from conda.models.channel import Channel
from conda.testing.helpers import CHANNEL_DIR_V1

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MonkeyPatch


PLATFORM = "linux-64"


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
    ],
)
def test_parse_duration_valid(value: str, expected: int):
    assert parse_duration_to_seconds(value) == expected


@pytest.mark.parametrize(
    "value, match",
    [
        pytest.param("", "must not be empty", id="empty"),
        pytest.param("abc", "invalid duration", id="garbage"),
        pytest.param("0d", "invalid duration", id="zero-duration"),
        pytest.param("7x", "invalid duration", id="unknown-unit"),
    ],
)
def test_parse_duration_invalid(value: str, match: str):
    with pytest.raises(ArgumentTypeError, match=match):
        parse_duration_to_seconds(value)


@pytest.mark.parametrize(
    "cooldown, exclude, expected_in, expected_out",
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
            id="short-cooldown-old-packages",
        ),
        pytest.param(
            None,
            None,
            set(),
            {"zlib", "libgcc-ng"},
            id="huge-cooldown-filters-all",
        ),
        pytest.param(
            None,
            "zlib&libgcc-ng",
            {"zlib", "libgcc-ng"},
            set(),
            id="exclude-bypasses-all",
        ),
        pytest.param(
            None,
            "zlib",
            {"zlib"},
            {"libgcc-ng"},
            id="partial-exclude",
        ),
    ],
)
def test_cooldown_local_channel(
    monkeypatch: MonkeyPatch,
    cooldown: str | None,
    exclude: str | None,
    expected_in: set[str],
    expected_out: set[str],
):
    if cooldown is None:
        cooldown = str(int(time()) + 86400)
    monkeypatch.setenv("CONDA_COOLDOWN", cooldown)
    if exclude is not None:
        monkeypatch.setenv("CONDA_COOLDOWN_EXCLUDE", exclude)
    reset_context()

    SubdirData.clear_cached_local_channel_data()
    channel = Channel(join(CHANNEL_DIR_V1, PLATFORM))
    sd = SubdirData(channel=channel)
    names = {rec.name for rec in sd.iter_records()}

    for name in expected_in:
        assert name in names, f"{name} should be included"
    for name in expected_out:
        assert name not in names, f"{name} should be excluded"


@pytest.fixture
def cooldown_channel(tmp_path: Path) -> Channel:
    """Create a temporary channel with packages that have and lack timestamps."""
    subdir_path = tmp_path / PLATFORM
    subdir_path.mkdir()

    now_ms = int(time() * 1000)
    pkg_base = {
        "build": "0",
        "build_number": 0,
        "depends": [],
        "md5": "d41d8cd98f00b204e9800998ecf8427e",
        "size": 100,
        "subdir": PLATFORM,
        "version": "1.0",
    }

    repodata = {
        "info": {"subdir": PLATFORM},
        "packages": {
            "has-old-timestamp-1.0-0.tar.bz2": {
                **pkg_base,
                "name": "has-old-timestamp",
                "timestamp": 1534516107109,
            },
            "has-new-timestamp-1.0-0.tar.bz2": {
                **pkg_base,
                "name": "has-new-timestamp",
                "timestamp": now_ms,
            },
            "no-timestamp-1.0-0.tar.bz2": {
                **pkg_base,
                "name": "no-timestamp",
            },
        },
        "packages.conda": {},
    }

    (subdir_path / "repodata.json").write_text(json.dumps(repodata))
    return Channel(str(subdir_path))


@pytest.mark.parametrize(
    "exclude, expected_in, expected_out",
    [
        pytest.param(
            None,
            {"no-timestamp", "has-old-timestamp"},
            {"has-new-timestamp"},
            id="no-timestamp-passes-through",
        ),
        pytest.param(
            "has-new-timestamp",
            {"no-timestamp", "has-old-timestamp", "has-new-timestamp"},
            set(),
            id="exempt-overrides-new-timestamp",
        ),
    ],
)
def test_cooldown_synthetic_channel(
    monkeypatch: MonkeyPatch,
    cooldown_channel: Channel,
    exclude: str | None,
    expected_in: set[str],
    expected_out: set[str],
):
    monkeypatch.setenv("CONDA_COOLDOWN", "86400")
    if exclude is not None:
        monkeypatch.setenv("CONDA_COOLDOWN_EXCLUDE", exclude)
    reset_context()

    SubdirData.clear_cached_local_channel_data()
    sd = SubdirData(channel=cooldown_channel)
    names = {rec.name for rec in sd.iter_records()}

    for name in expected_in:
        assert name in names, f"{name} should be included"
    for name in expected_out:
        assert name not in names, f"{name} should be excluded"


def test_cooldown_prefers_upload_timestamp(tmp_path: Path, monkeypatch: MonkeyPatch):
    subdir_path = tmp_path / PLATFORM
    subdir_path.mkdir()

    old_ms = 1534516107109
    now_ms = int(time() * 1000)

    pkg_base = {
        "build": "0",
        "build_number": 0,
        "depends": [],
        "md5": "d41d8cd98f00b204e9800998ecf8427e",
        "size": 100,
        "subdir": PLATFORM,
        "version": "1.0",
    }

    repodata = {
        "info": {"subdir": PLATFORM},
        "packages": {
            "old-upload-1.0-0.tar.bz2": {
                **pkg_base,
                "name": "old-upload",
                "timestamp": now_ms,
                "upload_timestamp": old_ms,
            },
            "new-upload-1.0-0.tar.bz2": {
                **pkg_base,
                "name": "new-upload",
                "timestamp": old_ms,
                "upload_timestamp": now_ms,
            },
        },
        "packages.conda": {},
    }

    (subdir_path / "repodata.json").write_text(json.dumps(repodata))

    monkeypatch.setenv("CONDA_COOLDOWN", "86400")
    reset_context()

    SubdirData.clear_cached_local_channel_data()
    sd = SubdirData(channel=Channel(str(subdir_path)))
    names = {rec.name for rec in sd.iter_records()}

    assert "old-upload" in names, (
        "old upload_timestamp should pass despite new build timestamp"
    )
    assert "new-upload" not in names, (
        "new upload_timestamp should be filtered despite old build timestamp"
    )
