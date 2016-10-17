# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import re

from conda.base.constants import DEFAULTS
from conda.models.record import Record
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
            elif isinstance(value, Record):
                return Dist.from_string(value.fn, channel_override=value.schannel)
            else:
                return Dist.from_string(value)
        else:
            return super(DistType, cls).__call__(*args, **kwargs)


@with_metaclass(DistType)
class Dist(Entity):

    channel = StringField(required=False, nullable=True, immutable=True)
    dist_name = StringField(immutable=True)
    with_features_depends = StringField(required=False, nullable=True, immutable=True)

    def __init__(self, channel, dist_name=None, with_features_depends=None):
        super(Dist, self).__init__(channel=channel, dist_name=dist_name,
                                   with_features_depends=with_features_depends)

    @property
    def full_name(self):
        return self.__str__()

    @property
    def pair(self):
        return self.channel or DEFAULTS, self.dist_name

    @property
    def quad(self):
        # returns: name, version, build_string, channel
        parts = self.dist_name.rsplit('-', 2) + ['', '']
        return parts[0], parts[1], parts[2], self.channel or DEFAULTS

    def build_number(self):
        n = self.quad[2].rsplit('_')[-1] or 0
        return int(n)

    def __str__(self):
        base = "%s::%s" % (self.channel, self.dist_name) if self.channel else self.dist_name
        if self.with_features_depends:
            return "%s[%s]" % (base, self.with_features_depends)
        else:
            return base

    @property
    def is_feature_package(self):
        return self.dist_name.endswith('@')

    def to_filename(self, extension='.tar.bz2'):
        if self.is_feature_package:
            return self.dist_name
        else:
            return self.dist_name + extension

    def to_matchspec(self):
        return ' '.join(self.quad[:3])

    @classmethod
    def from_string(cls, string, channel_override=None):
        string = text_type(string)

        if string.endswith('@'):
            return cls(channel='@', dist_name=string, with_features_depends=None)

        REGEX_STR = (r'(?:([^\s\[\]]+)::)?'        # optional channel
                     r'([^\s\[\]]+)'               # 3.x dist
                     r'(?:\[([a-zA-Z0-9_-]+)\])?'  # with_features_depends
                     )
        channel, original_dist, w_f_d = re.search(REGEX_STR, string).groups()

        if original_dist.endswith('.tar.bz2'):
            original_dist = original_dist[:-8]
        if channel_override:
            channel = channel_override
        elif channel is None:
            channel = DEFAULTS

        return cls(channel=channel, dist_name=original_dist, with_features_depends=w_f_d)

    def __key__(self):
        return (self.channel, self.dist_name, self.with_features_depends)

    def __lt__(self, other):
        return self.__key__() < other.__key__()

    def __gt__(self, other):
        return self.__key__() > other.__key__()

    def __hash__(self):
        return hash(self.__key__())

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__key__() == other.__key__()
