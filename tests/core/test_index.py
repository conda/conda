# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
from unittest import TestCase

import pytest

from conda.base.context import context, reset_context
from conda.common.compat import iteritems
from conda.common.io import env_var
from conda.core.index import get_index
from conda.core.repodata import Response304ContentUnchanged

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

log = getLogger(__name__)


def platform_in_record(platform, record):
    return ("/%s/" % platform in record.url) or ("/noarch/" in record.url)


@pytest.mark.integration
class GetIndexIntegrationTests(TestCase):

    def test_get_index_no_platform_with_offline_cache(self):
        import conda.core.index
        with env_var('CONDA_REPODATA_TIMEOUT_SECS', '0', reset_context):
            with patch.object(conda.core.index, 'read_mod_and_etag') as read_mod_and_etag:
                read_mod_and_etag.return_value = {}
                channel_urls = ('https://repo.continuum.io/pkgs/pro',)
                with env_var('CONDA_REPODATA_TIMEOUT_SECS', '0', reset_context):
                    this_platform = context.subdir
                    index = get_index(channel_urls=channel_urls, prepend=False)
                    for dist, record in iteritems(index):
                        assert platform_in_record(this_platform, record), (this_platform, record.url)

        # When unknown=True (which is implicity engaged when context.offline is
        # True), there may be additional items in the cache that are included in
        # the index. But where those items coincide with entries already in the
        # cache, they must not change the record in any way. TODO: add one or
        # more packages to the cache so these tests affirmatively exercise
        # supplement_index_from_cache on CI?

        for unknown in (None, False, True):
            with env_var('CONDA_OFFLINE', 'yes', reset_context):
                with patch.object(conda.core.index, 'fetch_repodata_remote_request') as remote_request:
                    index2 = get_index(channel_urls=channel_urls, prepend=False, unknown=unknown)
                    assert all(index2.get(k) == rec for k, rec in iteritems(index))
                    assert unknown is not False or len(index) == len(index2)
                    assert remote_request.call_count == 0

        for unknown in (False, True):
            with env_var('CONDA_REPODATA_TIMEOUT_SECS', '0', reset_context):
                with patch.object(conda.core.index, 'fetch_repodata_remote_request') as remote_request:
                    remote_request.side_effect = Response304ContentUnchanged()
                    index3 = get_index(channel_urls=channel_urls, prepend=False, unknown=unknown)
                    assert all(index3.get(k) == rec for k, rec in iteritems(index))
                    assert unknown or len(index) == len(index3)

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


