# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the exclude-newer feature."""

from __future__ import annotations

from datetime import datetime, timezone
from time import time
from typing import TYPE_CHECKING

import pytest

from conda import CondaError
from conda.base.context import context, reset_context
from conda.common.serialize import json
from conda.core.exclude_newer import ExcludeNewerPolicy
from conda.core.index import ReducedIndex
from conda.core.solve import Solver
from conda.core.subdir_data import SubdirData
from conda.exceptions import CondaValueError, PackagesNotFoundError
from conda.models.channel import Channel
from conda.models.match_spec import MatchSpec
from conda.models.records import PackageRecord

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MonkeyPatch

    from conda.testing.fixtures import CondaCLIFixture


PLATFORM = "linux-64"
NOW = 1_700_000_000.0
DAY = 86400
CUTOFF = datetime.fromtimestamp(NOW - DAY, timezone.utc).isoformat()

PKG_BASE = {
    "build": "0",
    "build_number": 0,
    "depends": [],
    "md5": "d41d8cd98f00b204e9800998ecf8427e",
    "size": 100,
    "subdir": PLATFORM,
    "version": "1.0",
}


def _record(
    name: str,
    *,
    timestamp: int | float | None = None,
    indexed_timestamp: int | float | None = None,
    date: str | None = None,
) -> PackageRecord:
    kwargs = {
        **PKG_BASE,
        "name": name,
        "channel": Channel("https://example.test/conda"),
        "fn": f"{name}-1.0-0.tar.bz2",
    }
    if timestamp is not None:
        kwargs["timestamp"] = timestamp
    if indexed_timestamp is not None:
        kwargs["indexed_timestamp"] = indexed_timestamp
    if date is not None:
        kwargs["date"] = date
    return PackageRecord(**kwargs)


@pytest.fixture
def exclude_newer_channel(tmp_path: Path) -> tuple[Path, Channel]:
    channel_root = tmp_path / "channel"
    subdir_path = channel_root / PLATFORM
    noarch_path = channel_root / "noarch"
    subdir_path.mkdir(parents=True)
    noarch_path.mkdir()

    repodata = {
        "info": {"subdir": PLATFORM},
        "packages": {
            "old-pkg-1.0-0.tar.bz2": {
                **PKG_BASE,
                "name": "old-pkg",
                "timestamp": int((NOW - 10 * DAY) * 1000),
            },
            "new-pkg-1.0-0.tar.bz2": {
                **PKG_BASE,
                "name": "new-pkg",
                "timestamp": int((NOW - 60) * 1000),
            },
            "no-timestamp-pkg-1.0-0.tar.bz2": {
                **PKG_BASE,
                "name": "no-timestamp-pkg",
            },
        },
        "packages.conda": {},
    }

    (subdir_path / "repodata.json").write_text(json.dumps(repodata))
    (noarch_path / "repodata.json").write_text(
        json.dumps({"info": {"subdir": "noarch"}, "packages": {}, "packages.conda": {}})
    )
    return channel_root, Channel(str(subdir_path))


@pytest.mark.parametrize(
    "value, expected_duration",
    [
        pytest.param("3600", 3600, id="plain-seconds"),
        pytest.param("20260401", 20260401, id="date-like-plain-seconds"),
        pytest.param("30s", 30, id="seconds"),
        pytest.param("5m", 300, id="minutes"),
        pytest.param("24h", DAY, id="hours"),
        pytest.param("7d", 7 * DAY, id="days"),
        pytest.param("1w", 7 * DAY, id="one-week"),
        pytest.param("3d12h", 3 * DAY + 12 * 3600, id="combined-compact"),
        pytest.param("7D", 7 * DAY, id="uppercase-compact"),
        pytest.param("P7D", 7 * DAY, id="iso-days"),
        pytest.param("PT24H", DAY, id="iso-hours"),
        pytest.param("P1W", 7 * DAY, id="iso-week"),
        pytest.param("P1DT12H", DAY + 12 * 3600, id="iso-combined"),
        pytest.param("PT30M", 1800, id="iso-minutes"),
        pytest.param("PT3600S", 3600, id="iso-seconds"),
    ],
)
def test_exclude_newer_policy_parses_durations(
    value: str, expected_duration: int
) -> None:
    policy = ExcludeNewerPolicy.from_values(value, {}, now=NOW)
    assert policy.global_cutoff == NOW - expected_duration


@pytest.mark.parametrize("value", ["0", "0d", "P0D"])
def test_exclude_newer_policy_accepts_zero_as_disabled(value: str) -> None:
    assert not ExcludeNewerPolicy.from_values(value, {}, now=NOW).active


def test_exclude_newer_policy_accepts_absolute_cutoff_equal_to_now() -> None:
    value = datetime.fromtimestamp(NOW, timezone.utc).isoformat()
    policy = ExcludeNewerPolicy.from_values(value, {}, now=NOW)

    assert policy.active
    assert policy.global_cutoff == NOW


def test_exclude_newer_policy_parses_date_as_next_utc_day() -> None:
    policy = ExcludeNewerPolicy.from_values("2026-03-30", {}, now=NOW)
    expected = datetime(2026, 3, 31, tzinfo=timezone.utc).timestamp()
    assert policy.global_cutoff == expected


def test_exclude_newer_policy_parses_rfc3339_offset() -> None:
    policy = ExcludeNewerPolicy.from_values("2020-06-15T12:00:00+02:00", {}, now=NOW)
    expected = datetime(2020, 6, 15, 10, 0, tzinfo=timezone.utc).timestamp()
    assert policy.global_cutoff == expected


def test_exclude_newer_policy_allows_future_absolute_timestamp() -> None:
    policy = ExcludeNewerPolicy.from_values("2099-01-01", {}, now=NOW)
    assert policy.active
    assert policy.global_cutoff == datetime(2099, 1, 2, tzinfo=timezone.utc).timestamp()


@pytest.mark.parametrize("value", ["abc", "7x", "P", "-1"])
def test_exclude_newer_policy_rejects_invalid_values(value: str) -> None:
    with pytest.raises(CondaValueError, match="Invalid exclude_newer value"):
        ExcludeNewerPolicy.from_values(value, {}, now=NOW)


def test_exclude_newer_policy_filters_records() -> None:
    policy = ExcludeNewerPolicy.from_values("1d", {}, now=NOW)

    assert policy.should_include(_record("old", timestamp=NOW - 2 * DAY))
    assert not policy.should_include(_record("new", timestamp=NOW - 60))
    assert policy.should_include(_record("missing"))


def test_exclude_newer_policy_normalizes_millisecond_timestamps() -> None:
    policy = ExcludeNewerPolicy.from_values("1d", {}, now=NOW)

    assert policy.should_include(_record("old", timestamp=int((NOW - 2 * DAY) * 1000)))
    assert not policy.should_include(_record("new", timestamp=int((NOW - 60) * 1000)))


def test_exclude_newer_policy_prefers_indexed_timestamp() -> None:
    policy = ExcludeNewerPolicy.from_values("1d", {}, now=NOW)

    assert policy.should_include(
        _record("old-indexed", timestamp=NOW - 60, indexed_timestamp=NOW - 2 * DAY)
    )
    assert not policy.should_include(
        _record("new-indexed", timestamp=NOW - 2 * DAY, indexed_timestamp=NOW - 60)
    )


def test_exclude_newer_policy_does_not_use_date_as_indexed_timestamp() -> None:
    policy = ExcludeNewerPolicy.from_values("1d", {}, now=NOW)
    record = _record(
        "legacy-date",
        timestamp=NOW - 2 * DAY,
        date=datetime.fromtimestamp(NOW - 60, timezone.utc).isoformat(),
    )

    assert record.indexed_timestamp == 0
    assert policy.should_include(record)


def test_exclude_newer_policy_honors_package_false_exemption() -> None:
    policy = ExcludeNewerPolicy.from_values(
        "1d", {"openssl": False, "ca-certificates": "false"}, now=NOW
    )

    assert policy.should_include(_record("openssl", timestamp=NOW - 60))
    assert policy.should_include(_record("ca-certificates", timestamp=NOW - 60))
    assert not policy.should_include(_record("new-pkg", timestamp=NOW - 60))


def test_exclude_newer_policy_honors_package_custom_cutoff() -> None:
    policy = ExcludeNewerPolicy.from_values("1d", {"numpy": "3d"}, now=NOW)

    assert policy.should_include(_record("scipy", timestamp=NOW - 2 * DAY))
    assert not policy.should_include(_record("numpy", timestamp=NOW - 2 * DAY))


def test_exclude_newer_policy_allows_package_only_cutoff() -> None:
    policy = ExcludeNewerPolicy.from_values("", {"numpy": "3d"}, now=NOW)

    assert policy.should_include(_record("scipy", timestamp=NOW - 2 * DAY))
    assert not policy.should_include(_record("numpy", timestamp=NOW - 2 * DAY))


def test_subdir_data_cache_stays_unfiltered(
    exclude_newer_channel: tuple[Path, Channel],
) -> None:
    _, channel = exclude_newer_channel
    SubdirData.clear_cached_local_channel_data()

    records = tuple(SubdirData(channel=channel).iter_records())
    names = {record.name for record in records}

    assert {"old-pkg", "new-pkg", "no-timestamp-pkg"} == names

    policy_before = ExcludeNewerPolicy.from_values("2h", {}, now=NOW)
    policy_after = ExcludeNewerPolicy.from_values("2h", {}, now=NOW + 3 * 3600)

    assert "new-pkg" not in {
        record.name for record in policy_before.filter_records(records)
    }
    assert "new-pkg" in {record.name for record in policy_after.filter_records(records)}


def test_reduced_index_applies_exclude_newer_policy(
    exclude_newer_channel: tuple[Path, Channel],
) -> None:
    channel_root, _ = exclude_newer_channel
    policy = ExcludeNewerPolicy.from_values("1d", {}, now=NOW)

    index = ReducedIndex(
        specs=(MatchSpec("old-pkg"), MatchSpec("new-pkg")),
        channels=(str(channel_root),),
        prepend=False,
        subdirs=(PLATFORM,),
        use_system=False,
        exclude_newer_policy=policy,
    )
    names = {record.name for record in index.data}

    assert "old-pkg" in names
    assert "new-pkg" not in names


def test_search_applies_exclude_newer_policy(
    exclude_newer_channel: tuple[Path, Channel],
    monkeypatch: MonkeyPatch,
    conda_cli: CondaCLIFixture,
) -> None:
    channel_root, _ = exclude_newer_channel
    monkeypatch.setenv("CONDA_EXCLUDE_NEWER", CUTOFF)
    reset_context()

    conda_cli(
        "search",
        "new-pkg",
        f"--platform={PLATFORM}",
        "--override-channels",
        f"--channel={channel_root}",
        raises=PackagesNotFoundError,
    )

    monkeypatch.setattr(context, "exclude_newer_package", {"new-pkg": False})
    stdout, _, _ = conda_cli(
        "search",
        "new-pkg",
        f"--platform={PLATFORM}",
        "--override-channels",
        f"--channel={channel_root}",
        "--json",
    )
    assert "new-pkg" in json.loads(stdout)


def test_solver_subclass_fails_closed_for_unsupported_policy(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    class UnsupportedSolver(Solver):
        pass

    monkeypatch.setenv("CONDA_EXCLUDE_NEWER", "1d")
    reset_context()

    with pytest.raises(CondaError, match="does not support --exclude-newer"):
        UnsupportedSolver(prefix=str(tmp_path))


def test_solver_global_only_subclass_fails_for_package_overrides(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    class GlobalOnlySolver(Solver):
        supports_exclude_newer_global = True

    monkeypatch.setenv("CONDA_EXCLUDE_NEWER", "1d")
    reset_context()
    monkeypatch.setattr(context, "exclude_newer_package", {"openssl": False})

    with pytest.raises(CondaError, match="package overrides"):
        GlobalOnlySolver(prefix=str(tmp_path))


def test_post_solve_guard_rejects_newer_link_prec(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CONDA_EXCLUDE_NEWER", "1d")
    reset_context()
    solver = Solver(prefix=str(tmp_path))

    with pytest.raises(CondaError, match="solver returned package"):
        solver._validate_exclude_newer_link_precs(
            (_record("new-pkg", timestamp=int(time() * 1000)),)
        )
