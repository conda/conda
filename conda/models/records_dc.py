# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""A19 PoC: @dataclass(slots=True) replacement for auxlib.Entity-based records.

Drop-in replacement for PackageRecord, PackageCacheRecord, SolvedRecord,
and PrefixRecord with identical public API but dramatically faster
instantiation, dump(), and from_objects().

This module can be imported alongside the original records.py for
benchmarking without modifying production code.
"""

from __future__ import annotations

import enum
import json  # noqa: TID251
import sys
from dataclasses import MISSING, dataclass, field, fields
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

from .channel import Channel
from .enums import NoarchType, PackageType, PathEnum, Platform

SENTINEL = object()

TS_BOUNDARY = 253402300799  # 9999-12-31 in epoch seconds

CACHE_FIELDS = frozenset({"_pkey_cache", "_hash_cache", "_memoized_md5"})

FIELDS_EXCLUDED_FROM_DUMP = frozenset({"metadata"})

FIELDS_WITHOUT_DEFAULT_IN_DUMP = frozenset(
    {
        "md5",
        "legacy_bz2_md5",
        "legacy_bz2_size",
        "url",
        "sha256",
        "track_features",
        "features",
        "noarch",
        "preferred_env",
        "python_site_packages_path",
        "license",
        "license_family",
        "package_type",
        "timestamp",
        "paths_data",
    }
)

NOARCH_TO_PACKAGE_TYPE: dict[NoarchType, PackageType] = {
    NoarchType.generic: PackageType.NOARCH_GENERIC,
    NoarchType.python: PackageType.NOARCH_PYTHON,
}

INTERN_FIELDS = frozenset({"name", "version", "build", "subdir"})


@runtime_checkable
class Dumpable(Protocol):
    def dump(self) -> dict[str, Any]: ...


@cache
def get_field_info(cls: type) -> tuple[tuple[str, Any, Any], ...]:
    """Return (name, default, default_factory) for each public field of *cls*."""
    info: list[tuple[str, Any, Any]] = []
    for f in fields(cls):
        if f.name in CACHE_FIELDS:
            continue
        default = f.default if f.default is not MISSING else SENTINEL
        default_factory = (
            f.default_factory if f.default_factory is not MISSING else None
        )
        info.append((f.name, default, default_factory))
    return tuple(info)


@cache
def get_dump_specs(cls: type) -> tuple[tuple[str, bool, Any], ...]:
    """Return (name, include_default, field_default) per dumpable field."""
    specs: list[tuple[str, bool, Any]] = []
    for f in fields(cls):
        if f.name in CACHE_FIELDS or f.name in FIELDS_EXCLUDED_FROM_DUMP:
            continue
        include_default = f.name not in FIELDS_WITHOUT_DEFAULT_IN_DUMP
        default = f.default if f.default is not MISSING else SENTINEL
        specs.append((f.name, include_default, default))
    return tuple(specs)


@cache
def get_known_fields(cls: type) -> frozenset[str]:
    """Return the set of non-cache field names for *cls*."""
    return frozenset(f.name for f in fields(cls) if f.name not in CACHE_FIELDS)


def resolve_channel(val: Any, record: PackageRecordDC) -> Channel | None:
    if val is not None:
        if isinstance(val, Channel):
            return val
        return Channel(val)
    url = record.url
    if url:
        return Channel(url)
    return None


def resolve_subdir(val: Any, record: PackageRecordDC) -> str | None:
    if val is not None:
        return val
    url = record.url
    if url:
        subdir = Channel(url).subdir
        if subdir:
            return subdir
    plat = record.platform
    arch = record.arch
    if plat is not None:
        plat_name = plat.name if isinstance(plat, Platform) else str(plat)
        if not arch:
            return "noarch"
        if "x86" in arch:
            arch = "64" if "64" in arch else "32"
        return f"{plat_name}-{arch}"
    from ..base.context import context

    return context.subdir


def resolve_fn(val: Any, record: PackageRecordDC) -> str:
    if val is not None:
        return val
    url = record.url
    if url:
        fn = Channel(url).package_filename
        if fn:
            return fn
    return f"{record.name}-{record.version}-{record.build}"


def resolve_timestamp(val: Any, record: PackageRecordDC) -> int | float:
    if val and val > TS_BOUNDARY:
        return val / 1000
    return val


def resolve_features(val: Any, record: PackageRecordDC) -> tuple[str, ...]:
    if isinstance(val, tuple):
        return val
    if not val:
        return ()
    if isinstance(val, str):
        val = val.replace(" ", ",").split(",")
    return tuple(f for f in (ff.strip() for ff in val) if f)


def resolve_as_tuple(val: Any, record: PackageRecordDC) -> tuple:
    if isinstance(val, tuple):
        return val
    if not val:
        return ()
    return tuple(val)


def resolve_noarch(val: Any, record: PackageRecordDC) -> NoarchType | None:
    if val is None or isinstance(val, NoarchType):
        return val
    return NoarchType.coerce(val)


def resolve_package_type(val: Any, record: PackageRecordDC) -> PackageType | None:
    if val is None or isinstance(val, PackageType):
        return val
    return PackageType(val)


def resolve_platform(val: Any, record: PackageRecordDC) -> Platform | None:
    if val is None or isinstance(val, Platform):
        return val
    try:
        return Platform(val)
    except ValueError:
        return Platform[val]


def resolve_paths_data(val: Any, record: PrefixRecordDC) -> Any:
    if isinstance(val, dict):
        from .records import PathsData

        return PathsData(**val)
    return val


def dump_channel(val: Any) -> str:
    return str(val) if val else ""


def dump_timestamp(val: Any) -> int:
    if not val:
        return 0
    if val < TS_BOUNDARY:
        val *= 1000
    return int(val)


def dump_features(val: Any) -> str | tuple:
    if isinstance(val, (tuple, list)):
        return " ".join(val) if val else ()
    return val or ()


def dump_enum(val: Any) -> Any:
    return val.value if isinstance(val, enum.Enum) else val


def dump_nested(val: Any) -> Any:
    return val.dump() if isinstance(val, Dumpable) else val


@dataclass(slots=True, init=False, eq=False, repr=False)
class PackageRecordDC:
    """Dataclass replacement for PackageRecord."""

    ALIASES: ClassVar[dict[str, str]] = {
        "build_string": "build",
        "schannel": "channel",
        "filename": "fn",
    }

    FIELD_RESOLVERS: ClassVar[dict[str, Callable]] = {
        "channel": resolve_channel,
        "subdir": resolve_subdir,
        "fn": resolve_fn,
        "timestamp": resolve_timestamp,
        "track_features": resolve_features,
        "features": resolve_features,
        "depends": resolve_as_tuple,
        "constrains": resolve_as_tuple,
        "files": resolve_as_tuple,
        "noarch": resolve_noarch,
        "package_type": resolve_package_type,
        "platform": resolve_platform,
    }

    DUMP_TRANSFORMS: ClassVar[dict[str, Callable]] = {
        "channel": dump_channel,
        "timestamp": dump_timestamp,
        "track_features": dump_features,
        "features": dump_features,
        "platform": dump_enum,
        "noarch": dump_enum,
        "package_type": dump_enum,
        "link": dump_nested,
        "paths_data": dump_nested,
    }

    name: str = ""
    version: str = ""
    build: str = ""
    build_number: int = 0
    channel: Channel | None = None
    subdir: str | None = None
    fn: str | None = None

    md5: str | None = None
    legacy_bz2_md5: str | None = None
    legacy_bz2_size: int | None = None
    url: str | None = None
    sha256: str | None = None

    arch: str | None = None
    platform: Platform | None = None

    depends: tuple[str, ...] = ()
    constrains: tuple[str, ...] = ()
    track_features: tuple[str, ...] = ()
    features: tuple[str, ...] = ()

    noarch: NoarchType | None = None
    preferred_env: str | None = None
    python_site_packages_path: str | None = None
    license: str | None = None
    license_family: str | None = None
    package_type: PackageType | None = None

    timestamp: int | float = 0
    date: str | None = None
    size: int | None = None

    metadata: set[str] = field(default_factory=set, repr=False)

    _pkey_cache: tuple | None = field(
        default=None, repr=False, compare=False, init=False
    )
    _hash_cache: int | None = field(default=None, repr=False, compare=False, init=False)

    def __init__(self, **kwargs: Any) -> None:
        setattr_ = object.__setattr__

        for alias, canonical in self.ALIASES.items():
            if alias in kwargs and canonical not in kwargs:
                kwargs[canonical] = kwargs.pop(alias)

        for name, default, default_factory in get_field_info(self.__class__):
            val = kwargs.get(name, SENTINEL)
            if val is SENTINEL:
                if default_factory is not None:
                    setattr_(self, name, default_factory())
                else:
                    setattr_(self, name, default)
            else:
                setattr_(self, name, val)

        for name, resolve in self.FIELD_RESOLVERS.items():
            val = getattr(self, name, SENTINEL)
            if val is not SENTINEL:
                setattr_(self, name, resolve(val, self))

        for fname in INTERN_FIELDS:
            val = getattr(self, fname, None)
            if isinstance(val, str):
                setattr_(self, fname, sys.intern(val))

        setattr_(self, "_pkey_cache", None)
        setattr_(self, "_hash_cache", None)

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError:
            raise KeyError(item) from None

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)

    @property
    def channel_name(self) -> str | None:
        ch = self.channel
        if ch is None:
            return None
        return getattr(ch, "canonical_name", str(ch))

    def resolve_package_type(self) -> PackageType | None:
        val = self.package_type
        if val is not None:
            return val
        noarch_val = self.noarch
        if noarch_val:
            noarch_coerced = (
                noarch_val
                if isinstance(noarch_val, NoarchType)
                else NoarchType.coerce(noarch_val)
            )
            return NOARCH_TO_PACKAGE_TYPE.get(noarch_coerced)
        return None

    @property
    def _pkey(self) -> tuple:
        cached = self._pkey_cache
        if cached is not None:
            return cached
        ch = self.channel
        ch_name = getattr(ch, "canonical_name", str(ch)) if ch else ""
        pk: list[Any] = [
            ch_name,
            self.subdir,
            self.name,
            self.version,
            self.build_number,
            self.build,
        ]
        from ..base.context import context

        if context.separate_format_cache:
            pk.append(self.fn)
        result = tuple(pk)
        object.__setattr__(self, "_pkey_cache", result)
        return result

    def invalidate_pkey(self) -> None:
        object.__setattr__(self, "_pkey_cache", None)
        object.__setattr__(self, "_hash_cache", None)

    def __hash__(self) -> int:
        cached = self._hash_cache
        if cached is not None:
            return cached
        h = hash(self._pkey)
        object.__setattr__(self, "_hash_cache", h)
        return h

    def __eq__(self, other: object) -> bool:
        return self._pkey == other._pkey  # type: ignore[union-attr]

    def dump(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        transforms = self.DUMP_TRANSFORMS
        for name, include_default, default in get_dump_specs(self.__class__):
            val = getattr(self, name, SENTINEL)
            if val is SENTINEL:
                continue

            if val is None:
                if not include_default:
                    continue
                if default is not SENTINEL and default is None:
                    continue
            if not include_default:
                if (
                    (default is not SENTINEL and val == default)
                    or val == ()
                    or val == 0
                ):
                    continue

            transform = transforms.get(name)
            if transform is not None:
                val = transform(val)

            result[name] = val
        return result

    @classmethod
    def from_objects(cls, *objects: Any, **overrides: Any) -> PackageRecordDC:
        kwargs: dict[str, Any] = {}
        known = get_known_fields(cls)

        for obj in objects:
            if isinstance(obj, dict):
                src = obj
            elif isinstance(obj, Dumpable):
                src = obj.dump()
            elif hasattr(obj, "__dict__"):
                src = obj.__dict__
            elif hasattr(obj, "__slots__"):
                src = {
                    s: getattr(obj, s)
                    for s in obj.__slots__
                    if hasattr(obj, s) and not s.startswith("_")
                }
            else:
                continue
            for k, v in src.items():
                target = cls.ALIASES.get(k, k) if k not in known else k
                if target in known and target not in kwargs and v is not None:
                    kwargs[target] = v
        kwargs.update(overrides)
        return cls(**kwargs)

    @classmethod
    def from_json(cls, json_str: str) -> PackageRecordDC:
        return cls(**json.loads(json_str))

    @classmethod
    def load(cls, data_dict: dict[str, Any]) -> PackageRecordDC:
        return cls(**data_dict)

    def __str__(self) -> str:
        ch = self.channel
        ch_name = getattr(ch, "canonical_name", "") if ch else ""
        return f"{ch_name}/{self.subdir}::{self.name}=={self.version}={self.build}"

    def __repr__(self) -> str:
        parts: list[str] = []
        for f_obj in fields(self.__class__):
            if f_obj.name in CACHE_FIELDS or f_obj.name == "metadata":
                continue
            val = getattr(self, f_obj.name, SENTINEL)
            if val is SENTINEL or val is None or val == () or val == "":
                continue
            parts.append(f"{f_obj.name}={val!r}")
        return f"{self.__class__.__name__}({', '.join(parts)})"

    def dist_str(self, canonical_name: bool = True) -> str:
        ch = self.channel
        if ch is None:
            ch_str = ""
        elif canonical_name:
            ch_str = getattr(ch, "canonical_name", str(ch))
        else:
            ch_str = getattr(ch, "name", str(ch))
        subdir = self.subdir
        sub = f"/{subdir}" if subdir else ""
        return f"{ch_str}{sub}::{self.name}-{self.version}-{self.build}"

    def dist_fields_dump(self) -> dict[str, Any]:
        ch = self.channel
        return {
            "base_url": getattr(ch, "base_url", "") if ch else "",
            "build_number": self.build_number,
            "build_string": self.build,
            "channel": getattr(ch, "name", "") if ch else "",
            "dist_name": self.dist_str().split(":")[-1],
            "name": self.name,
            "platform": self.subdir,
            "version": self.version,
        }

    def to_match_spec(self):
        from .match_spec import MatchSpec

        return MatchSpec(
            channel=self.channel,
            subdir=self.subdir,
            name=self.name,
            version=self.version,
            build=self.build,
        )

    def to_simple_match_spec(self):
        from .match_spec import MatchSpec

        return MatchSpec(name=self.name, version=self.version)

    @property
    def is_unmanageable(self) -> bool:
        return self.resolve_package_type() in PackageType.unmanageable_package_types()

    @property
    def combined_depends(self) -> tuple:
        from .match_spec import MatchSpec

        result = {ms.name: ms for ms in MatchSpec.merge(self.depends)}
        for spec in self.constrains or ():
            ms = MatchSpec(spec)
            result[ms.name] = MatchSpec(ms, optional=(ms.name not in result))
        return tuple(result.values())

    @property
    def namekey(self) -> str:
        return f"global:{self.name}"

    @property
    def spec(self) -> str:
        return f"{self.name}={self.version}={self.build}"

    @property
    def spec_no_build(self) -> str:
        return f"{self.name}={self.version}"

    def record_id(self) -> str:
        ch = self.channel
        ch_name = getattr(ch, "name", "") if ch else ""
        return f"{ch_name}/{self.subdir}::{self.name}-{self.version}-{self.build}"

    @classmethod
    def feature(cls, feature_name: str) -> PackageRecordDC:
        from ..base.context import context

        pkg_name = f"{feature_name}@"
        return cls(
            name=pkg_name,
            version="0",
            build="0",
            channel="@",
            subdir=context.subdir,
            md5="12345678901234567890123456789012",
            track_features=(feature_name,),
            build_number=0,
            fn=pkg_name,
        )

    @classmethod
    def virtual_package(
        cls,
        name: str,
        version: str | None = None,
        build_string: str | None = None,
    ) -> PackageRecordDC:
        from ..base.context import context

        return cls(
            package_type=PackageType.VIRTUAL_SYSTEM,
            name=name,
            version=version or "0",
            build_string=build_string or "0",
            channel="@",
            subdir=context.subdir,
            md5="12345678901234567890123456789012",
            build_number=0,
            fn=name,
        )


@dataclass(slots=True, init=False, eq=False, repr=False)
class PackageCacheRecordDC(PackageRecordDC):
    """Dataclass replacement for PackageCacheRecord."""

    package_tarball_full_path: str = ""
    extracted_package_dir: str = ""
    _memoized_md5: str | None = field(
        default=None, repr=False, compare=False, init=False
    )

    @property
    def is_fetched(self) -> bool:
        from ..gateways.disk.read import isfile

        return isfile(self.package_tarball_full_path)

    @property
    def is_extracted(self) -> bool:
        from ..gateways.disk.read import isdir, isfile

        epd = self.extracted_package_dir
        return isdir(epd) and isfile(str(Path(epd) / "info" / "index.json"))

    @property
    def tarball_basename(self) -> str:
        return Path(self.package_tarball_full_path).name

    def calculate_md5sum(self) -> str | None:
        if self._memoized_md5:
            return self._memoized_md5
        if Path(self.package_tarball_full_path).is_file():
            from ..gateways.disk.read import compute_sum

            md5sum = compute_sum(self.package_tarball_full_path, "md5")
            object.__setattr__(self, "_memoized_md5", md5sum)
            return md5sum
        return None


@dataclass(slots=True, init=False, eq=False, repr=False)
class SolvedRecordDC(PackageRecordDC):
    """Dataclass replacement for SolvedRecord."""

    ALIASES: ClassVar[dict[str, str]] = {
        **PackageRecordDC.ALIASES,
        "requested_specs": "_requested_specs",
    }

    requested_spec: str | None = None
    _requested_specs: tuple[str, ...] | None = None

    @property
    def requested_specs(self) -> tuple[str, ...]:
        val = self._requested_specs
        if val:
            return tuple(val)
        spec = self.requested_spec
        if spec:
            return (spec,)
        return ()

    def dump(self) -> dict[str, Any]:
        dumped = PackageRecordDC.dump(self)
        if dumped.get("_requested_specs"):
            dumped["requested_specs"] = dumped.pop("_requested_specs")
        elif spec := dumped.get("requested_spec"):
            dumped["requested_specs"] = [spec]
        return dumped


@dataclass(slots=True, init=False, eq=False, repr=False)
class PrefixRecordDC(SolvedRecordDC):
    """Dataclass replacement for PrefixRecord."""

    FIELD_RESOLVERS: ClassVar[dict[str, Callable]] = {
        **PackageRecordDC.FIELD_RESOLVERS,
        "paths_data": resolve_paths_data,
    }

    package_tarball_full_path: str | None = None
    extracted_package_dir: str | None = None
    files: tuple[str, ...] = ()
    paths_data: Any = None
    link: Any = None
    auth: str | None = None

    def package_size(self, prefix_path: Path) -> int:
        total_size = 0
        meta_file = (
            prefix_path / "conda-meta" / f"{self.name}-{self.version}-{self.build}.json"
        )
        try:
            total_size += meta_file.stat().st_size
        except OSError:
            pass
        if self.paths_data is not None:
            for path_data in self.paths_data.paths:
                if path_data.path_type in (PathEnum.softlink, PathEnum.directory):
                    continue
                if getattr(path_data, "size_in_bytes", None) is not None:
                    total_size += path_data.size_in_bytes
                    continue
                file_path = prefix_path / path_data._path
                try:
                    total_size += file_path.stat().st_size
                except OSError:
                    pass
        return total_size
