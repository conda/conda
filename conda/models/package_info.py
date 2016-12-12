# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger

from .enums import FileMode
from .record import Record
from .._vendor.auxlib.entity import (BooleanField, ComposableField, Entity, EnumField,
                                     IntegerField, ListField, StringField)
from ..common.compat import string_types
from ..models.channel import Channel
from ..models.enums import PathType

log = getLogger(__name__)


class Noarch(Entity):
    type = StringField()
    entry_points = ListField(string_types, required=False)


class PreferredEnv(Entity):
    name = StringField()
    executable_paths = ListField(string_types, required=False)


class PackageMetadata(Entity):
    version = IntegerField()
    noarch = ComposableField(Noarch, required=False)
    preferred_env = ComposableField(PreferredEnv, required=False)


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
    channel = ComposableField(Channel)
    repodata_record = ComposableField(Record)
    url = StringField()

    # attributes within the package tarball
    paths_version = IntegerField()   # from info/paths.json
    paths = ListField(PathInfo)  # from info/paths.json
    index_json_record = ComposableField(Record)
    icondata = StringField(required=False, nullable=True)
    package_metadata = ComposableField(Noarch, required=False, nullable=True)
