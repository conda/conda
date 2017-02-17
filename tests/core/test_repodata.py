# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals
from logging import getLogger
from unittest import TestCase

from conda.common.disk import temporary_content_in_file
from conda.core.repodata import read_mod_and_etag, cache_fn_url

log = getLogger(__name__)


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

