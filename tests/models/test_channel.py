# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from conda._vendor.auxlib.ish import dals
from conda.base.constants import RESERVED_CHANNELS
from conda.base.context import context, reset_context
from conda.common.compat import odict
from conda.common.configuration import YamlRawParameter
from conda.common.url import path_to_url
from conda.common.yaml import yaml_load
from conda.models.channel import Channel, UrlChannel, CondaChannelUrl
from conda.utils import on_win
from logging import getLogger
from unittest import TestCase




try:
    from unittest import mock
except ImportError:
    import mock
patch = mock.patch

log = getLogger(__name__)


platform = context.subdir
DEFAULT_URLS = ['https://repo.continuum.io/pkgs/free/%s/' % platform,
                 'https://repo.continuum.io/pkgs/free/noarch/',
                 'https://repo.continuum.io/pkgs/pro/%s/' % platform,
                 'https://repo.continuum.io/pkgs/pro/noarch/']
if on_win:
    DEFAULT_URLS.extend(['https://repo.continuum.io/pkgs/msys2/%s/' % platform,
                          'https://repo.continuum.io/pkgs/msys2/noarch/'])


# class ChannelTests(TestCase):
#
#     def test_channel_cache(self):
#         Channel._reset_state()
#         assert len(Channel._cache_) == 0
#         dc = Channel('defaults')
#         assert len(Channel._cache_) == 1
#         dc1 = Channel('defaults')
#         assert len(Channel._cache_) == 1
#         dc2 = Channel('defaults')
#         assert len(Channel._cache_) == 1
#
#         assert dc1 is dc
#         assert dc2 is dc
#
#         dc3 = Channel(dc)
#         assert len(Channel._cache_) == 1
#         assert dc3 is dc
#
#         ccc = Channel('conda-canary')
#         assert len(Channel._cache_) == 2
#
#         ccc1 = Channel('conda-canary')
#         assert len(Channel._cache_) == 2
#         assert ccc1 is ccc
#
#     def test_default_channel(self):
#         dc = Channel('defaults')
#         # assert isinstance(dc, DefaultChannel)
#
#         assert dc.base_url == 'https://conda.anaconda.org/defaults'
#         assert dc.canonical_name == 'defaults'
#         assert dc.urls == DEFAULT_URLS
#
#         assert dc._scheme == "https"
#         assert dc._netloc == "conda.anaconda.org"
#         assert dc._path == "/defaults"
#         assert dc._platform is None
#
#     def test_url_channel_w_platform(self):
#         channel = Channel('https://repo.continuum.io/pkgs/free/osx-64/')
#         assert isinstance(channel, UrlChannel)
#
#         assert channel._scheme == "https"
#         assert channel._netloc == "repo.continuum.io"
#         assert channel._path == "/pkgs/free"
#         assert channel._platform == 'osx-64'
#
#         assert channel.base_url == 'https://repo.continuum.io/pkgs/free'
#         assert channel.canonical_name == 'defaults'
#         assert channel.urls == DEFAULT_URLS
#
#     def test_url_channel_wo_platform(self):
#         channel = Channel('https://repo.continuum.io/pkgs/free/')
#         assert isinstance(channel, UrlChannel)
#
#         assert channel._scheme == "https"
#         assert channel._netloc == "repo.continuum.io"
#         assert channel._path == "/pkgs/free"
#         assert channel._platform is None
#
#         platform = context.subdir
#         assert channel.base_url == 'https://repo.continuum.io/pkgs/free'
#         assert channel.canonical_name == 'defaults'
#         assert channel.urls == DEFAULT_URLS
#
#     def test_split_platform(self):
#         assert split_platform('/pkgs/free/') == ('/pkgs/free', None)
#         assert split_platform('/pkgs/free') == ('/pkgs/free', None)
#         assert split_platform('/pkgs/free/osx-64/') == ('/pkgs/free', 'osx-64')
#         assert split_platform('/pkgs/free/osx-64') == ('/pkgs/free', 'osx-64')
#
#         assert split_platform('/') == ('/', None)
#         assert split_platform('') == ('/', None)
#         assert split_platform(None) == ('/', None)
#
#     def test_local_channel(self):
#         local = Channel('local')
#         assert local.canonical_name == "local"
#         build_path = path_to_url(context.local_build_root)
#         local_urls = ['%s/%s/' % (build_path, context.subdir),
#                       '%s/noarch/' % build_path]
#         assert local.urls == local_urls
#
#         lc = Channel(build_path)
#         assert lc.canonical_name == "local"
#         assert lc.urls == local_urls
#
#         lc_noarch = Channel(local_urls[1])
#         assert lc_noarch.canonical_name == "local"
#         assert lc_noarch.urls == local_urls
#
#     def test_canonical_name(self):
#         assert Channel('https://repo.continuum.io/pkgs/free').canonical_name == "defaults"
#         assert Channel('http://repo.continuum.io/pkgs/free/linux-64').canonical_name == "defaults"
#         assert Channel('https://conda.anaconda.org/bioconda').canonical_name == "bioconda"
#         assert Channel('http://conda.anaconda.org/bioconda/win-64').canonical_name == "bioconda"
#         assert Channel('http://conda.anaconda.org/bioconda/label/main/osx-64').canonical_name == "bioconda/label/main"
#         assert Channel('http://conda.anaconda.org/t/tk-abc-123-456/bioconda/win-64').canonical_name == "bioconda"
#
#     def test_urls_from_name(self):
#         platform = context.subdir
#         assert Channel("bioconda").urls == ["https://conda.anaconda.org/bioconda/%s/" % platform,
#                                             "https://conda.anaconda.org/bioconda/noarch/"]
#         assert Channel("bioconda/label/dev").urls == [
#             "https://conda.anaconda.org/bioconda/label/dev/%s/" % platform,
#             "https://conda.anaconda.org/bioconda/label/dev/noarch/"]
#
#     def test_regular_url_channels(self):
#         platform = context.subdir
#         c = Channel('https://some.other.com/pkgs/free/')
#         assert c.canonical_name == "https://some.other.com/pkgs/free"
#         assert c.urls == ["https://some.other.com/pkgs/free/%s/" % platform,
#                           "https://some.other.com/pkgs/free/noarch/"]
#
#         c = Channel('https://some.other.com/pkgs/free/noarch')
#         assert c.canonical_name == "https://some.other.com/pkgs/free"
#         assert c.urls == ["https://some.other.com/pkgs/free/%s/" % platform,
#                           "https://some.other.com/pkgs/free/noarch/"]
#
#








platform = context.subdir


class ContextTests(TestCase):

    def setUp(self):
        string = dals("""
        custom_channels:
          darwin: https://some.url.somewhere/stuff
          chuck: http://user1:pass2@another.url:8080/t/tk-1234/with/path
        migrated_custom_channels:
          darwin: s3://just/cant
          chuck: file:///var/lib/repo/
        migrated_channel_aliases:
          - https://conda.anaconda.org
        channel_alias: ftp://new.url:8082
        anaconda_token: tk-123-456-cba
        """)
        reset_context()
        rd = odict(testdata=YamlRawParameter.make_raw_parameters('testdata', yaml_load(string)))
        context._add_raw_data(rd)
        Channel._reset_state()

    def tearDown(self):
        reset_context()

    def test_reserved_channels(self):
        channel = CondaChannelUrl.from_channel_name('free')
        assert channel.channel_name == "free"
        assert channel.channel_location == "repo.continuum.io/pkgs"

        channel = CondaChannelUrl.from_url('https://repo.continuum.io/pkgs/free')
        assert channel.channel_name == "free"
        assert channel.channel_location == "repo.continuum.io/pkgs"

        channel = CondaChannelUrl.from_url('https://repo.continuum.io/pkgs/free/noarch')
        assert channel.channel_name == "free"
        assert channel.channel_location == "repo.continuum.io/pkgs"

        channel = CondaChannelUrl.from_url('https://repo.continuum.io/pkgs/free/label/dev')
        assert channel.channel_name == "free/label/dev"
        assert channel.channel_location == "repo.continuum.io/pkgs"

        channel = CondaChannelUrl.from_url('https://repo.continuum.io/pkgs/free/noarch/flask-1.0.tar.bz2')
        assert channel.channel_name == "free"
        assert channel.channel_location == "repo.continuum.io/pkgs"
        assert channel.platform == "noarch"
        assert channel.package_filename == "flask-1.0.tar.bz2"

    def test_custom_channels(self):
        channel = CondaChannelUrl.from_channel_name('darwin')
        assert channel.channel_name == "darwin"
        assert channel.channel_location == "some.url.somewhere/stuff"

        channel = CondaChannelUrl.from_url('https://some.url.somewhere/stuff/darwin')
        assert channel.channel_name == "darwin"
        assert channel.channel_location == "some.url.somewhere/stuff"

        channel = CondaChannelUrl.from_url('https://some.url.somewhere/stuff/darwin/label/dev/')
        assert channel.channel_name == "darwin/label/dev"
        assert channel.channel_location == "some.url.somewhere/stuff"
        assert channel.platform is None

        channel = CondaChannelUrl.from_url('https://some.url.somewhere/stuff/darwin/label/dev/linux-64')
        assert channel.channel_name == "darwin/label/dev"
        assert channel.channel_location == "some.url.somewhere/stuff"
        assert channel.platform == 'linux-64'
        assert channel.package_filename is None

        channel = CondaChannelUrl.from_url('https://some.url.somewhere/stuff/darwin/label/dev/linux-64/flask-1.0.tar.bz2')
        assert channel.channel_name == "darwin/label/dev"
        assert channel.channel_location == "some.url.somewhere/stuff"
        assert channel.platform == 'linux-64'
        assert channel.package_filename == 'flask-1.0.tar.bz2'
        assert channel.auth is None
        assert channel.token is None
        assert channel.scheme == "https"

        channel = CondaChannelUrl.from_url('https://some.url.somewhere/stuff/darwin/label/dev/linux-64/flask-1.0.tar.bz2')
        assert channel.channel_name == "darwin/label/dev"
        assert channel.channel_location == "some.url.somewhere/stuff"
        assert channel.platform == 'linux-64'
        assert channel.package_filename == 'flask-1.0.tar.bz2'
        assert channel.auth is None
        assert channel.token is None
        assert channel.scheme == "https"

    def test_custom_channels_port_token_auth(self):
        channel = CondaChannelUrl.from_channel_name('chuck')
        assert channel.channel_name == "chuck"
        assert channel.channel_location == "another.url:8080/with/path"
        assert channel.auth == 'user1:pass2'
        assert channel.token == 'tk-1234'
        assert channel.scheme == "http"

        channel = CondaChannelUrl.from_url('https://another.url:8080/with/path/chuck/label/dev/linux-64/flask-1.0.tar.bz2')
        assert channel.channel_name == "chuck/label/dev"
        assert channel.channel_location == "another.url:8080/with/path"
        assert channel.auth == 'user1:pass2'
        assert channel.token == 'tk-1234'
        assert channel.scheme == "http"
        assert channel.platform == 'linux-64'
        assert channel.package_filename == 'flask-1.0.tar.bz2'

    def test_migrated_custom_channels(self):
        channel = CondaChannelUrl.from_url('s3://just/cant/darwin/osx-64')
        assert channel.channel_name == "darwin"
        assert channel.channel_location == "some.url.somewhere/stuff"
        assert channel.platform == 'osx-64'
        assert channel.package_filename is None
        assert channel.auth is None
        assert channel.token is None
        assert channel.scheme == "https"

    def test_local_channel(self):
        channel = CondaChannelUrl.from_channel_name('local')
        assert channel.channel_name == "local"
        assert channel.channel_location == RESERVED_CHANNELS['local']
        assert channel.platform is None
        assert channel.package_filename is None
        assert channel.auth is None
        assert channel.token is None
        assert channel.scheme == "file"





# TODO: test file:// urls REALLY well







    #     # assert Channel('free').urls == [
    #     #     'https://repo.continuum.io/pkgs/free/%s' % platform,
    #     #     'https://repo.continuum.io/pkgs/free/noarch',
    #     # ]

    # def test_migrated_custom_channels(self):
    #     assert Channel('https://some.url.somewhere/stuff/noarch/a-mighty-fine.tar.bz2').canonical_name == 'darwin'
    #     assert Channel('s3://just/cant/noarch/a-mighty-fine.tar.bz2').canonical_name == 'darwin'
    #     assert Channel('s3://just/cant/noarch/a-mighty-fine.tar.bz2').urls == [
    #         'https://some.url.somewhere/stuff/%s/' % platform,
    #         'https://some.url.somewhere/stuff/noarch/']
    #
    # def test_old_channel_alias(self):
    #     cf_urls = ["ftp://new.url:8082/conda-forge/%s/" % platform, "ftp://new.url:8082/conda-forge/noarch/"]
    #     assert Channel('conda-forge').urls == cf_urls
    #
    #     url = "https://conda.anaconda.org/conda-forge/osx-64/some-great-package.tar.bz2"
    #     assert Channel(url).canonical_name == 'conda-forge'
    #     assert Channel(url).base_url == 'ftp://new.url:8082/conda-forge'
    #     assert Channel(url).urls == cf_urls
    #     assert Channel("https://conda.anaconda.org/conda-forge/label/dev/linux-64/"
    #                    "some-great-package.tar.bz2").urls == [
    #         "ftp://new.url:8082/conda-forge/label/dev/%s/" % platform,
    #         "ftp://new.url:8082/conda-forge/label/dev/noarch/"]
    #
    # def test_anaconda_token(self):
    #     try:
    #         assert context.anaconda_token == 'tk-123-456-cba'
    #         os.environ['CONDA_ANACONDA_TOKEN'] = 'tk-123-789-def'
    #         reset_context()
    #         assert context.anaconda_token == 'tk-123-789-def'
    #     finally:
    #         os.environ.pop('CONDA_ANACONDA_TOKEN', None)
