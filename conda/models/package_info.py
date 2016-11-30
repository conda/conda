# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from conda.models.channel import Channel
from enum import Enum
from logging import getLogger

from .record import Record
from .._vendor.auxlib.entity import (BooleanField, ComposableField, Entity, EnumField,
                                     IntegerField, ListField, StringField)
from ..base.constants import FileMode
from ..common.compat import string_types

log = getLogger(__name__)


class NoarchInfo(Entity):
    type = StringField()
    entry_points = ListField(string_types, required=False)


class PathType(Enum):
    """
    Refers to if the file in question is hard linked or soft linked. Originally designed to be used
    in paths.json
    """
    hardlink = 'hardlink'
    softlink = 'softlink'
    directory = 'directory'

    def __int__(self):
        return self.value

    def __str__(self):
        return self.name


class PathInfo(Entity):
    _path = StringField()
    prefix_placeholder = StringField(required=False, nullable=True)
    file_mode = EnumField(FileMode, required=False, nullable=True)
    no_link = BooleanField(required=False, nullable=True)
    path_type = EnumField(PathType)

    @property
    def path(self):
        # because I don't have aliases as an option for entity fields yet
        return self._path


class PathInfoV1(PathInfo):
    sha256 = StringField()
    size_in_bytes = IntegerField()
    inode_paths = ListField(string_types, required=False, nullable=True)


class PackageInfo(Entity):

    # attributes external to the package tarball
    extracted_package_dir = StringField()
    package_st_dev = IntegerField()  # value of os.lstat(extracted_package_dir).st_dev
    channel = ComposableField(Channel)
    repodata_record = ComposableField(Record)

    # attributes within the package tarball
    paths_version = IntegerField()
    paths = ListField(PathInfo)
    index_json_record = ComposableField(Record)
    icondata = StringField(required=False, nullable=True)
    noarch = ComposableField(NoarchInfo, required=False, nullable=True)  # TODO: this isn't noarch anymore; package_metadata.json
