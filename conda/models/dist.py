# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import namedtuple
from logging import getLogger
import re

from .channel import Channel
from .records import PackageRecord
from .package_info import PackageInfo
from .. import CondaError
from .._vendor.auxlib.entity import Entity, EntityType, IntegerField, StringField
from ..base.constants import CONDA_TARBALL_EXTENSION, DEFAULTS_CHANNEL_NAME, UNKNOWN_CHANNEL
from ..base.context import context
from ..common.compat import ensure_text_type, text_type, with_metaclass
from ..common.constants import NULL
from ..common.url import has_platform, is_url, join_url

log = getLogger(__name__)
DistDetails = namedtuple('DistDetails', ('name', 'version', 'build_string', 'build_number',
                                         'dist_name'))


IndexRecord = PackageRecord  # for conda-build backward compat


class DistType(EntityType):

    def __call__(cls, *args, **kwargs):
        if len(args) == 1 and not kwargs:
            value = args[0]
            if value in Dist._cache_:
                return Dist._cache_[value]
            elif isinstance(value, Dist):
                dist = value
            elif isinstance(value, PackageRecord):
                dist = Dist.from_string(value.fn, channel_override=value.channel.canonical_name)
            elif hasattr(value, 'dist') and isinstance(value.dist, Dist):
                dist = value.dist
            elif isinstance(value, PackageInfo):
                dist = Dist.from_string(value.repodata_record.fn,
                                        channel_override=value.channel.canonical_name)
            elif isinstance(value, Channel):
                dist = Dist.from_url(value.url())
            else:
                dist = Dist.from_string(value)
            Dist._cache_[value] = dist
            return dist
        else:
            return super(DistType, cls).__call__(*args, **kwargs)


@with_metaclass(DistType)
class Dist(Entity):
    _cache_ = {}
    _lazy_validate = True

    channel = StringField(required=False, nullable=True, immutable=True)

    dist_name = StringField(immutable=True)
    name = StringField(immutable=True)
    version = StringField(immutable=True)
    build_string = StringField(immutable=True)
    build_number = IntegerField(immutable=True)

    base_url = StringField(required=False, nullable=True, immutable=True)
    platform = StringField(required=False, nullable=True, immutable=True)

    def __init__(self, channel, dist_name=None, name=None, version=None, build_string=None,
                 build_number=None, base_url=None, platform=None):
        super(Dist, self).__init__(channel=channel,
                                   dist_name=dist_name,
                                   name=name,
                                   version=version,
                                   build_string=build_string,
                                   build_number=build_number,
                                   base_url=base_url,
                                   platform=platform)

    def to_package_ref(self):
        return PackageRecord(
            channel=self.channel,
            subdir=self.platform,
            name=self.name,
            version=self.version,
            build=self.build_string,
            build_number=self.build_number,
        )

    @property
    def full_name(self):
        return self.__str__()

    @property
    def build(self):
        return self.build_string

    @property
    def subdir(self):
        return self.platform

    @property
    def pair(self):
        return self.channel or DEFAULTS_CHANNEL_NAME, self.dist_name

    @property
    def quad(self):
        # returns: name, version, build_string, channel
        parts = self.dist_name.rsplit('-', 2) + ['', '']
        return parts[0], parts[1], parts[2], self.channel or DEFAULTS_CHANNEL_NAME

    def __str__(self):
        return "%s::%s" % (self.channel, self.dist_name) if self.channel else self.dist_name

    @property
    def is_feature_package(self):
        return self.dist_name.endswith('@')

    @property
    def is_channel(self):
        return bool(self.base_url and self.platform)

    def to_filename(self, extension='.tar.bz2'):
        if self.is_feature_package:
            return self.dist_name
        else:
            return self.dist_name + extension

    def to_matchspec(self):
        return ' '.join(self.quad[:3])

    @classmethod
    def from_string(cls, string, channel_override=NULL):
        string = text_type(string)

        if is_url(string) and channel_override == NULL:
            return cls.from_url(string)

        if string.endswith('@'):
            return cls(channel='@',
                       name=string,
                       version="",
                       build_string="",
                       build_number=0,
                       dist_name=string)

        REGEX_STR = (r'(?:([^\s\[\]]+)::)?'        # optional channel
                     r'([^\s\[\]]+)'               # 3.x dist
                     r'(?:\[([a-zA-Z0-9_-]+)\])?'  # with_features_depends
                     )
        channel, original_dist, w_f_d = re.search(REGEX_STR, string).groups()

        if original_dist.endswith(CONDA_TARBALL_EXTENSION):
            original_dist = original_dist[:-len(CONDA_TARBALL_EXTENSION)]

        if channel_override != NULL:
            channel = channel_override
        if not channel:
            channel = UNKNOWN_CHANNEL

        # enforce dist format
        dist_details = cls.parse_dist_name(original_dist)
        return cls(channel=channel,
                   name=dist_details.name,
                   version=dist_details.version,
                   build_string=dist_details.build_string,
                   build_number=dist_details.build_number,
                   dist_name=original_dist)

    @staticmethod
    def parse_dist_name(string):
        original_string = string
        try:
            string = ensure_text_type(string)

            no_tar_bz2_string = (string[:-len(CONDA_TARBALL_EXTENSION)]
                                 if string.endswith(CONDA_TARBALL_EXTENSION)
                                 else string)

            # remove any directory or channel information
            if '::' in no_tar_bz2_string:
                dist_name = no_tar_bz2_string.rsplit('::', 1)[-1]
            else:
                dist_name = no_tar_bz2_string.rsplit('/', 1)[-1]

            parts = dist_name.rsplit('-', 2)

            name = parts[0]
            version = parts[1]
            build_string = parts[2] if len(parts) >= 3 else ''
            build_number_as_string = ''.join(filter(lambda x: x.isdigit(),
                                                    (build_string.rsplit('_')[-1]
                                                     if build_string else '0')))
            build_number = int(build_number_as_string) if build_number_as_string else 0

            return DistDetails(name, version, build_string, build_number, dist_name)

        except:
            raise CondaError("dist_name is not a valid conda package: %s" % original_string)

    @classmethod
    def from_url(cls, url):
        assert is_url(url), url
        if not url.endswith(CONDA_TARBALL_EXTENSION) and '::' not in url:
            raise CondaError("url '%s' is not a conda package" % url)

        dist_details = cls.parse_dist_name(url)
        if '::' in url:
            url_no_tarball = url.rsplit('::', 1)[0]
            platform = context.subdir
            base_url = url_no_tarball.split('::')[0]
            channel = text_type(Channel(base_url))
        else:
            url_no_tarball = url.rsplit('/', 1)[0]
            platform = has_platform(url_no_tarball, context.known_subdirs)
            base_url = url_no_tarball.rsplit('/', 1)[0] if platform else url_no_tarball
            channel = Channel(base_url).canonical_name if platform else UNKNOWN_CHANNEL

        return cls(channel=channel,
                   name=dist_details.name,
                   version=dist_details.version,
                   build_string=dist_details.build_string,
                   build_number=dist_details.build_number,
                   dist_name=dist_details.dist_name,
                   base_url=base_url,
                   platform=platform)

    def to_url(self):
        if not self.base_url:
            return None
        filename = self.dist_name + CONDA_TARBALL_EXTENSION
        return (join_url(self.base_url, self.platform, filename)
                if self.platform
                else join_url(self.base_url, filename))

    def __key__(self):
        return self.channel, self.dist_name

    def __lt__(self, other):
        assert isinstance(other, self.__class__)
        return self.__key__() < other.__key__()

    def __gt__(self, other):
        assert isinstance(other, self.__class__)
        return self.__key__() > other.__key__()

    def __le__(self, other):
        assert isinstance(other, self.__class__)
        return self.__key__() <= other.__key__()

    def __ge__(self, other):
        assert isinstance(other, self.__class__)
        return self.__key__() >= other.__key__()

    def __hash__(self):
        return hash(self.__key__())

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__key__() == other.__key__()

    def __ne__(self, other):
        return not self.__eq__(other)

    # ############ conda-build compatibility ################

    def split(self, sep=None, maxsplit=-1):
        assert sep == '::'
        return [self.channel, self.dist_name] if self.channel else [self.dist_name]

    def rsplit(self, sep=None, maxsplit=-1):
        assert sep == '-'
        assert maxsplit == 2
        name = '%s::%s' % (self.channel, self.quad[0]) if self.channel else self.quad[0]
        return name, self.quad[1], self.quad[2]

    def startswith(self, match):
        return self.dist_name.startswith(match)

    def __contains__(self, item):
        item = ensure_text_type(item)
        if item.endswith(CONDA_TARBALL_EXTENSION):
            item = item[:-len(CONDA_TARBALL_EXTENSION)]
        return item in self.__str__()

    @property
    def fn(self):
        return self.to_filename()


def dist_str_to_quad(dist_str):
    if dist_str.endswith(CONDA_TARBALL_EXTENSION):
        dist_str = dist_str[:-len(CONDA_TARBALL_EXTENSION)]
    if '::' in dist_str:
        channel_str, dist_str = dist_str.split("::", 1)
    else:
        channel_str = UNKNOWN_CHANNEL
    name, version, build = dist_str.rsplit('-', 2)
    return name, version, build, channel_str
