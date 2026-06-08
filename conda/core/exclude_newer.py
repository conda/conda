# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Helpers for applying the ``exclude_newer`` package policy."""

from __future__ import annotations

from dataclasses import dataclass
from time import time
from typing import TYPE_CHECKING

from ..common.datetime import (
    normalize_timestamp_seconds,
    parse_date_to_next_utc_day_timestamp,
    parse_duration_seconds,
    parse_iso_datetime_to_timestamp,
)
from ..exceptions import CondaValueError

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from typing import Any

    from ..models.records import PackageRecord


@dataclass(frozen=True)
class _CutoffParser:
    """Resolve user-provided cutoff values into absolute POSIX timestamps."""

    now: float

    @staticmethod
    def is_false_override(value: object) -> bool:
        return value is False or (
            isinstance(value, str) and value.strip().casefold() == "false"
        )

    def optional_cutoff(self, value: str | int | float | bool | None) -> float | None:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        if self.is_disabled_cutoff(value):
            return None

        return self.cutoff(value)

    def cutoff(self, value: str | int | float | bool) -> float:
        if isinstance(value, bool):
            raise CondaValueError(
                f"Invalid exclude_newer value {value!r}; "
                "use a duration, date, or timestamp"
            )

        if isinstance(value, (int, float)):
            return self.duration_cutoff(float(value), value)

        raw_value = value.strip()
        if not raw_value:
            raise CondaValueError(
                "Invalid exclude_newer value ''; value must not be empty"
            )

        try:
            duration = parse_duration_seconds(raw_value)
        except ValueError as exc:
            raise self.invalid(raw_value) from exc
        if duration is not None:
            return self.duration_cutoff(duration, raw_value)

        try:
            date_cutoff = parse_date_to_next_utc_day_timestamp(raw_value)
        except ValueError as exc:
            raise self.invalid(raw_value) from exc
        if date_cutoff is not None:
            return date_cutoff

        timestamp = parse_iso_datetime_to_timestamp(raw_value)
        if timestamp is not None:
            return timestamp

        raise self.invalid(raw_value)

    def duration_cutoff(self, duration_seconds: float, value: object) -> float:
        if duration_seconds < 0:
            raise CondaValueError(
                f"Invalid exclude_newer value {value!r}; duration must not be negative"
            )
        return self.now - duration_seconds

    def is_disabled_cutoff(self, value: str | int | float | bool) -> bool:
        if isinstance(value, (int, float)):
            return value == 0

        raw_value = value.strip()
        try:
            duration = parse_duration_seconds(raw_value)
        except ValueError:
            duration = None
        return duration == 0

    @staticmethod
    def invalid(value: str) -> CondaValueError:
        return CondaValueError(
            f"Invalid exclude_newer value {value!r}; use e.g. 7d, P7D, "
            "2026-04-01, or 2026-04-01T12:00:00Z"
        )


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
        parser = _CutoffParser(resolved_now)
        global_cutoff = parser.optional_cutoff(exclude_newer)

        package_cutoffs: dict[str, float | None] = {}
        for package_name, raw_value in sorted((exclude_newer_package or {}).items()):
            if not package_name:
                continue
            if parser.is_false_override(raw_value):
                package_cutoffs[package_name] = None
            elif raw_value is None or raw_value is True:
                continue
            else:
                package_cutoffs[package_name] = parser.cutoff(raw_value)

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
        if (
            package_name
            and self.package_cutoffs
            and package_name in self.package_cutoffs
        ):
            return self.package_cutoffs[package_name]
        return self.global_cutoff

    def should_include(self, record: PackageRecord | Mapping[str, Any]) -> bool:
        if hasattr(record, "get"):
            package_name = record.get("name")
        else:
            package_name = getattr(record, "name", None)
        cutoff = self.cutoff_for(package_name)
        if cutoff is None:
            return True

        timestamp = self.timestamp_for(record)
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

    @staticmethod
    def timestamp_for(record: PackageRecord | Mapping[str, Any]) -> float | None:
        if hasattr(record, "get"):
            value = record.get("indexed_timestamp") or record.get("timestamp")
        else:
            value = getattr(record, "indexed_timestamp", None) or getattr(
                record, "timestamp", None
            )

        if not value:
            return None

        try:
            timestamp = normalize_timestamp_seconds(value)
        except (TypeError, ValueError):
            return None
        return timestamp
