# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Date, time, duration, and timestamp helpers."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from enum import Enum
from types import MappingProxyType

COMPACT_DURATION_UNITS = MappingProxyType(
    {
        "w": 604800,
        "d": 86400,
        "h": 3600,
        "m": 60,
        "s": 1,
    }
)

# Year 9999 in seconds. Larger timestamps are treated as milliseconds.
MAX_SECONDS_TIMESTAMP = 253402300799


class DateOnlyBehavior(Enum):
    """Behavior for date-only strings passed to ``parse_datetime_to_timestamp``."""

    REJECT = "reject"
    NEXT_UTC_DAY = "next-utc-day"


_COMPACT_DURATION_RE = re.compile(r"(\d+)\s*([wdhms])", re.IGNORECASE)
_ISO8601_DURATION_RE = re.compile(
    r"^P(?:(\d+)W)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$",
    re.IGNORECASE,
)
_DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_COMPACT_DATE_ONLY_RE = re.compile(r"^\d{8}$")


def parse_duration(value: str) -> timedelta | None:
    """Parse plain, compact, or ISO 8601 duration strings."""
    seconds = _parse_duration_seconds(value)
    if seconds is None:
        return None
    return timedelta(seconds=seconds)


def parse_datetime_to_timestamp(
    value: str,
    *,
    date_only: DateOnlyBehavior = DateOnlyBehavior.REJECT,
) -> float | None:
    """Parse an ISO/RFC 3339 datetime into a POSIX timestamp.

    Naive datetimes are interpreted as UTC. Date-only handling is explicit
    because its semantics vary by feature.
    """
    if _DATE_ONLY_RE.match(value):
        if date_only == DateOnlyBehavior.NEXT_UTC_DAY:
            day = datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
            return (day + timedelta(days=1)).timestamp()
        return None

    if _COMPACT_DATE_ONLY_RE.match(value):
        return None

    normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
    try:
        timestamp = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.timestamp()


def normalize_timestamp_seconds(value: str | int | float) -> float:
    """Normalize a seconds-or-milliseconds POSIX timestamp to seconds."""
    timestamp = float(value)
    if timestamp > MAX_SECONDS_TIMESTAMP:
        timestamp /= 1000
    return timestamp


def _parse_duration_seconds(value: str) -> int | None:
    value = value.strip()
    try:
        return int(value)
    except ValueError:
        pass

    duration = _parse_iso8601_duration_seconds(value)
    if duration is not None:
        return duration

    return _parse_compact_duration_seconds(value)


def _parse_iso8601_duration_seconds(value: str) -> int | None:
    match = _ISO8601_DURATION_RE.match(value)
    if not match:
        return None

    if not any(group is not None for group in match.groups()):
        raise ValueError(f"Invalid ISO 8601 duration {value!r}")

    weeks, days, hours, minutes, seconds = (
        int(group) if group else 0 for group in match.groups()
    )
    return (
        weeks * COMPACT_DURATION_UNITS["w"]
        + days * COMPACT_DURATION_UNITS["d"]
        + hours * COMPACT_DURATION_UNITS["h"]
        + minutes * COMPACT_DURATION_UNITS["m"]
        + seconds
    )


def _parse_compact_duration_seconds(value: str) -> int | None:
    pairs = _COMPACT_DURATION_RE.findall(value)
    if not pairs:
        return None

    consumed = _COMPACT_DURATION_RE.sub("", value).strip()
    if consumed:
        raise ValueError(f"Invalid compact duration {value!r}")

    return sum(
        int(amount) * COMPACT_DURATION_UNITS[unit.lower()] for amount, unit in pairs
    )
