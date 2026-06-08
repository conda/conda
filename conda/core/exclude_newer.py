# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Helpers for applying the ``exclude_newer`` package policy."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from time import time
from typing import TYPE_CHECKING

from ..exceptions import CondaValueError

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from typing import Any

    from ..models.records import PackageRecord

_DURATION_UNITS: dict[str, int] = {
    "w": 604800,
    "d": 86400,
    "h": 3600,
    "m": 60,
    "s": 1,
}

_COMPACT_DURATION_RE = re.compile(r"(\d+)\s*([wdhms])", re.IGNORECASE)
_ISO8601_DURATION_RE = re.compile(
    r"^P(?:(\d+)W)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$",
    re.IGNORECASE,
)
_DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Year 9999 in seconds. Larger repodata timestamps are treated as milliseconds.
_MAX_SECONDS_TIMESTAMP = 253402300799


@dataclass(frozen=True)
class ExcludeNewerPolicy:
    """Resolved ``exclude_newer`` configuration.

    Cutoffs are stored as absolute POSIX timestamps. A package record is included
    when its ``indexed_timestamp`` or ``timestamp`` is missing or older than the
    effective cutoff for that package name.
    """

    global_cutoff: float | None = None
    package_cutoffs: dict[str, float | None] | None = None
    now: float = 0.0

    @classmethod
    def disabled(cls) -> ExcludeNewerPolicy:
        return cls()

    @classmethod
    def from_context(cls, now: float | None = None) -> ExcludeNewerPolicy:
        from ..base.context import context

        return cls.from_values(
            context.exclude_newer,
            context.exclude_newer_package,
            now=now,
        )

    @classmethod
    def from_values(
        cls,
        exclude_newer: str | int | float | None,
        exclude_newer_package: Mapping[str, str | bool | int | float | None] | None,
        now: float | None = None,
    ) -> ExcludeNewerPolicy:
        resolved_now = time() if now is None else now
        global_cutoff = _parse_optional_cutoff(exclude_newer, resolved_now)

        package_cutoffs: dict[str, float | None] = {}
        for package_name, raw_value in sorted((exclude_newer_package or {}).items()):
            if not package_name:
                continue
            if _is_false(raw_value):
                package_cutoffs[package_name] = None
            elif raw_value is None or raw_value is True:
                continue
            else:
                package_cutoffs[package_name] = _parse_cutoff(raw_value, resolved_now)

        if global_cutoff is None and not any(
            cutoff is not None for cutoff in package_cutoffs.values()
        ):
            return cls.disabled()

        return cls(
            global_cutoff=global_cutoff,
            package_cutoffs=package_cutoffs,
            now=resolved_now,
        )

    @property
    def active(self) -> bool:
        return self.global_cutoff is not None or any(
            cutoff is not None for cutoff in (self.package_cutoffs or {}).values()
        )

    @property
    def has_global_cutoff(self) -> bool:
        return self.global_cutoff is not None

    @property
    def has_package_overrides(self) -> bool:
        return bool(self.package_cutoffs) and self.active

    def cutoff_for(self, package_name: str | None) -> float | None:
        if package_name and self.package_cutoffs and package_name in self.package_cutoffs:
            return self.package_cutoffs[package_name]
        return self.global_cutoff

    def should_include(self, record: PackageRecord | Mapping[str, Any]) -> bool:
        package_name = _record_value(record, "name")
        cutoff = self.cutoff_for(package_name)
        if cutoff is None:
            return True

        timestamp = _record_timestamp(record)
        if timestamp is None:
            return True

        return timestamp <= cutoff

    def filter_records(
        self, records: Iterable[PackageRecord]
    ) -> tuple[PackageRecord, ...]:
        if not self.active:
            return tuple(records)
        return tuple(record for record in records if self.should_include(record))

    def excluded_records(
        self, records: Iterable[PackageRecord]
    ) -> tuple[PackageRecord, ...]:
        if not self.active:
            return ()
        return tuple(record for record in records if not self.should_include(record))


def _is_false(value: object) -> bool:
    return value is False or (
        isinstance(value, str) and value.strip().casefold() == "false"
    )


def _parse_optional_cutoff(value: str | int | float | None, now: float) -> float | None:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None

    cutoff = _parse_cutoff(value, now)
    return None if cutoff == now else cutoff


def _parse_cutoff(value: str | int | float | bool, now: float) -> float:
    if isinstance(value, bool):
        raise CondaValueError(
            f"Invalid exclude_newer value {value!r}; use a duration, date, or timestamp"
        )

    if isinstance(value, (int, float)):
        return _duration_cutoff(float(value), value, now)

    raw_value = value.strip()
    if not raw_value:
        raise CondaValueError("Invalid exclude_newer value ''; value must not be empty")

    try:
        return _duration_cutoff(float(int(raw_value)), raw_value, now)
    except ValueError:
        pass

    if _DATE_ONLY_RE.match(raw_value):
        try:
            day = datetime.fromisoformat(raw_value).replace(tzinfo=timezone.utc)
        except ValueError as exc:
            raise _invalid(raw_value) from exc
        return (day + timedelta(days=1)).timestamp()

    normalized = raw_value.replace("Z", "+00:00") if raw_value.endswith("Z") else raw_value
    try:
        timestamp = datetime.fromisoformat(normalized)
    except ValueError:
        pass
    else:
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        return timestamp.timestamp()

    duration = _parse_iso8601_duration(raw_value)
    if duration is not None:
        return _duration_cutoff(duration, raw_value, now)

    duration = _parse_compact_duration(raw_value)
    if duration is not None:
        return _duration_cutoff(duration, raw_value, now)

    raise _invalid(raw_value)


def _duration_cutoff(duration_seconds: float, value: object, now: float) -> float:
    if duration_seconds < 0:
        raise CondaValueError(
            f"Invalid exclude_newer value {value!r}; duration must not be negative"
        )
    return now - duration_seconds


def _parse_iso8601_duration(value: str) -> int | None:
    match = _ISO8601_DURATION_RE.match(value)
    if not match:
        return None

    if not any(group is not None for group in match.groups()):
        raise _invalid(value)

    weeks, days, hours, minutes, seconds = (
        int(group) if group else 0 for group in match.groups()
    )
    return (
        weeks * _DURATION_UNITS["w"]
        + days * _DURATION_UNITS["d"]
        + hours * _DURATION_UNITS["h"]
        + minutes * _DURATION_UNITS["m"]
        + seconds
    )


def _parse_compact_duration(value: str) -> int | None:
    pairs = _COMPACT_DURATION_RE.findall(value)
    if not pairs:
        return None

    consumed = _COMPACT_DURATION_RE.sub("", value).strip()
    if consumed:
        raise _invalid(value)

    return sum(int(amount) * _DURATION_UNITS[unit.lower()] for amount, unit in pairs)


def _invalid(value: str) -> CondaValueError:
    return CondaValueError(
        f"Invalid exclude_newer value {value!r}; use e.g. 7d, P7D, "
        "2026-04-01, or 2026-04-01T12:00:00Z"
    )


def _record_value(record: PackageRecord | Mapping[str, Any], key: str) -> Any:
    if hasattr(record, "get"):
        return record.get(key)  # type: ignore[no-any-return, union-attr]
    return getattr(record, key, None)


def _record_timestamp(record: PackageRecord | Mapping[str, Any]) -> float | None:
    value = _record_value(record, "indexed_timestamp") or _record_value(
        record, "timestamp"
    )
    if not value:
        return None

    try:
        timestamp = float(value)
    except (TypeError, ValueError):
        return None

    if timestamp > _MAX_SECONDS_TIMESTAMP:
        timestamp /= 1000
    return timestamp
