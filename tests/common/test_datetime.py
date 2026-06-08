# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from conda.common.datetime import (
    normalize_timestamp_seconds,
    parse_date_to_next_utc_day_timestamp,
    parse_duration_seconds,
    parse_iso_datetime_to_timestamp,
)


@pytest.mark.parametrize(
    "value, expected",
    [
        pytest.param("3600", 3600, id="plain-seconds"),
        pytest.param("20260401", 20260401, id="date-like-plain-seconds"),
        pytest.param("30s", 30, id="seconds"),
        pytest.param("5m", 300, id="minutes"),
        pytest.param("24h", 86400, id="hours"),
        pytest.param("7d", 7 * 86400, id="days"),
        pytest.param("1w", 7 * 86400, id="weeks"),
        pytest.param("3d12h", 3 * 86400 + 12 * 3600, id="combined-compact"),
        pytest.param("P1DT12H", 86400 + 12 * 3600, id="iso-combined"),
        pytest.param("PT30M", 1800, id="iso-minutes"),
        pytest.param("0d", 0, id="zero-compact"),
        pytest.param("P0D", 0, id="zero-iso"),
    ],
)
def test_parse_duration_seconds(value: str, expected: int) -> None:
    assert parse_duration_seconds(value) == expected


@pytest.mark.parametrize("value", ["P", "7d2x"])
def test_parse_duration_seconds_rejects_malformed_duration(value: str) -> None:
    with pytest.raises(ValueError):
        parse_duration_seconds(value)


def test_parse_duration_seconds_returns_none_for_non_duration() -> None:
    assert parse_duration_seconds("not-a-duration") is None


def test_parse_date_to_next_utc_day_timestamp() -> None:
    expected = datetime(2026, 4, 2, tzinfo=timezone.utc).timestamp()
    assert parse_date_to_next_utc_day_timestamp("2026-04-01") == expected


def test_parse_iso_datetime_to_timestamp_treats_naive_values_as_utc() -> None:
    expected = datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc).timestamp()
    assert parse_iso_datetime_to_timestamp("2026-04-01T12:00:00") == expected


def test_parse_iso_datetime_to_timestamp_honors_z_suffix_and_offsets() -> None:
    expected = datetime(2026, 4, 1, 10, 0, tzinfo=timezone.utc).timestamp()
    assert parse_iso_datetime_to_timestamp("2026-04-01T10:00:00Z") == expected
    assert parse_iso_datetime_to_timestamp("2026-04-01T12:00:00+02:00") == expected


@pytest.mark.parametrize("value", ["2026-04-01", "20260401"])
def test_parse_iso_datetime_to_timestamp_leaves_date_only_to_callers(
    value: str,
) -> None:
    assert parse_iso_datetime_to_timestamp(value) is None


def test_normalize_timestamp_seconds() -> None:
    assert normalize_timestamp_seconds(1_700_000_000) == 1_700_000_000
    assert normalize_timestamp_seconds(1_700_000_000_000) == 1_700_000_000
