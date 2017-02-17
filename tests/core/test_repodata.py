# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
from unittest import TestCase

import pytest

from conda.base.context import context, reset_context
from conda.common.compat import iteritems
from conda.common.disk import temporary_content_in_file
from conda.common.io import env_var
from conda.core.index import get_index
from conda.core.repodata import Response304ContentUnchanged, cache_fn_url, read_mod_and_etag

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

log = getLogger(__name__)


def platform_in_record(platform, record):
    return ("/%s/" % platform in record.url) or ("/noarch/" in record.url)


@pytest.mark.integration
class GetRepodataIntegrationTests(TestCase):

    def test_get_index_no_platform_with_offline_cache(self):
        import conda.core.repodata
        with env_var('CONDA_REPODATA_TIMEOUT_SECS', '0', reset_context):
            with patch.object(conda.core.repodata, 'read_mod_and_etag') as read_mod_and_etag:
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
                with patch.object(conda.core.repodata, 'fetch_repodata_remote_request') as remote_request:
                    index2 = get_index(channel_urls=channel_urls, prepend=False, unknown=unknown)
                    assert all(index2.get(k) == rec for k, rec in iteritems(index))
                    assert unknown is not False or len(index) == len(index2)
                    assert remote_request.call_count == 0

        for unknown in (False, True):
            with env_var('CONDA_REPODATA_TIMEOUT_SECS', '0', reset_context):
                with patch.object(conda.core.repodata, 'fetch_repodata_remote_request') as remote_request:
                    remote_request.side_effect = Response304ContentUnchanged()
                    index3 = get_index(channel_urls=channel_urls, prepend=False, unknown=unknown)
                    assert all(index3.get(k) == rec for k, rec in iteritems(index))
                    assert unknown or len(index) == len(index3)


class StaticFunctionTests(TestCase):

    def test_read_mod_and_etag_mod_only(self):
        mod_only_str = """
        {
          "_mod": "Wed, 14 Dec 2016 18:49:16 GMT",
          "_url": "https://conda.anaconda.org/conda-canary/noarch",
          "info": {
            "arch": null,
            "default_numpy_version": "1.7",
            "default_python_version": "2.7",
            "platform": null,
            "subdir": "noarch"
          },
          "packages": {}
        }
        """.strip()
        with temporary_content_in_file(mod_only_str) as path:
            mod_etag_dict = read_mod_and_etag(path)
            assert "_etag" not in mod_etag_dict
            assert mod_etag_dict["_mod"] == "Wed, 14 Dec 2016 18:49:16 GMT"

    def test_read_mod_and_etag_etag_only(self):
        etag_only_str = """
        {
          "_url": "https://repo.continuum.io/pkgs/r/noarch",
          "info": {},
          "_etag": "\"569c0ecb-48\"",
          "packages": {}
        }
        """.strip()
        with temporary_content_in_file(etag_only_str) as path:
            mod_etag_dict = read_mod_and_etag(path)
            assert "_mod" not in mod_etag_dict
            assert mod_etag_dict["_etag"] == "\"569c0ecb-48\""

    def test_read_mod_and_etag_etag_mod(self):
        etag_mod_str = """
        {
          "_etag": "\"569c0ecb-48\"",
          "_mod": "Sun, 17 Jan 2016 21:59:39 GMT",
          "_url": "https://repo.continuum.io/pkgs/r/noarch",
          "info": {},
          "packages": {}
        }
        """.strip()
        with temporary_content_in_file(etag_mod_str) as path:
            mod_etag_dict = read_mod_and_etag(path)
            assert mod_etag_dict["_mod"] == "Sun, 17 Jan 2016 21:59:39 GMT"
            assert mod_etag_dict["_etag"] == "\"569c0ecb-48\""

    def test_read_mod_and_etag_mod_etag(self):
        mod_etag_str = """
        {
          "_mod": "Sun, 17 Jan 2016 21:59:39 GMT",
          "_url": "https://repo.continuum.io/pkgs/r/noarch",
          "info": {},
          "_etag": "\"569c0ecb-48\"",
          "packages": {}
        }
        """.strip()
        with temporary_content_in_file(mod_etag_str) as path:
            mod_etag_dict = read_mod_and_etag(path)
            assert mod_etag_dict["_mod"] == "Sun, 17 Jan 2016 21:59:39 GMT"
            assert mod_etag_dict["_etag"] == "\"569c0ecb-48\""

    def test_cache_fn_url(self):
        hash1 = cache_fn_url("http://repo.continuum.io/pkgs/free/osx-64/")
        hash2 = cache_fn_url("http://repo.continuum.io/pkgs/free/osx-64")
        assert "aa99d924.json" == hash1 == hash2

        hash3 = cache_fn_url("https://repo.continuum.io/pkgs/free/osx-64/")
        hash4 = cache_fn_url("https://repo.continuum.io/pkgs/free/osx-64")
        assert "d85a531e.json" == hash3 == hash4 != hash1

        hash5 = cache_fn_url("https://repo.continuum.io/pkgs/free/linux-64/")
        assert hash4 != hash5

        hash6 = cache_fn_url("https://repo.continuum.io/pkgs/r/osx-64")
        assert hash4 != hash6

