# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Implements the data model for conda packages.

A PackageRecord is the record of a package present in a channel. A PackageCache is the record of a
downloaded and cached package. A PrefixRecord is the record of a package installed into a conda
environment.

Object inheritance:

.. autoapi-inheritance-diagram:: PackageRecord PackageCacheRecord PrefixRecord
   :top-classes: conda.models.records.PackageRecord
   :parts: 1
"""

from __future__ import annotations

import enum
import json  # noqa: TID251
import sys
from dataclasses import MISSING, dataclass, field, fields, is_dataclass
from functools import cache, partial
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Protocol, runtime_checkable

from ..auxlib.entity import (
    BooleanField,
    DictSafeMixin,
    Entity,
    EnumField,
    IntegerField,
    ListField,
    StringField,
)
from ..auxlib.exceptions import ValidationError
from ..deprecations import deprecated
from .channel import Channel
from .enums import FileMode, LinkType, NoarchType, PackageType, PathEnum, Platform

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from .match_spec import MatchSpec


class LinkTypeField(EnumField):
    def box(self, instance, instance_type, val):
        if isinstance(val, str):
            val = val.replace("-", "").replace("_", "").lower()
            if val == "hard":
                val = LinkType.hardlink
            elif val == "soft":
                val = LinkType.softlink
        return super().box(instance, instance_type, val)


class Link(DictSafeMixin, Entity):
    source = StringField()
    type = LinkTypeField(LinkType, required=False)


EMPTY_LINK = Link(source="")


class PathData(Entity):
    _path = StringField()
    prefix_placeholder = StringField(
        required=False, nullable=True, default=None, default_in_dump=False
    )
    file_mode = EnumField(FileMode, required=False, nullable=True)
    no_link = BooleanField(
        required=False, nullable=True, default=None, default_in_dump=False
    )
    path_type = EnumField(PathEnum)

    @property
    def path(self):
        return self._path


class PathDataV1(PathData):
    sha256 = StringField(required=False, nullable=True)
    size_in_bytes = IntegerField(required=False, nullable=True)
    inode_paths = ListField(str, required=False, nullable=True)

    sha256_in_prefix = StringField(required=False, nullable=True)


class PathsData(Entity):
    paths_version = IntegerField()
    paths = ListField(PathDataV1)


SENTINEL = object()

TS_BOUNDARY = 253402300799  # 9999-12-31 in epoch seconds

REQUIRED_FIELDS = ("name", "version", "build", "build_number")

STRING_FIELDS = frozenset(
    {
        "name",
        "version",
        "build",
        "subdir",
        "fn",
        "md5",
        "legacy_bz2_md5",
        "url",
        "sha256",
        "arch",
        "preferred_env",
        "python_site_packages_path",
        "license",
        "license_family",
        "date",
        "package_tarball_full_path",
        "extracted_package_dir",
        "requested_spec",
        "auth",
    }
)

INTEGER_FIELDS = frozenset({"build_number", "legacy_bz2_size", "size"})

SEQUENCE_FIELDS = frozenset(
    {
        "depends",
        "constrains",
        "flags",
        "track_features",
        "features",
        "files",
        "_requested_specs",
    }
)

PKEY_FIELDS = frozenset(
    {"channel", "subdir", "name", "version", "build_number", "build", "fn"}
)

CACHE_FIELDS = frozenset({"_pkey_cache", "_hash_cache", "_memoized_md5"})

FIELDS_EXCLUDED_FROM_DUMP = frozenset({"metadata"})

FIELDS_WITHOUT_DEFAULT_IN_DUMP = frozenset(
    {
        "md5",
        "legacy_bz2_md5",
        "legacy_bz2_size",
        "url",
        "sha256",
        "flags",
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
        "package_tarball_full_path",
        "extracted_package_dir",
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
    """Return initialization metadata for each constructor field of *cls*."""
    info: list[tuple[str, Any, Any]] = []
    for f in fields(cls):
        if not f.init:
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
    """Return constructor field names for *cls*."""
    return frozenset(f.name for f in fields(cls) if f.init)


def resolve_channel(val: Any, record: PackageRecord) -> Channel | None:
    if val is not None:
        if isinstance(val, Channel):
            return val
        return Channel(val)
    return Channel(record.url)


def resolve_subdir(val: Any, record: PackageRecord) -> str | None:
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


def resolve_fn(val: Any, record: PackageRecord) -> str:
    if val is not None:
        return val
    url = record.url
    if url:
        fn = Channel(url).package_filename
        if fn:
            return fn
    return f"{record.name}-{record.version}-{record.build}"


def resolve_timestamp(val: Any, record: PackageRecord) -> int | float:
    if not val and record.date:
        from boltons.timeutils import dt_to_timestamp, isoparse

        try:
            return int(dt_to_timestamp(isoparse(record.date)))
        except (TypeError, ValueError):
            return 0
    if val and val > TS_BOUNDARY:
        return val / 1000
    return val


def resolve_features(val: Any, record: PackageRecord) -> tuple[str, ...]:
    if isinstance(val, tuple):
        return val
    if not val:
        return ()
    if isinstance(val, str):
        val = val.replace(" ", ",").split(",")
    return tuple(f for f in (ff.strip() for ff in val) if f)


def resolve_as_tuple(
    val: Any,
    record: PackageRecord,
    field_name: str = "sequence",
) -> tuple:
    if isinstance(val, tuple):
        return val
    if not val:
        return ()
    if isinstance(val, str):
        raise ValidationError(field_name, val)
    return tuple(val)


def resolve_optional_tuple(val: Any, record: PackageRecord) -> tuple | None:
    if val is None:
        return None
    return resolve_as_tuple(val, record, "_requested_specs")


def resolve_noarch(val: Any, record: PackageRecord) -> NoarchType | None:
    if val is None or isinstance(val, NoarchType):
        return val
    return NoarchType.coerce(val)


def resolve_package_type(val: Any, record: PackageRecord) -> PackageType | None:
    if val is None or isinstance(val, PackageType):
        return val
    return PackageType(val)


def resolve_platform(val: Any, record: PackageRecord) -> Platform | None:
    if val is None or isinstance(val, Platform):
        return val
    try:
        return Platform(val)
    except ValueError:
        return Platform[val]


def resolve_paths_data(val: Any, record: PrefixRecord) -> Any:
    if isinstance(val, dict):
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


def coerce_and_validate(name: str, val: Any) -> Any:
    """Preserve the scalar validation performed by the old Entity fields."""
    if val is None:
        if name in REQUIRED_FIELDS:
            raise ValidationError(name)
        return val
    if name in STRING_FIELDS:
        if isinstance(val, (int, float, complex)):
            return str(val)
        if not isinstance(val, str):
            raise ValidationError(name, val)
    elif name in INTEGER_FIELDS and not isinstance(val, int):
        raise ValidationError(name, val)
    elif name == "timestamp" and not isinstance(val, (int, float)):
        raise ValidationError(name, val)
    elif name in SEQUENCE_FIELDS and not isinstance(val, tuple):
        raise ValidationError(name, val)
    return val


@dataclass(slots=True, init=False, eq=False, repr=False)
class PackageRecord:
    """Representation of a concrete package archive (tarball or .conda file).

    The subclasses add information for solved, cached, and installed packages,
    but do not add fields to :attr:`_pkey`. Records with the same identity
    fields therefore compare equal and produce the same hash across subclasses.
    """

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
        "depends": partial(resolve_as_tuple, field_name="depends"),
        "constrains": partial(resolve_as_tuple, field_name="constrains"),
        "flags": partial(resolve_as_tuple, field_name="flags"),
        "files": partial(resolve_as_tuple, field_name="files"),
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
    flags: tuple[str, ...] = ()
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

        for name in REQUIRED_FIELDS:
            if name not in kwargs:
                raise ValidationError(
                    name,
                    msg=(
                        f"{self.__class__.__name__} requires a {name} field. "
                        f"Instantiated with {kwargs}"
                    ),
                )

        for name, default, default_factory in get_field_info(self.__class__):
            val = kwargs.get(name, SENTINEL)
            if val is SENTINEL:
                if default_factory is not None:
                    val = default_factory()
                else:
                    val = default
            if name not in self.FIELD_RESOLVERS:
                val = coerce_and_validate(name, val)
            setattr_(self, name, val)

        for f_obj in fields(self.__class__):
            if f_obj.init:
                continue
            if f_obj.default_factory is not MISSING:
                setattr_(self, f_obj.name, f_obj.default_factory())
            elif f_obj.default is not MISSING:
                setattr_(self, f_obj.name, f_obj.default)

        for name, resolve in self.FIELD_RESOLVERS.items():
            val = getattr(self, name, SENTINEL)
            if val is not SENTINEL:
                resolved = (
                    val
                    if name == "timestamp" and name in kwargs and not val
                    else resolve(val, self)
                )
                setattr_(self, name, coerce_and_validate(name, resolved))

        for fname in INTERN_FIELDS:
            val = getattr(self, fname, None)
            if isinstance(val, str):
                setattr_(self, fname, sys.intern(val))

    def __setattr__(self, name: str, value: Any) -> None:
        if resolve := self.FIELD_RESOLVERS.get(name):
            value = resolve(value, self)
        value = coerce_and_validate(name, value)
        object.__setattr__(self, name, value)
        if name in PKEY_FIELDS and hasattr(self, "_pkey_cache"):
            self.invalidate_pkey()

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError:
            raise KeyError(item) from None

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)

    @property
    def channel_name(self) -> str | None:
        """The canonical name of the channel of this package."""
        ch = self.channel
        if ch is None:
            return None
        return getattr(ch, "canonical_name", str(ch))

    def effective_package_type(self) -> PackageType | None:
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
        """Components used for record comparison and hashing.

        The key contains the channel name, subdir, name, version, build number,
        and build string. It also contains the filename when
        :ref:`separate_format_cache <auto-config-reference>` is enabled.
        """
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
        if not hasattr(other, "_pkey"):
            return NotImplemented
        return self._pkey == other._pkey

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
    def from_objects(cls, *objects: Any, **overrides: Any) -> PackageRecord:
        kwargs: dict[str, Any] = {}
        known = get_known_fields(cls)

        for obj in objects:
            if isinstance(obj, dict):
                src = obj
            elif isinstance(obj, Dumpable):
                src = obj.dump()
            elif is_dataclass(obj):
                src = {f.name: getattr(obj, f.name) for f in fields(obj)}
            elif hasattr(obj, "__dict__"):
                src = obj.__dict__
            else:
                src = {
                    name: getattr(obj, name)
                    for name in known | cls.ALIASES.keys()
                    if hasattr(obj, name)
                }
            for k, v in src.items():
                target = cls.ALIASES.get(k, k) if k not in known else k
                if target in known and target not in kwargs and v is not None:
                    kwargs[target] = v
        kwargs.update(overrides)
        return cls(**kwargs)

    @classmethod
    def from_json(cls, json_str: str) -> PackageRecord:
        return cls(**json.loads(json_str))

    @classmethod
    def load(cls, data_dict: dict[str, Any]) -> PackageRecord:
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

    def to_match_spec(self) -> MatchSpec:
        from .match_spec import MatchSpec

        return MatchSpec(
            channel=self.channel,
            subdir=self.subdir,
            name=self.name,
            version=self.version,
            build=self.build,
        )

    def to_simple_match_spec(self) -> MatchSpec:
        from .match_spec import MatchSpec

        return MatchSpec(name=self.name, version=self.version)

    @property
    def is_unmanageable(self) -> bool:
        return self.effective_package_type() in PackageType.unmanageable_package_types()

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
        """Return package spec as ``name=version=build``."""
        return f"{self.name}={self.version}={self.build}"

    @property
    def spec_no_build(self) -> str:
        """Return package spec as ``name=version``."""
        return f"{self.name}={self.version}"

    def record_id(self) -> str:
        # Used only by link.py's change report. This is not an official record
        # identifier until it gains a namespace and a stable format.
        ch = self.channel
        ch_name = getattr(ch, "name", "") if ch else ""
        return f"{ch_name}/{self.subdir}::{self.name}-{self.version}-{self.build}"

    @classmethod
    def feature(cls, feature_name: str) -> PackageRecord:
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
    ) -> PackageRecord:
        """
        Create a virtual package record.

        Args:
            name: The name of the virtual package.
            version: The version of the virtual package, defaults to "0".
            build_string: The build string of the virtual package, defaults to "0".

        Returns:
            A PackageRecord representing the virtual package.
        """
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
class PackageCacheRecord(PackageRecord):
    """Representation of a package in the local package cache.

    This specialization adds the local archive and extracted-directory paths.
    It does not add fields to :attr:`PackageRecord._pkey`, so equal package and
    prefix records continue to compare equal and produce the same hash.
    """

    # Full path to the local package archive.
    package_tarball_full_path: str = ""
    # Full path to the local extracted package directory.
    extracted_package_dir: str = ""
    _memoized_md5: str | None = field(
        default=None, repr=False, compare=False, init=False
    )

    @property
    def is_fetched(self) -> bool:
        """Whether the package archive exists locally."""
        from ..gateways.disk.read import isfile

        return isfile(self.package_tarball_full_path)

    @property
    def is_extracted(self) -> bool:
        """Whether the package has been extracted locally."""
        from ..gateways.disk.read import isdir, isfile

        epd = self.extracted_package_dir
        return isdir(epd) and isfile(str(Path(epd) / "info" / "index.json"))

    @property
    def tarball_basename(self) -> str:
        """The basename of the local package archive."""
        return Path(self.package_tarball_full_path).name

    def calculate_md5sum(self) -> str | None:
        memoized = self._memoized_md5
        if memoized:
            return memoized
        if Path(self.package_tarball_full_path).is_file():
            from ..gateways.disk.read import compute_sum

            md5sum = compute_sum(self.package_tarball_full_path, "md5")
            object.__setattr__(self, "_memoized_md5", md5sum)
            return md5sum
        return None


def _make_md5_auto_compute_property() -> property:
    """Build the backwards-compatible ``md5`` descriptor for PackageCacheRecord.

    The old ``Md5Field`` descriptor hashed the tarball on attribute read when
    the field was unset. That behaviour is kept one release cycle via this
    property; the getter falls through to :meth:`calculate_md5sum` and uses
    the ``deprecated`` framework to nudge callers toward the explicit method.

    The property is attached after the class body because
    ``@dataclass(slots=True)`` strips class attributes whose names match
    inherited fields (``md5`` lives on :class:`PackageRecord`) before
    allocating slots, which otherwise silently drops an inline property.
    Storage stays on the inherited slot so ``record.md5 = "abc"`` keeps
    working.
    """
    slot = PackageRecord.__dict__["md5"]

    def fget(self: PackageCacheRecord) -> str | None:
        value = slot.__get__(self, type(self))
        if value is not None:
            return value
        auto = self.calculate_md5sum()
        if auto is not None:
            deprecated.topic(
                "27.3",
                "27.9",
                topic="Implicit md5 auto-compute on PackageCacheRecord.md5",
                addendum="Call PackageCacheRecord.calculate_md5sum() explicitly instead.",
            )
        return auto

    def fset(self: PackageCacheRecord, value: str | None) -> None:
        slot.__set__(self, value)

    return property(fget, fset)


PackageCacheRecord.md5 = _make_md5_auto_compute_property()


@dataclass(slots=True, init=False, eq=False, repr=False)
class SolvedRecord(PackageRecord):
    """Representation of a package returned as part of a solver solution.

    This sits between :class:`PackageRecord` and :class:`PrefixRecord`, adding
    the requested specs used by lockfiles without requiring an artifact on disk.
    """

    ALIASES: ClassVar[dict[str, str]] = {
        **PackageRecord.ALIASES,
        "requested_specs": "_requested_specs",
    }

    FIELD_RESOLVERS: ClassVar[dict[str, Callable]] = {
        **PackageRecord.FIELD_RESOLVERS,
        "_requested_specs": resolve_optional_tuple,
    }

    # The MatchSpec explicitly requested by the user, if any.
    requested_spec: str | None = None
    # All MatchSpecs explicitly requested by the user, if available.
    _requested_specs: tuple[str, ...] | None = None

    @property
    def requested_specs(self) -> tuple[str, ...]:
        """Return plural requested specs, falling back to ``requested_spec``."""
        val = self._requested_specs
        if val:
            return tuple(val)
        spec = self.requested_spec
        if spec:
            return (spec,)
        return ()

    def dump(self) -> dict[str, Any]:
        """Expose requested specs under their public plural field name."""
        dumped = PackageRecord.dump(self)
        if dumped.get("_requested_specs"):
            dumped["requested_specs"] = list(dumped.pop("_requested_specs"))
        elif spec := dumped.get("requested_spec"):
            dumped["requested_specs"] = [spec]
        return dumped


@dataclass(slots=True, init=False, eq=False, repr=False)
class PrefixRecord(SolvedRecord):
    """Representation of a package installed in a local conda environment.

    This specialization adds paths, link information, and local cache paths.
    It does not add fields to :attr:`PackageRecord._pkey`. Instances are
    generally loaded from JSON files in ``$prefix/conda-meta``.
    """

    FIELD_RESOLVERS: ClassVar[dict[str, Callable]] = {
        **SolvedRecord.FIELD_RESOLVERS,
        "paths_data": resolve_paths_data,
    }

    # Local cache paths, if known.
    package_tarball_full_path: str = ""
    extracted_package_dir: str = ""
    # Files and detailed path/link metadata recorded for the installation.
    files: tuple[str, ...] = ()
    paths_data: Any = None
    link: Any = None
    auth: str | None = None

    def _get_json_fn(self) -> str:
        return f"{self.name}-{self.version}-{self.build}.json"

    def package_size(self, prefix_path: Path) -> int:
        """
        Compute the installed size of this package within a prefix.

        This sums up the size_in_bytes of all non-softlink paths in paths_data,
        and stats the files on disk if size_in_bytes is missing and for the
        package's conda-meta JSON manifest.

        Returns:
            Total size in bytes of all files installed by this package.
        """
        total_size = 0
        meta_file = prefix_path / "conda-meta" / self._get_json_fn()
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


def _legacy_field(name: str) -> type:
    """Lazy-import a deprecated ``auxlib.Entity`` field descriptor by name.

    Used as the ``factory=`` callable in the module-level
    :func:`deprecated.constant` registrations below so that importing
    :mod:`conda.models.records` does not drag ``boltons.timeutils`` et al.
    onto the cold-start path for callers of the new dataclass records.
    """
    from . import _legacy_record_fields

    return getattr(_legacy_record_fields, name)


for _name in (
    "NoarchField",
    "TimestampField",
    "_FeaturesField",
    "ChannelField",
    "SubdirField",
    "FilenameField",
    "PackageTypeField",
    "Md5Field",
):
    deprecated.constant(
        "27.3",
        "27.9",
        _name,
        factory=partial(_legacy_field, _name),
        addendum=(
            "auxlib.Entity-based record field descriptors are no longer used "
            "by conda's record classes; record classes have moved to "
            "``@dataclass(slots=True)``. Subclasses of "
            "``conda.auxlib.entity.Entity`` can keep the descriptor by "
            "vendoring it or by importing the base class from "
            "``conda.auxlib.entity`` directly."
        ),
    )
del _name
