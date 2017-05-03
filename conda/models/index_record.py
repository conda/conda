# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from functools import total_ordering

from .enums import LinkType, NoarchType, Platform
from .leased_path_entry import LeasedPathEntry
from .version import VersionOrder
from .._vendor.auxlib.decorators import memoizedproperty
from .._vendor.auxlib.entity import (BooleanField, ComposableField, DictSafeMixin, Entity,
                                     EnumField, Field, IntegerField, ListField, StringField)
from ..base.constants import MAX_CHANNEL_PRIORITY
from ..base.context import context
from ..common.compat import itervalues, string_types


@total_ordering
class Priority(object):

    def __init__(self, priority):
        self._priority = priority

    def __int__(self):
        return self._priority

    def __lt__(self, other):
        return self._priority < int(other)

    def __eq__(self, other):
        return self._priority == int(other)

    def __repr__(self):
        return "Priority(%d)" % self._priority


class PriorityField(Field):
    _type = (int, Priority)

    def unbox(self, instance, instance_type, val):
        return int(val)


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


class IndexJsonRecord(DictSafeMixin, Entity):
    _lazy_validate = True

    arch = StringField(required=False, nullable=True)
    build = StringField()
    build_number = IntegerField()
    constrains = ListField(string_types, required=False, nullable=True)
    date = StringField(required=False)
    depends = ListField(string_types, required=False, nullable=True)
    features = StringField(required=False)
    has_prefix = BooleanField(required=False)
    license = StringField(required=False)
    license_family = StringField(required=False)
    md5 = StringField(required=False, nullable=True)
    name = StringField()
    noarch = NoarchField(NoarchType, required=False, nullable=True)
    platform = EnumField(Platform, required=False, nullable=True)
    preferred_env = StringField(default=None, required=False, nullable=True)
    size = IntegerField(required=False)
    track_features = StringField(default='', required=False)

    version = StringField()

    @property
    def dist_name(self):
        return "%s-%s-%s" % (self.name, self.version, self.build)


class IndexRecord(IndexJsonRecord):

    fn = StringField()
    schannel = StringField(required=False, nullable=True)
    channel = StringField(required=False, nullable=True)
    priority = PriorityField(required=False)
    auth = StringField(required=False, nullable=True)
    subdir = StringField(required=False)

    # url is optional here for legacy support.
    #   see tests/test_create.py test_dash_c_usage_replacing_python
    url = StringField()
    preferred_env = StringField(default=None, required=False, nullable=True)

    # this is only for LinkedPackageRecord
    leased_paths = ListField(LeasedPathEntry, required=False)

    @property
    def combined_depends(self):
        from .match_spec import MatchSpec
        result = {ms.name: ms for ms in (MatchSpec(spec) for spec in self.depends or ())}
        result.update({ms.name: ms for ms in (MatchSpec(spec, option=True)
                                              for spec in self.constrains or ())})
        return tuple(itervalues(result))

    @memoizedproperty
    def pkey(self):
        if self.name.endswith('@'):
            return self.name
        return "%s::%s" % (self.schannel, self.dist_name) if self.schannel else self.dist_name

    def __hash__(self):
        return hash(self.pkey)

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __key__(self):
        return self.pkey

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

    def __ne__(self, other):
        return not self.__eq__(other)

    def to_filename(self):
        return self.fn


class LinkedPackageRecord(IndexRecord):
    files = ListField(string_types, default=(), required=False)
    link = ComposableField(Link, required=False)
