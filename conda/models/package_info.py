# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import namedtuple
from logging import getLogger

from .._vendor.auxlib.entity import Entity, ListField
from ..common.compat import string_types

log = getLogger(__name__)


PackageInfoContents = namedtuple('PackageInfoContents',
                                 ('files', 'has_prefix_files', 'no_link', 'soft_links',
                                  'index_json_record', 'icondata', 'noarch'))


class PackageInfo(Entity):

    file = ListField(string_types)
    # TODO: finish this
