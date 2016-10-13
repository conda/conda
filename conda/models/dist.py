# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import re

from conda.base.constants import DEFAULTS
from logging import getLogger

from .._vendor.auxlib.entity import Entity, EntityType, StringField
from ..common.compat import text_type, with_metaclass

log = getLogger(__name__)


class DistType(EntityType):

    def __call__(cls, *args, **kwargs):
        if len(args) == 1 and not kwargs:
            value = args[0]
            if isinstance(value, Dist):
                return value
            elif value.__class__.__name__ == "Package":
                return Dist.from_string(value.fn, channel_override=value.schannel)
            else:
                return Dist.from_string(value)
        else:
            return super(DistType, cls).__call__(*args, **kwargs)


@with_metaclass(DistType)
class Dist(Entity):

    channel = StringField(required=False, nullable=True, immutable=True)
    package_name = StringField(immutable=True)
    version = StringField(required=False, immutable=True)
    build_string = StringField(required=False, immutable=True)

    def __init__(self, channel, package_name=None, version=None,
                 build_string=None, with_feature_depends=None):
        self.with_feature_depends = with_feature_depends
        super(Dist, self).__init__(channel=channel, package_name=package_name,
                                   version=version, build_string=build_string)

    @property
    def build_number(self):
        return int(self.build_string.rsplit('_', 1)[-1])

    @property
    def dist_name(self):
        return '-'.join((self.package_name, self.version, self.build_string))

    @property
    def full_name(self):
        return self.__str__()

    @property
    def is_feature_package(self):
        return self.package_name.endswith('@')

    def to_filename(self, extension='.tar.bz2'):
        if self.is_feature_package:
            return self.package_name
        else:
            return self.dist_name + extension

    @classmethod
    def from_string(cls, string, channel_override=None):
        string = text_type(string)

        if string.endswith('@'):
            return cls(channel='@', package_name=string, version='0',
                   build_string='0', with_feature_depends=None)

        REGEX_STR = (r'(?:([^\s\[\]]+)::)?'  # optional channel
                     r'([^\s\[\]]+)'  # 3.x dist
                     r'(?:\[([a-zA-Z0-9_-]+)\])?'  # with_feature_depends
                     )
        channel, original_dist, with_feature_depends = re.search(REGEX_STR, string).groups()

        if original_dist.endswith('.tar.bz2'):
            original_dist = original_dist[:-8]
        if channel_override:
            channel = channel_override
        elif channel is None:
            channel = DEFAULTS

        parts = tuple(text_type(s) for s in original_dist.rsplit('-', 2)) + ('', '')
        package_name, version, build_string = parts[:3]

        return cls(channel=channel, package_name=package_name, version=version or None,
                   build_string=build_string or None, with_feature_depends=with_feature_depends)

    def __key__(self):
        return (self.channel, self.package_name, self.version, self.build_string)

    def __lt__(self, other):
        return self.__key__()[1:] < other.__key__()[1:]

    def __gt__(self, other):
        return self.__key__()[1:] > other.__key__()[1:]

    def __hash__(self):
        return hash(self.__key__())

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__key__() == other.__key__()

    def __str__(self):
        base = "%s::%s" % (self.channel, self.dist_name) if self.channel else self.dist_name
        if self.with_feature_depends:
            return "%s[%s]" % (base, self.with_feature_depends)
        else:
            return base

#
#
# def dist2pair(dist):
#     dist = str(dist)
#     if dist.endswith(']'):
#         dist = dist.split('[', 1)[0]
#     if dist.endswith('.tar.bz2'):
#         dist = dist[:-8]
#     parts = dist.split('::', 1)
#     return 'defaults' if len(parts) < 2 else parts[0], parts[-1]
#
#
# def dist2quad(dist):
#     channel, dist = dist2pair(dist)
#     parts = dist.rsplit('-', 2) + ['', '']
#     return (str(parts[0]), str(parts[1]), str(parts[2]), str(channel))
#
#
# def dist2name(dist):
#     return dist2quad(dist)[0]
#
#
# def name_dist(dist):
#     return dist2name(dist)
#
#
# def dist2filename(dist, suffix='.tar.bz2'):
#     return dist2pair(dist)[1] + suffix
#
#



