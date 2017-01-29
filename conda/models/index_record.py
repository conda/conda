# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from conda._vendor.auxlib.decorators import memoizedproperty
from conda.base.constants import UNKNOWN_CHANNEL

from .enums import LinkType, NoarchType, Platform
from .._vendor.auxlib.entity import (BooleanField, ComposableField, DictSafeMixin, Entity,
                                     EnumField, ImmutableEntity, IntegerField, ListField,
                                     MapField, StringField)
from ..common.compat import string_types


class LinkTypeField(EnumField):
    def box(self, instance, val):
        if isinstance(val, string_types):
            val = val.replace('-', '').replace('_', '').lower()
            if val == 'hard':
                val = LinkType.hardlink
            elif val == 'soft':
                val = LinkType.softlink
        return super(LinkTypeField, self).box(instance, val)


class NoarchField(EnumField):
    def box(self, instance, val):
        return super(NoarchField, self).box(instance, NoarchType.coerce(val))


class Link(DictSafeMixin, Entity):
    source = StringField()
    type = LinkTypeField(LinkType, required=False)


EMPTY_LINK = Link(source='')

# TODO: eventually stop mixing Record with LinkedPackageData
# class LinkedPackageRecord(DictSafeMixin, Entity):
#     arch = EnumField(Arch, nullable=True)
#     build = StringField()
#     build_number = IntegerField()
#     channel = StringField(required=False)
#     date = StringField(required=False)
#     depends = ListField(string_types)
#     files = ListField(string_types, required=False)
#     license = StringField(required=False)
#     link = ComposableField(Link, required=False)
#     md5 = StringField(required=False, nullable=True)
#     name = StringField()
#     platform = EnumField(Platform)
#     requires = ListField(string_types, required=False)
#     size = IntegerField(required=False)
#     subdir = StringField(required=False)
#     url = StringField(required=False)
#     version = StringField()


class IndexRecord(DictSafeMixin, Entity):  # rename to IndexRecord
    _lazy_validate = True

    arch = StringField(required=False, nullable=True)
    build = StringField()
    build_number = IntegerField()
    date = StringField(required=False)
    depends = ListField(string_types, required=False)
    features = StringField(required=False)
    has_prefix = BooleanField(required=False)
    license = StringField(required=False)
    license_family = StringField(required=False)
    md5 = StringField(required=False, nullable=True)
    name = StringField()
    noarch = NoarchField(NoarchType, required=False, nullable=True)
    platform = EnumField(Platform, required=False, nullable=True)
    requires = ListField(string_types, required=False)
    size = IntegerField(required=False)
    subdir = StringField(required=False)
    track_features = StringField(required=False)
    version = StringField()

    fn = StringField(required=False, nullable=True)
    schannel = StringField(required=False, nullable=True)
    channel = StringField(required=False, nullable=True)
    priority = IntegerField(required=False)
    url = StringField(required=False, nullable=True)
    auth = StringField(required=False, nullable=True)

    files = ListField(string_types, default=(), required=False)
    link = ComposableField(Link, required=False)

    with_features_depends = MapField(required=False)
    preferred_env = StringField(default=None, required=False, nullable=True)

    @memoizedproperty
    def pkey(self):
        if self.schannel:
            dist = "%s::%s-%s-%s" % (self.schannel, self.name, self.version, self.build)
        else:
            dist = "%s-%s-%s" % (self.name, self.version, self.build)
        if self.with_features_depends:
            # TODO: might not be quite right
            dist += "[%s]" % self.with_features_depends
        return dist

    @property
    def dist_name(self):
        return self.pkey.split('::')[-1]

    def __hash__(self):
        return hash(self.pkey)

    def __eq__(self, other):
        return hash(self) == hash(other)
