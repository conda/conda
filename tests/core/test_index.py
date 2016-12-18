# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
from time import time
from unittest import TestCase

from conda.connection import CondaSession

from conda.common.io import env_var

from conda.base.context import context, reset_context
from conda.common.compat import iteritems
from conda.common.disk import temporary_content_in_file
from conda.core.index import get_index, read_mod_and_etag, cache_fn_url, \
    Response304ContentUnchanged

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

log = getLogger(__name__)


def platform_in_record(platform, record):
    return ("/%s/" % platform in record.url) or ("/noarch/" in record.url)


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

        with env_var('CONDA_OFFLINE', 'yes', reset_context):
            with patch.object(conda.core.index, 'fetch_repodata_remote_request') as remote_request:
                index2 = get_index(channel_urls=channel_urls, prepend=False)
                assert index2 == index
                assert remote_request.call_count == 0

        with env_var('CONDA_REPODATA_TIMEOUT_SECS', '0', reset_context):
            with patch.object(conda.core.index, 'fetch_repodata_remote_request') as remote_request:
                remote_request.side_effect = Response304ContentUnchanged()
                index3 = get_index(channel_urls=channel_urls, prepend=False)
                assert index3 == index

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
        assert "87c17da0.json" == hash1 == hash2

        hash3 = cache_fn_url("https://repo.continuum.io/pkgs/free/osx-64/")
        hash4 = cache_fn_url("https://repo.continuum.io/pkgs/free/osx-64")
        assert "840cf1fb.json" == hash3 == hash4 != hash1

        hash5 = cache_fn_url("https://repo.continuum.io/pkgs/free/linux-64/")
        assert hash4 != hash5

        hash6 = cache_fn_url("https://repo.continuum.io/pkgs/r/osx-64")
        assert hash4 != hash6

