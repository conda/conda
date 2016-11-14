# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import namedtuple
from logging import getLogger

from .._vendor.auxlib.entity import Entity, ListField, ComposableField, StringField, MapField
from ..common.compat import string_types
from .record import Record

log = getLogger(__name__)


PackageInfoContents = namedtuple('PackageInfoContents',
                                 ('files', 'has_prefix_files', 'no_link', 'soft_links',
                                  'index_json_record', 'icondata', 'noarch'))


class PackageInfo(Entity):
    files = ListField(string_types)
    has_prefix_files = ListField(string_types)
    no_link = ListField(string_types)
    soft_links = ListField(string_types)
    index_json_record = ComposableField(Record)
    icondata = StringField()
    noarch = MapField()
