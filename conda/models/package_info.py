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


class FileType(Enum):
    hardlink = 1
    softlink = 2
    directory = 4


class PathInfo(Entity):
    path = StringField()
    sha256 = StringField()
    size_in_bytes = IntegerField()
    file_type = EnumField(FileType)
    prefix_placeholder = StringField(required=False)
    file_mode = EnumField(FileMode, required=False)
    no_link = BooleanField(required=False, nullable=True)
    inode_paths = ListField(string_types)


class PackageInfo(Entity):
    files = ListField(PathInfo)
    index_json_record = ComposableField(Record)
    icondata = StringField()
    noarch = ComposableField(NoarchInfo)
