# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
from unittest import TestCase

import pytest

from conda.common.compat import iteritems
from conda.core.index import get_index

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

log = getLogger(__name__)


def platform_in_record(platform, record):
    return ("/%s/" % platform in record.url) or ("/noarch/" in record.url)


@pytest.mark.integration
class GetIndexIntegrationTests(TestCase):

    def test_get_index_linux64_platform(self):
        linux64 = 'linux-64'
        index = get_index(platform=linux64)
        for dist, record in iteritems(index):
            assert platform_in_record(linux64, record), (linux64, record.url)

    def test_get_index_osx64_platform(self):
        osx64 = 'osx-64'
        index = get_index(platform=osx64)
        for dist, record in iteritems(index):
            assert platform_in_record(osx64, record), (osx64, record.url)

    def test_get_index_win64_platform(self):
        win64 = 'win-64'
        index = get_index(platform=win64)
        for dist, record in iteritems(index):
            assert platform_in_record(win64, record), (win64, record.url)


