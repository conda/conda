# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Date, time, duration, and timestamp helpers."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

from frozendict import frozendict

COMPACT_DURATION_UNITS = frozendict(
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


_COMPACT_DURATION_RE = re.compile(r"(\d+)\s*([wdhms])", re.IGNORECASE)
_ISO8601_DURATION_RE = re.compile(
    r"""
    ^P             # period/duration designator
    (?:(\d+)W)?    # number of weeks
    (?:(\d+)D)?    # number of days
    (?:T            # time designator
      (?:(\d+)H)?  # number of hours
      (?:(\d+)M)?  # number of minutes
      (?:(\d+)S)?  # number of seconds
    )?
    $
    """,
    re.IGNORECASE | re.VERBOSE,
)
_DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_COMPACT_DATE_ONLY_RE = re.compile(r"^\d{8}$")


def parse_duration(value: str) -> timedelta | None:
    """Parse plain, compact, or ISO 8601 duration strings."""
    value = value.strip()
    # Try a plain duration in seconds.
    try:
        return timedelta(seconds=int(value))
    except ValueError:
        pass

    # Match an ISO 8601 duration (e.g. P2W, P3D).
    match = _ISO8601_DURATION_RE.match(value)
    if match:
        if all(group is None for group in match.groups()):
            raise ValueError(f"Invalid ISO 8601 duration {value!r}")

        weeks, days, hours, minutes, seconds = (
            int(group) if group else 0 for group in match.groups()
        )
        return timedelta(
            seconds=(
                weeks * COMPACT_DURATION_UNITS["w"]
                + days * COMPACT_DURATION_UNITS["d"]
                + hours * COMPACT_DURATION_UNITS["h"]
                + minutes * COMPACT_DURATION_UNITS["m"]
                + seconds
            )
        )

    # Find compact duration components (e.g. 2w, 3d).
    pairs = _COMPACT_DURATION_RE.findall(value)
    if not pairs:
        return None

    # Reject values with unmatched compact duration content.
    remainder = _COMPACT_DURATION_RE.sub("", value).strip()
    if remainder:
        raise ValueError(f"Invalid compact duration {value!r}")

    return timedelta(
        seconds=sum(
            int(amount) * COMPACT_DURATION_UNITS[unit.lower()] for amount, unit in pairs
        )
    )


def parse_datetime_to_timestamp(value: str) -> float | None:
    """Parse an ISO/RFC 3339 datetime into a POSIX timestamp.

    Naive datetimes are interpreted as UTC. Date-only values are interpreted
    as the start of the following UTC day.
    """
    if _DATE_ONLY_RE.match(value):
        day = date.fromisoformat(value) + timedelta(days=1)
        return datetime.combine(
            day,
            datetime.min.time(),
            tzinfo=timezone.utc,
        ).timestamp()

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
