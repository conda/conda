# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
                         +----------------+
                         | BasePackageRef |
                         +-------+--------+
                                 |
              +------------+     |     +-----------------+
              | PackageRef <-----+-----> IndexJsonRecord |
              +------+-----+           +-------+---------+
                     |                         |
                     +-----------+-------------+
                                 |
                         +-------v-------+
                         | PackageRecord |
                         +--+---------+--+
+--------------------+      |         |      +--------------+
| PackageCacheRecord <------+         +------> PrefixRecord |
+--------------------+                       +--------------+


"""
from __future__ import absolute_import, division, print_function, unicode_literals

from os.path import basename, join

from .channel import Channel
from .enums import FileMode, LinkType, NoarchType, PackageType, PathType, Platform
from .._vendor.auxlib.entity import (BooleanField, ComposableField, DictSafeMixin, Entity,
                                     EnumField, IntegerField, ListField, NumberField,
                                     StringField)
from ..base.context import context
from ..common.compat import isiterable, itervalues, string_types, text_type
from ..exceptions import PathNotFoundError


NAMESPACES = {
    "python": "python",
    "r-base": "r",
    "mro-base": "r",
    "openjdk": "java",
    "ruby": "ruby",
    "lua": "lua",
    "nodejs": "nodejs",
    "perl": "perl",
}


class LinkTypeField(EnumField):
    def box(self, instance, instance_type, val):
        if isinstance(val, string_types):
            val = val.replace('-', '').replace('_', '').lower()
            if val == 'hard':
                val = LinkType.hardlink
            elif val == 'soft':
                val = LinkType.softlink
        return super(LinkTypeField, self).box(instance, instance_type, val)


class NoarchField(EnumField):
    def box(self, instance, instance_type, val):
        return super(NoarchField, self).box(instance, instance_type, NoarchType.coerce(val))


class TimestampField(NumberField):

    # @staticmethod
    # def _make_seconds(val):
    #     if val:
    #         val = int(val)
    #         if val > 253402300799:  # 9999-12-31
    #             val //= 1000  # convert milliseconds to seconds; see conda/conda-build#1988
    #     return val

    @staticmethod
    def _make_milliseconds(val):
        if val:
            if val < 253402300799:  # 9999-12-31
                val *= 1000  # convert seconds to milliseconds
            val = int(val)
        return val

    def box(self, instance, instance_type, val):
        return self._make_milliseconds(
            super(TimestampField, self).box(instance, instance_type, val)
        )

    def unbox(self, instance, instance_type, val):
        return self._make_milliseconds(
            super(TimestampField, self).unbox(instance, instance_type, val)
        )

    def dump(self, instance, instance_type, val):
        return self._make_milliseconds(
            super(TimestampField, self).dump(instance, instance_type, val)
        )


class Link(DictSafeMixin, Entity):
    source = StringField()
    type = LinkTypeField(LinkType, required=False)


EMPTY_LINK = Link(source='')


class _FeaturesField(ListField):

    def __init__(self, **kwargs):
        super(_FeaturesField, self).__init__(string_types, **kwargs)

    def box(self, instance, instance_type, val):
        if isinstance(val, string_types):
            val = val.replace(' ', ',').split(',')
        val = tuple(f for f in (ff.strip() for ff in val) if f)
        return super(_FeaturesField, self).box(instance, instance_type, val)

    def dump(self, instance, instance_type, val):
        if isiterable(val):
            return ' '.join(val)
        else:
            return val or ()  # default value is (), and default_in_dump=False


class ChannelField(ComposableField):

    def __init__(self, aliases=()):
        super(ChannelField, self).__init__(Channel, required=False, aliases=aliases)

    def dump(self, instance, instance_type, val):
        if val:
            return text_type(val)
        else:
            val = instance.channel  # call __get__
            return text_type(val)

    def __get__(self, instance, instance_type):
        try:
            return super(ChannelField, self).__get__(instance, instance_type)
        except AttributeError:
            url = instance.url
            return self.unbox(instance, instance_type, Channel(url))


class SubdirField(StringField):

    def __init__(self):
        super(SubdirField, self).__init__(required=False)

    def __get__(self, instance, instance_type):
        try:
            return super(SubdirField, self).__get__(instance, instance_type)
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
                return self.unbox(instance, instance_type, 'noarch')
            elif platform:
                if 'x86' in arch:
                    arch = '64' if '64' in arch else '32'
                return self.unbox(instance, instance_type, '%s-%s' % (platform, arch))
            else:
                return self.unbox(instance, instance_type, context.subdir)


class NamespaceField(StringField):

    def __init__(self):
        super(NamespaceField, self).__init__(required=False)

    def __get__(self, instance, instance_type):
        try:
            return super(NamespaceField, self).__get__(instance, instance_type)
        except AttributeError:
            from .match_spec import MatchSpec
            spaces = {MatchSpec(spec).name for spec in instance.depends} & set(NAMESPACES)
            len_spaces = len(spaces)
            if len_spaces == 0:
                return "global"
            elif len_spaces == 1:
                return NAMESPACES[next(iter(spaces))]
            else:
                raise NotImplementedError()


class FilenameField(StringField):

    def __init__(self, aliases=()):
        super(FilenameField, self).__init__(required=False, aliases=aliases)

    def __get__(self, instance, instance_type):
        try:
            return super(FilenameField, self).__get__(instance, instance_type)
        except AttributeError:
            try:
                url = instance.url
                fn = Channel(url).package_filename
                if not fn:
                    raise AttributeError()
            except AttributeError:
                fn = '%s-%s-%s' % (instance.name, instance.version, instance.build)
            assert fn
            return self.unbox(instance, instance_type, fn)


class PackageTypeField(EnumField):

    def __init__(self):
        super(PackageTypeField, self).__init__(PackageType, required=False, nullable=True,
                                               default=None, default_in_dump=False)

    def __get__(self, instance, instance_type):
        val = super(PackageTypeField, self).__get__(instance, instance_type)
        if val is None:
            # look in noarch field
            noarch_val = instance.noarch
            if noarch_val:
                type_map = {
                    NoarchType.generic: PackageType.NOARCH_GENERIC,
                    NoarchType.python: PackageType.NOARCH_PYTHON,
                }
                val = type_map[NoarchType.coerce(noarch_val)]
                val = self.unbox(instance, instance_type, val)
        return val


class PathData(Entity):
    _path = StringField()
    prefix_placeholder = StringField(required=False, nullable=True, default=None,
                                     default_in_dump=False)
    file_mode = EnumField(FileMode, required=False, nullable=True)
    no_link = BooleanField(required=False, nullable=True, default=None, default_in_dump=False)
    path_type = EnumField(PathType)

    @property
    def path(self):
        # because I don't have aliases as an option for entity fields yet
        return self._path


class PathDataV1(PathData):
    # TODO: sha256 and size_in_bytes should be required for all PathType.hardlink, but not for softlink and directory  # NOQA
    sha256 = StringField(required=False, nullable=True)
    size_in_bytes = IntegerField(required=False, nullable=True)
    inode_paths = ListField(string_types, required=False, nullable=True)

    sha256_in_prefix = StringField(required=False, nullable=True)


class PathsData(Entity):
    # from info/paths.json
    paths_version = IntegerField()
    paths = ListField(PathData)


class PackageRecord(DictSafeMixin, Entity):
    name = StringField()
    version = StringField()
    build = StringField(aliases=('build_string',))
    build_number = IntegerField()

    # the canonical code abbreviation for PackageRef is `pref`
    # fields required to uniquely identifying a package

    channel = ChannelField(aliases=('schannel',))
    subdir = SubdirField()
    fn = FilenameField(aliases=('filename',))

    md5 = StringField(default=None, required=False, nullable=True, default_in_dump=False)
    url = StringField(default=None, required=False, nullable=True, default_in_dump=False)

    @property
    def schannel(self):
        return self.channel.canonical_name

    @property
    def _pkey(self):
        try:
            return self.__pkey
        except AttributeError:
            __pkey = self.__pkey = (self.channel.canonical_name, self.subdir, self.name,
                                    self.version, self.build_number, self.build)
            return __pkey

    def __hash__(self):
        return hash(self._pkey)

    def __eq__(self, other):
        return self._pkey == other._pkey

    def dist_str(self):
        return "%s::%s-%s-%s" % (self.channel.canonical_name, self.name, self.version, self.build)


    arch = StringField(required=False, nullable=True)  # so legacy
    platform = EnumField(Platform, required=False, nullable=True)  # so legacy

    depends = ListField(string_types, default=())
    constrains = ListField(string_types, default=())

    track_features = _FeaturesField(required=False, default=(), default_in_dump=False)
    features = _FeaturesField(required=False, default=(), default_in_dump=False)

    noarch = NoarchField(NoarchType, required=False, nullable=True, default=None,
                         default_in_dump=False)  # TODO: rename to package_type
    preferred_env = StringField(required=False, nullable=True, default=None, default_in_dump=False)

    license = StringField(required=False, nullable=True, default=None, default_in_dump=False)
    license_family = StringField(required=False, nullable=True, default=None,
                                 default_in_dump=False)
    package_type = PackageTypeField()

    timestamp = TimestampField(required=False)

    namespace = NamespaceField()

    @property
    def combined_depends(self):
        from .match_spec import MatchSpec
        result = {ms.name: ms for ms in MatchSpec.merge(self.depends)}
        result.update({ms.name: ms for ms in MatchSpec.merge(
            MatchSpec(spec, optional=True) for spec in self.constrains or ()
        )})
        return tuple(itervalues(result))


# conflicting attribute due to subdir on both IndexJsonRecord and PackageRef
# probably unavoidable for now

    # the canonical code abbreviation for PackageRecord is `prec`, not to be confused with
    # PackageCacheRecord (`pcrec`) or PrefixRecord (`prefix_rec`)
    #
    # important for "choosing" a package (i.e. the solver), listing packages
    # (like search), and for verifying downloads
    #
    # this is the highest level of the record inheritance model that MatchSpec is designed to
    # work with

    date = StringField(required=False)
    size = IntegerField(required=False)

    def __str__(self):
        return "%s/%s::%s==%s=%s" % (self.channel.canonical_name, self.subdir, self.name,
                                     self.version, self.build)


class Md5Field(StringField):

    def __init__(self):
        super(Md5Field, self).__init__(required=False, nullable=True)

    def __get__(self, instance, instance_type):
        try:
            return super(Md5Field, self).__get__(instance, instance_type)
        except AttributeError as e:
            try:
                return instance._calculate_md5sum()
            except PathNotFoundError:
                raise e


class PackageCacheRecord(PackageRecord):

    package_tarball_full_path = StringField()
    extracted_package_dir = StringField()

    md5 = Md5Field()

    @property
    def is_fetched(self):
        from ..gateways.disk.read import isfile
        return isfile(self.package_tarball_full_path)

    @property
    def is_extracted(self):
        from ..gateways.disk.read import isdir, isfile
        epd = self.extracted_package_dir
        return isdir(epd) and isfile(join(epd, 'info', 'index.json'))

    @property
    def tarball_basename(self):
        return basename(self.package_tarball_full_path)

    def _calculate_md5sum(self):
        memoized_md5 = getattr(self, '_memoized_md5', None)
        if memoized_md5:
            return memoized_md5

        from os.path import isfile
        if isfile(self.package_tarball_full_path):
            from ..gateways.disk.read import compute_md5sum
            md5sum = compute_md5sum(self.package_tarball_full_path)
            setattr(self, '_memoized_md5', md5sum)
            return md5sum


class PrefixRecord(PackageRecord):

    package_tarball_full_path = StringField(required=False)
    extracted_package_dir = StringField(required=False)

    files = ListField(string_types, default=(), required=False)
    paths_data = ComposableField(PathsData, required=False, nullable=True, default_in_dump=False)
    link = ComposableField(Link, required=False)
    # app = ComposableField(App, required=False)

    requested_spec = StringField(required=False)

    # There have been requests in the past to save remote server auth
    # information with the package.  Open to rethinking that though.
    auth = StringField(required=False, nullable=True)

    # # a new concept introduced in 4.4 for private env packages
    # leased_paths = ListField(LeasedPathEntry, required=False)

    # @classmethod
    # def load(cls, conda_meta_json_path):
    #     return cls()
