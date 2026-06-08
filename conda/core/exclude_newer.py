# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Helpers for applying the ``exclude_newer`` package policy."""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
from time import time
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from ..common.datetime import (
    DateOnlyBehavior,
    normalize_timestamp_seconds,
    parse_datetime_to_timestamp,
    parse_duration,
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
            duration = parse_duration(raw_value)
        except ValueError as exc:
            raise self.invalid(raw_value) from exc
        if duration is not None:
            return self.duration_cutoff(duration.total_seconds(), raw_value)

        try:
            timestamp = parse_datetime_to_timestamp(
                raw_value,
                date_only=DateOnlyBehavior.NEXT_UTC_DAY,
            )
        except ValueError as exc:
            raise self.invalid(raw_value) from exc
        if timestamp is not None:
            return timestamp

        raise self.invalid(raw_value)

    def duration_cutoff(self, duration_seconds: float, value: object) -> float:
        if duration_seconds < 0:
            raise CondaValueError(
                f"Invalid exclude_newer value {value!r}; duration must not be negative"
            )
        return self.now - duration_seconds

    @staticmethod
    def invalid(value: str) -> CondaValueError:
        return CondaValueError(
            f"Invalid exclude_newer value {value!r}; use e.g. 7d, P7D, "
            "2026-04-01, or 2026-04-01T12:00:00Z"
        )


@dataclass(frozen=True)
class ChannelSelector:
    """Resolved ``channel_settings`` channel selector."""

    URL_GLOB_CHARS = frozenset("*?[")

    value: str
    keys: frozenset[str]
    url_pattern: tuple[str, str] | None

    @classmethod
    def from_value(cls, value: str) -> ChannelSelector:
        return cls(
            value=value,
            keys=cls.keys_for(value),
            url_pattern=(
                cls.url_match_parts(value)
                if cls.URL_GLOB_CHARS.intersection(value)
                else None
            ),
        )

    def matches(self, record: PackageRecord | Mapping[str, Any]) -> bool:
        record_keys = self.keys_for_record(record)
        if self.keys.intersection(record_keys):
            return True

        if not self.url_pattern:
            return False

        pattern_scheme, pattern = self.url_pattern
        return any(
            parsed.scheme == pattern_scheme
            and fnmatch(f"{parsed.netloc}{parsed.path}".rstrip("/"), pattern)
            for key in record_keys
            if (parsed := urlparse(key)).scheme
        )

    @classmethod
    def keys_for_record(
        cls, record: PackageRecord | Mapping[str, Any]
    ) -> frozenset[str]:
        keys = set()
        for field in ("channel", "schannel", "url"):
            keys.update(cls.keys_for(ExcludeNewerPolicy.record_value(record, field)))
        return frozenset(keys)

    @classmethod
    def keys_for(cls, value: object) -> frozenset[str]:
        keys = set()
        if normalized := cls.normalize(value):
            keys.add(normalized)

        channel = cls.channel_from(value)
        if channel is None:
            return frozenset(keys)

        for resolved_channel in (channel, *channel.channels):
            for key in (
                resolved_channel.name,
                resolved_channel.canonical_name,
                resolved_channel.base_url,
                resolved_channel.url(with_credentials=False),
                str(resolved_channel),
            ):
                if normalized := cls.normalize(key):
                    keys.add(normalized)

        return frozenset(keys)

    @staticmethod
    def channel_from(value: object):
        if value is None:
            return None

        from ..models.channel import Channel

        try:
            return value if isinstance(value, Channel) else Channel(str(value))
        except Exception:
            return None

    @classmethod
    def url_match_parts(cls, value: object) -> tuple[str, str] | None:
        value = cls.normalize(value)
        if not value:
            return None

        parsed = urlparse(value)
        if not parsed.scheme:
            return None
        return parsed.scheme, f"{parsed.netloc}{parsed.path}".rstrip("/")

    @staticmethod
    def normalize(value: object) -> str | None:
        if value is None:
            return None
        value = str(value).strip().rstrip("/")
        return value or None


@dataclass(frozen=True)
class ChannelCutoff:
    """Resolved channel-specific ``exclude_newer`` cutoff."""

    SETTING_KEYS = ("exclude_newer", "exclude-newer")

    selector: ChannelSelector
    cutoff: float | None

    @classmethod
    def from_settings(
        cls,
        settings: Mapping[str, Any],
        parser: _CutoffParser,
    ) -> ChannelCutoff | None:
        channel = str(settings.get("channel", "")).strip()
        if not channel:
            return None

        missing = object()
        raw_value = missing
        for key in cls.SETTING_KEYS:
            if key in settings:
                raw_value = settings[key]
                break

        if raw_value is missing or raw_value is None or raw_value is True:
            return None

        if parser.is_false_override(raw_value):
            cutoff = None
        else:
            cutoff = parser.optional_cutoff(raw_value)
            if cutoff is None:
                return None

        return cls(ChannelSelector.from_value(channel), cutoff)

    def matches(self, record: PackageRecord | Mapping[str, Any]) -> bool:
        return self.selector.matches(record)


@dataclass(frozen=True)
class ExcludeNewerPolicy:
    """Resolved ``exclude_newer`` configuration.

    Cutoffs are stored as absolute POSIX timestamps. A package record is included
    when its ``indexed_timestamp`` or ``timestamp`` is missing or older than the
    effective cutoff for that package name.
    """

    global_cutoff: float | None = None
    channel_cutoffs: tuple[ChannelCutoff, ...] = ()
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
            channel_settings=context.channel_settings,
            now=now,
        )

    @classmethod
    def from_values(
        cls,
        exclude_newer: str | int | float | None,
        exclude_newer_package: Mapping[str, str | bool | int | float | None] | None,
        channel_settings: Iterable[Mapping[str, Any]] | None = None,
        now: float | None = None,
    ) -> ExcludeNewerPolicy:
        resolved_now = time() if now is None else now
        parser = _CutoffParser(resolved_now)
        global_cutoff = parser.optional_cutoff(exclude_newer)

        channel_cutoffs = tuple(
            channel_cutoff
            for settings in channel_settings or ()
            if (channel_cutoff := ChannelCutoff.from_settings(settings, parser))
            is not None
        )

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

        if (
            global_cutoff is None
            and not any(cutoff is not None for cutoff in package_cutoffs.values())
            and not any(cutoff.cutoff is not None for cutoff in channel_cutoffs)
        ):
            return cls.disabled()

        return cls(
            global_cutoff=global_cutoff,
            channel_cutoffs=channel_cutoffs,
            package_cutoffs=package_cutoffs,
            now=resolved_now,
        )

    @property
    def active(self) -> bool:
        return (
            self.global_cutoff is not None
            or any(cutoff.cutoff is not None for cutoff in self.channel_cutoffs)
            or any(
                cutoff is not None for cutoff in (self.package_cutoffs or {}).values()
            )
        )

    @property
    def has_global_cutoff(self) -> bool:
        return self.global_cutoff is not None

    @property
    def has_package_overrides(self) -> bool:
        return bool(self.package_cutoffs) and self.active

    @property
    def has_channel_overrides(self) -> bool:
        return bool(self.channel_cutoffs) and self.active

    def cutoff_for(self, package_name: str | None) -> float | None:
        if (
            package_name
            and self.package_cutoffs
            and package_name in self.package_cutoffs
        ):
            return self.package_cutoffs[package_name]
        return self.global_cutoff

    def cutoff_for_record(
        self, record: PackageRecord | Mapping[str, Any]
    ) -> float | None:
        package_name = self.record_value(record, "name")
        if (
            package_name
            and self.package_cutoffs
            and package_name in self.package_cutoffs
        ):
            return self.package_cutoffs[package_name]

        for channel_cutoff in reversed(self.channel_cutoffs):
            if channel_cutoff.matches(record):
                return channel_cutoff.cutoff

        return self.global_cutoff

    def should_include(self, record: PackageRecord | Mapping[str, Any]) -> bool:
        cutoff = self.cutoff_for_record(record)
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
        value = ExcludeNewerPolicy.record_value(
            record, "indexed_timestamp"
        ) or ExcludeNewerPolicy.record_value(record, "timestamp")

        if not value:
            return None

        try:
            timestamp = normalize_timestamp_seconds(value)
        except (TypeError, ValueError):
            return None
        return timestamp

    @staticmethod
    def record_value(record: PackageRecord | Mapping[str, Any], key: str) -> Any:
        if hasattr(record, "get"):
            return record.get(key)
        return getattr(record, key, None)
