# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger

from .._vendor.auxlib.entity import (BooleanField, ComposableField, DictSafeMixin, Entity,
                                     EnumField, IntegerField, ListField, StringField)
from ..base.constants import Arch, Platform
from ..common.compat import string_types

log = getLogger(__name__)


class Link(DictSafeMixin, Entity):
    source = StringField()
    type = StringField()


EMPTY_LINK = Link(source='', type='')

# TODO: eventually stop mixing Record with LinkedPackageData
# class LinkedPackageData(DictSafeMixin, Entity):
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


class Record(DictSafeMixin, Entity):
    arch = EnumField(Arch, required=False, nullable=True)
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
    # TODO: noarch should support being a string or bool
    noarch = StringField(required=False)
    platform = EnumField(Platform, required=False, nullable=True)
    requires = ListField(string_types, required=False)
    size = IntegerField(required=False)
    subdir = StringField(required=False)
    track_features = StringField(required=False)
    version = StringField()

    fn = StringField(required=False)
    schannel = StringField(required=False, nullable=True)
    channel = StringField(required=False, nullable=True)
    priority = IntegerField(required=False)
    url = StringField(required=False, nullable=True)

    files = ListField(string_types, required=False)
    link = ComposableField(Link, required=False)
