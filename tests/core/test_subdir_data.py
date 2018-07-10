# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import defaultdict
from logging import getLogger
from os.path import getsize
from pprint import pprint
from unittest import TestCase

import pytest

from conda.base.context import context, reset_context
from conda.common.compat import iteritems, PY2
from conda.common.disk import temporary_content_in_file
from conda.common.io import env_var, env_vars
from conda.core.index import get_index
from conda.core.subdir_data import Response304ContentUnchanged, SubdirData, cache_fn_url, \
    read_mod_and_etag
from conda.exports import rm_rf
from conda.gateways.disk.read import isfile
from conda.gateways.logging import initialize_logging, set_verbosity
from conda.models.channel import Channel
from tests.helpers import get_index_r_4

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

log = getLogger(__name__)


def platform_in_record(platform, record):
    return record.name.endswith('@') or ("/%s/" % platform in record.url) or ("/noarch/" in record.url)


def test_namespace_query():
    get_index_r_4()
    sd = SubdirData._cache_['https://conda.anaconda.org/channel-4/' + context.subdir]

    def num(generator):
        return len(tuple(generator))

    assert num(sd.query('graphviz')) == 9
    assert num(sd.query('python-graphviz')) == num(sd.query('python:graphviz')) == 6
    assert num(sd.query('perl-graphviz')) == num(sd.query('perl:graphviz')) == 1
    assert num(sd.query('global:graphviz')) == 1

    perl_graphviz_rec = next(sd.query('perl:graphviz'))
    assert perl_graphviz_rec.name == 'graphviz'
    assert perl_graphviz_rec.namespace == 'perl'
    assert perl_graphviz_rec.legacy_name == 'perl-graphviz'

    global_graphviz_rec = next(sd.query('global:graphviz'))
    assert global_graphviz_rec.name == 'graphviz'
    assert global_graphviz_rec.namespace == 'global'
    assert global_graphviz_rec.legacy_name == 'graphviz'


@pytest.mark.integration
class GetRepodataIntegrationTests(TestCase):

    def test_get_index_no_platform_with_offline_cache(self):
        import conda.core.subdir_data
        with env_var('CONDA_REPODATA_TIMEOUT_SECS', '0', reset_context):
            with patch.object(conda.core.subdir_data, 'read_mod_and_etag') as read_mod_and_etag:
                read_mod_and_etag.return_value = {}
                channel_urls = ('https://repo.anaconda.com/pkgs/pro',)
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
                with patch.object(conda.core.subdir_data, 'fetch_repodata_remote_request') as remote_request:
                    index2 = get_index(channel_urls=channel_urls, prepend=False, unknown=unknown)
                    assert all(index2.get(k) == rec for k, rec in iteritems(index))
                    assert unknown is not False or len(index) == len(index2)
                    assert remote_request.call_count == 0

        for unknown in (False, True):
            with env_var('CONDA_REPODATA_TIMEOUT_SECS', '0', reset_context):
                with patch.object(conda.core.subdir_data, 'fetch_repodata_remote_request') as remote_request:
                    remote_request.side_effect = Response304ContentUnchanged()
                    index3 = get_index(channel_urls=channel_urls, prepend=False, unknown=unknown)
                    assert all(index3.get(k) == rec for k, rec in iteritems(index))
                    assert unknown or len(index) == len(index3)

    @pytest.mark.skipif(True, reason="Use with '-s' flag to get package report.")
    def test_report_packages_with_multiple_namespaces(self):
        def make_namespace_groups(precs):
            ns_groups = defaultdict(lambda: defaultdict(list))
            for prec in precs:
                ns_groups[prec.name][prec.namespace].append(prec)
            return ns_groups

        def print_report(channe_str):
            print("\n>>> %s <<<" % channe_str)
            sd = SubdirData(Channel(channe_str)).load()
            namespace_groups = make_namespace_groups(sd._package_records)
            for name, ns_map in namespace_groups.items():
                keys = tuple(ns_map.keys())
                if len(keys) > 1:
                    # import pdb; pdb.set_trace()
                    print(name, keys)

        channels = (
            "pkgs/main/linux-64",
            "pkgs/main/osx-64",
            "pkgs/main/win-64",
            "pkgs/free/linux-64",
            "pkgs/free/osx-64",
            "pkgs/free/win-64",
            "conda-forge/linux-64",
            "conda-forge/osx-64",
            "conda-forge/win-64",
            "bioconda/linux-64",
            "bioconda/osx-64",
            "bioconda/win-64",
            "pkgs/r/linux-64",
            "pkgs/r/osx-64",
            "pkgs/r/win-64",
        )
        for channel_str in channels:
            print_report(channel_str)

        assert 0

    @pytest.mark.skipif(True, reason="Use with '-s' flag to ensure pickled repodata is working correctly.")
    def test_load_subdir_data_profiling(self):
        from conda.cli.main import init_loggers
        with env_vars({'CONDA_LOCAL_REPODATA_TTL': '3600', "CONDA_VERBOSE": "3"}, reset_context):
            init_loggers(context)
            channels = (
                'pkgs/main',
                'pkgs/free',
                'conda-forge',
                'bioconda',
                'pkgs/r',
            )
            subdirs = (
                'linux-64',
                'osx-64',
                'win-64',
            )
            SubdirData._cache_.clear()
            query_result = SubdirData.query_all('graphviz', channels, subdirs)

        pprint(query_result)

        assert 0

    @pytest.mark.xfail(PY2, strict=True,
                       reason="Currently not supporting python2 pickling protocol.")
    def test_write_and_read_pickled_repodata(self):
        initialize_logging()
        set_verbosity(2)
        channel = Channel("pkgs/main/linux-64")
        cache_key = SubdirData.cache_key(channel)
        SubdirData._cache_.pop(cache_key, None)
        sd = SubdirData(channel)
        rm_rf(sd.cache_path_json)
        rm_rf(sd.cache_path_pickle)
        assert not sd._loaded

        sd.load()
        assert sd._loaded
        assert isfile(sd.cache_path_json)
        assert getsize(sd.cache_path_json)
        assert isfile(sd.cache_path_pickle)
        assert getsize(sd.cache_path_pickle)

        mod_etag_headers = read_mod_and_etag(sd.cache_path_json)
        assert sd._read_pickled(mod_etag_headers.get('_etag'), mod_etag_headers.get('_mod'))

        assert sd._pickle_me() is True

        assert len(tuple(sd.query("conda"))) > 1


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
          "_url": "https://repo.anaconda.com/pkgs/r/noarch",
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
          "_url": "https://repo.anaconda.com/pkgs/r/noarch",
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
          "_url": "https://repo.anaconda.com/pkgs/r/noarch",
          "info": {},
          "_etag": "\"569c0ecb-48\"",
          "packages": {}
        }
        """.strip()
        with temporary_content_in_file(mod_etag_str) as path:
            mod_etag_dict = read_mod_and_etag(path)
            assert mod_etag_dict["_mod"] == "Sun, 17 Jan 2016 21:59:39 GMT"
            assert mod_etag_dict["_etag"] == "\"569c0ecb-48\""

    def test_cache_fn_url_repo_continuum_io(self):
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

    def test_cache_fn_url_repo_anaconda_com(self):
        hash1 = cache_fn_url("http://repo.anaconda.com/pkgs/free/osx-64/")
        hash2 = cache_fn_url("http://repo.anaconda.com/pkgs/free/osx-64")
        assert "1e817819.json" == hash1 == hash2

        hash3 = cache_fn_url("https://repo.anaconda.com/pkgs/free/osx-64/")
        hash4 = cache_fn_url("https://repo.anaconda.com/pkgs/free/osx-64")
        assert "3ce78580.json" == hash3 == hash4 != hash1

        hash5 = cache_fn_url("https://repo.anaconda.com/pkgs/free/linux-64/")
        assert hash4 != hash5

        hash6 = cache_fn_url("https://repo.anaconda.com/pkgs/r/osx-64")
        assert hash4 != hash6


# @pytest.mark.integration
# class SubdirDataTests(TestCase):
#
#     def test_basic_subdir_data(self):
#         channel = Channel("https://conda.anaconda.org/conda-test/linux-64")
#         sd = SubdirData(channel)
#         sd.load()
#         print(sd._names_index.keys())
#         assert 0
