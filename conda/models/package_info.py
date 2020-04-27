# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger

from .channel import Channel
from .records import LinkMetadata, PackageRecord, PathsData
from .._vendor.auxlib.entity import ComposableField, ImmutableEntity, StringField

log = getLogger(__name__)




class PackageInfo(ImmutableEntity):

    # attributes external to the package tarball
    extracted_package_dir = StringField()
    package_tarball_full_path = StringField()
    channel = ComposableField(Channel)
    repodata_record = ComposableField(PackageRecord)
    url = StringField()

    # attributes within the package tarball
    icondata = StringField(required=False, nullable=True)
    link_metadata = ComposableField(LinkMetadata, required=False, nullable=True,
                                    default=None, default_in_dump=False)
    paths_data = ComposableField(PathsData)

    def dist_str(self):
        return "%s::%s-%s-%s" % (self.channel.canonical_name, self.name, self.version, self.build)

    @property
    def name(self):
        return self.repodata_record.name

    @property
    def version(self):
        return self.repodata_record.version

    @property
    def build(self):
        return self.repodata_record.build

    @property
    def build_number(self):
        return self.repodata_record.build_number

    @property
    def noarch_type(self):
        return self.link_metadata and self.link_metadata.noarch or None

