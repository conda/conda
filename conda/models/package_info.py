# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import namedtuple
from enum import Enum
from logging import getLogger

from .record import Record
from .._vendor.auxlib.entity import (BooleanField, ComposableField, Entity, EnumField,
                                     IntegerField, ListField, StringField)
from ..base.constants import FileMode
from ..common.compat import string_types

log = getLogger(__name__)


PackageInfoContents = namedtuple('PackageInfoContents',
                                 ('files', 'has_prefix_files', 'no_link', 'soft_links',
                                  'index_json_record', 'icondata', 'noarch'))


class NoarchInfo(Entity):
    type = StringField()
    entry_points = ListField(string_types, required=False)


class NodeType(Enum):
    """
    Refers to if the file in question is hard linked or soft linked. Originally designed to be used
    in files.json
    """
    hardlink = 1
    softlink = 2

    @classmethod
    def __call__(cls, value, *args, **kwargs):
        if isinstance(cls, value, *args, **kwargs):
            return cls[value]
        return super(NodeType, cls).__call__(value, *args, **kwargs)

    @classmethod
    def __getitem__(cls, name):
        return cls._member_map_[name.replace('-', '').replace('_', '').lower()]

    def __int__(self):
        return self.value

    def __str__(self):
        return self.name


class PathInfo(Entity):
    path = StringField()
    prefix_placeholder = StringField(required=False)
    file_mode = EnumField(FileMode, required=False)
    no_link = BooleanField(required=False, nullable=True)
    node_type = EnumField(NodeType)


class PathInfoV1(PathInfo):
    sha256 = StringField()
    size_in_bytes = IntegerField()
    inode_paths = ListField(string_types, required=False, nullable=True)


class PackageInfo(Entity):
    path_info_version = IntegerField()
    files = ListField(PathInfo)
    index_json_record = ComposableField(Record)
    icondata = StringField(required=False, nullable=True)
    noarch = ComposableField(NoarchInfo, required=False, nullable=True)
