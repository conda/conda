# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Legacy auxlib.Entity-based field descriptors for ``conda.models.records``.

Kept around one release cycle so that plugins and downstreams importing the
old descriptor names from :mod:`conda.models.records` continue to resolve.
The dataclass-based record classes in :mod:`conda.models.records` no longer
use any of these; they only exist to preserve import-time compatibility for
code that still builds its own :class:`conda.auxlib.entity.Entity` subclasses.

This module is imported lazily via ``deprecated.constant(factory=...)``.
"""

from __future__ import annotations

from boltons.timeutils import dt_to_timestamp, isoparse

from ..auxlib.entity import (
    ComposableField,
    EnumField,
    ListField,
    NumberField,
    StringField,
)
from ..base.context import context
from ..common.compat import isiterable
from ..exceptions import PathNotFoundError
from .channel import Channel
from .enums import NoarchType, PackageType


class NoarchField(EnumField):
    def box(self, instance, instance_type, val):
        return super().box(instance, instance_type, NoarchType.coerce(val))


class TimestampField(NumberField):
    def __init__(self):
        super().__init__(default=0, required=False, default_in_dump=False)

    @staticmethod
    def _make_seconds(val):
        if val:
            val = val
            if val > 253402300799:  # 9999-12-31
                val /= (
                    1000  # convert milliseconds to seconds; see conda/conda-build#1988
                )
        return val

    @staticmethod
    def _make_milliseconds(val):
        if val:
            if val < 253402300799:  # 9999-12-31
                val *= 1000
            val = val
        return val

    def box(self, instance, instance_type, val):
        return self._make_seconds(super().box(instance, instance_type, val))

    def dump(self, instance, instance_type, val):
        return int(self._make_milliseconds(super().dump(instance, instance_type, val)))

    def __get__(self, instance, instance_type):
        try:
            return super().__get__(instance, instance_type)
        except AttributeError:
            try:
                return int(dt_to_timestamp(isoparse(instance.date)))
            except (AttributeError, ValueError):
                return 0


class _FeaturesField(ListField):
    def __init__(self, **kwargs):
        super().__init__(str, **kwargs)

    def box(self, instance, instance_type, val):
        if isinstance(val, str):
            val = val.replace(" ", ",").split(",")
        val = tuple(f for f in (ff.strip() for ff in val) if f)
        return super().box(instance, instance_type, val)

    def dump(self, instance, instance_type, val):
        if isiterable(val):
            return " ".join(val)
        else:
            return val or ()


class ChannelField(ComposableField):
    def __init__(self, aliases=()):
        super().__init__(Channel, required=False, aliases=aliases)

    def dump(self, instance, instance_type, val):
        if val:
            return str(val)
        else:
            val = instance.channel
            return str(val)

    def __get__(self, instance, instance_type):
        try:
            return super().__get__(instance, instance_type)
        except AttributeError:
            url = instance.url
            return self.unbox(instance, instance_type, Channel(url))


class SubdirField(StringField):
    def __init__(self):
        super().__init__(required=False)

    def __get__(self, instance, instance_type):
        try:
            return super().__get__(instance, instance_type)
        except AttributeError:
            try:
                url = instance.url
            except AttributeError:
                url = None
            if url:
                return self.unbox(instance, instance_type, Channel(url).subdir)

            try:
                platform, arch = instance.platform.name, instance.arch
            except AttributeError:
                platform, arch = None, None
            if platform and not arch:
                return self.unbox(instance, instance_type, "noarch")
            elif platform:
                if "x86" in arch:
                    arch = "64" if "64" in arch else "32"
                return self.unbox(instance, instance_type, f"{platform}-{arch}")
            else:
                return self.unbox(instance, instance_type, context.subdir)


class FilenameField(StringField):
    def __init__(self, aliases=()):
        super().__init__(required=False, aliases=aliases)

    def __get__(self, instance, instance_type):
        try:
            return super().__get__(instance, instance_type)
        except AttributeError:
            try:
                url = instance.url
                fn = Channel(url).package_filename
                if not fn:
                    raise AttributeError()
            except AttributeError:
                fn = f"{instance.name}-{instance.version}-{instance.build}"
            if not fn:
                raise ValueError("Filename cannot be empty.")
            return self.unbox(instance, instance_type, fn)


class PackageTypeField(EnumField):
    def __init__(self):
        super().__init__(
            PackageType,
            required=False,
            nullable=True,
            default=None,
            default_in_dump=False,
        )

    def __get__(self, instance, instance_type):
        val = super().__get__(instance, instance_type)
        if val is None:
            noarch_val = instance.noarch
            if noarch_val:
                type_map = {
                    NoarchType.generic: PackageType.NOARCH_GENERIC,
                    NoarchType.python: PackageType.NOARCH_PYTHON,
                }
                val = type_map[NoarchType.coerce(noarch_val)]
                val = self.unbox(instance, instance_type, val)
        return val


class Md5Field(StringField):
    def __init__(self):
        super().__init__(required=False, nullable=True)

    def __get__(self, instance, instance_type):
        try:
            return super().__get__(instance, instance_type)
        except AttributeError as e:
            try:
                return instance._calculate_md5sum()
            except PathNotFoundError:
                raise e
