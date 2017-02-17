# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import OrderedDict
import os
from tempfile import gettempdir

from conda.common.io import env_var

from conda._vendor.auxlib.ish import dals
from conda.base.context import context, reset_context
from conda.common.compat import odict
from conda.common.configuration import YamlRawParameter
from conda.common.url import join_url, join
from conda.common.yaml import yaml_load
from conda.gateways.disk.create import mkdir_p
from conda.gateways.disk.delete import rm_rf
from conda.models.channel import Channel, prioritize_channels
from conda.utils import on_win
from logging import getLogger
from unittest import TestCase
import conda.models.channel

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

log = getLogger(__name__)


class DefaultConfigChannelTests(TestCase):

    @classmethod
    def setUpClass(cls):
        reset_context()
        cls.platform = context.subdir
        cls.DEFAULT_URLS = ['https://repo.continuum.io/pkgs/anaconda/%s' % cls.platform,
                            'https://repo.continuum.io/pkgs/anaconda/noarch',
                            'https://repo.continuum.io/pkgs/r/%s' % cls.platform,
                            'https://repo.continuum.io/pkgs/r/noarch',
                            'https://repo.continuum.io/pkgs/pro/%s' % cls.platform,
                            'https://repo.continuum.io/pkgs/pro/noarch']
        if on_win:
            cls.DEFAULT_URLS.extend(['https://repo.continuum.io/pkgs/msys2/%s' % cls.platform,
                                     'https://repo.continuum.io/pkgs/msys2/noarch'])

    def test_channel_alias_channels(self):
        channel = Channel('binstar/label/dev')
        assert channel.channel_name == "binstar/label/dev"
        assert channel.channel_location == "conda.anaconda.org"
        assert channel.platform is None
        assert channel.package_filename is None
        assert channel.canonical_name == "binstar/label/dev"
        assert channel.urls() == [
            'https://conda.anaconda.org/binstar/label/dev/%s' % context.subdir,
            'https://conda.anaconda.org/binstar/label/dev/noarch',
        ]

    def test_channel_cache(self):
        Channel._reset_state()
        assert len(Channel._cache_) == 0
        dc = Channel('defaults')
        assert len(Channel._cache_) == 1
        dc1 = Channel('defaults')
        assert len(Channel._cache_) == 1
        dc2 = Channel('defaults')
        assert len(Channel._cache_) == 1

        assert dc1 is dc
        assert dc2 is dc

        dc3 = Channel(dc)
        assert len(Channel._cache_) == 1
        assert dc3 is dc

        ccc = Channel('conda-canary')
        assert len(Channel._cache_) == 2

        ccc1 = Channel('conda-canary')
        assert len(Channel._cache_) == 2
        assert ccc1 is ccc

    def test_default_channel(self):
        dc = Channel('defaults')
        assert dc.canonical_name == 'defaults'
        assert dc.urls() == self.DEFAULT_URLS

    def test_url_channel_w_platform(self):
        channel = Channel('https://repo.continuum.io/pkgs/anaconda/osx-64')

        assert channel.scheme == "https"
        assert channel.location == "repo.continuum.io"
        assert channel.platform == 'osx-64'
        assert channel.name == 'pkgs/anaconda'

        assert channel.base_url == 'https://repo.continuum.io/pkgs/anaconda'
        assert channel.canonical_name == 'defaults'
        assert channel.url() == 'https://repo.continuum.io/pkgs/anaconda/osx-64'
        assert channel.urls() == [
            'https://repo.continuum.io/pkgs/anaconda/osx-64',
            'https://repo.continuum.io/pkgs/anaconda/noarch',
        ]

    def test_bare_channel(self):
        url = "http://conda-01"
        channel = Channel(url)
        assert channel.scheme == "http"
        assert channel.location == "conda-01"
        assert channel.platform is None
        assert channel.canonical_name == url
        assert channel.name is None

        assert channel.base_url == url
        assert channel.url() == join_url(url, context.subdir)
        assert channel.urls() == [
            join_url(url, context.subdir),
            join_url(url, 'noarch'),
        ]


class AnacondaServerChannelTests(TestCase):

    @classmethod
    def setUpClass(cls):
        string = dals("""
        channel_alias: https://10.2.3.4:8080/conda/t/tk-123-45
        migrated_channel_aliases:
          - https://conda.anaconda.org
          - http://10.2.3.4:7070/conda
        """)
        reset_context()
        rd = odict(testdata=YamlRawParameter.make_raw_parameters('testdata', yaml_load(string)))
        context._set_raw_data(rd)
        Channel._reset_state()

        cls.platform = context.subdir

    @classmethod
    def tearDownClass(cls):
        reset_context()

    def test_channel_alias_w_conda_path(self):
        channel = Channel('bioconda')
        assert channel.channel_name == "bioconda"
        assert channel.channel_location == "10.2.3.4:8080/conda"
        assert channel.platform is None
        assert channel.package_filename is None
        assert channel.auth is None
        assert channel.scheme == "https"
        assert channel.canonical_name == 'bioconda'
        assert channel.urls() == [
            "https://10.2.3.4:8080/conda/bioconda/%s" % self.platform,
            "https://10.2.3.4:8080/conda/bioconda/noarch",
        ]
        assert channel.token == "tk-123-45"

    def test_channel_alias_w_subhcnnale(self):
        channel = Channel('bioconda/label/dev')
        assert channel.channel_name == "bioconda/label/dev"
        assert channel.channel_location == "10.2.3.4:8080/conda"
        assert channel.platform is None
        assert channel.package_filename is None
        assert channel.auth is None
        assert channel.scheme == "https"
        assert channel.canonical_name == 'bioconda/label/dev'
        assert channel.urls() == [
            "https://10.2.3.4:8080/conda/bioconda/label/dev/%s" % self.platform,
            "https://10.2.3.4:8080/conda/bioconda/label/dev/noarch",
        ]
        assert channel.token == "tk-123-45"

    def test_custom_token_in_channel(self):
        channel = Channel("https://10.2.3.4:8080/conda/t/x1029384756/bioconda")
        assert channel.channel_name == "bioconda"
        assert channel.channel_location == "10.2.3.4:8080/conda"
        assert channel.platform is None
        assert channel.package_filename is None
        assert channel.auth is None
        assert channel.token == "x1029384756"
        assert channel.scheme == "https"
        assert channel.canonical_name == 'bioconda'
        assert channel.urls() == [
            "https://10.2.3.4:8080/conda/bioconda/%s" % self.platform,
            "https://10.2.3.4:8080/conda/bioconda/noarch",
        ]

    def test_canonicalized_url_gets_correct_token(self):
        channel = Channel("bioconda")
        assert channel.urls() == [
            "https://10.2.3.4:8080/conda/bioconda/%s" % self.platform,
            "https://10.2.3.4:8080/conda/bioconda/noarch",
        ]
        assert channel.urls(with_credentials=True) == [
            "https://10.2.3.4:8080/conda/t/tk-123-45/bioconda/%s" % self.platform,
            "https://10.2.3.4:8080/conda/t/tk-123-45/bioconda/noarch",
        ]

        channel = Channel("https://10.2.3.4:8080/conda/bioconda")
        assert channel.urls() == [
            "https://10.2.3.4:8080/conda/bioconda/%s" % self.platform,
            "https://10.2.3.4:8080/conda/bioconda/noarch",
        ]
        assert channel.urls(with_credentials=True) == [
            "https://10.2.3.4:8080/conda/t/tk-123-45/bioconda/%s" % self.platform,
            "https://10.2.3.4:8080/conda/t/tk-123-45/bioconda/noarch",
        ]

        channel = Channel("https://10.2.3.4:8080/conda/t/x1029384756/bioconda")
        assert channel.urls() == [
            "https://10.2.3.4:8080/conda/bioconda/%s" % self.platform,
            "https://10.2.3.4:8080/conda/bioconda/noarch",
        ]
        assert channel.urls(with_credentials=True) == [
            "https://10.2.3.4:8080/conda/t/x1029384756/bioconda/%s" % self.platform,
            "https://10.2.3.4:8080/conda/t/x1029384756/bioconda/noarch",
        ]

        # what happens with the token if it's in the wrong places?
        channel = Channel("https://10.2.3.4:8080/t/x1029384756/conda/bioconda")
        assert channel.urls() == [
            "https://10.2.3.4:8080/conda/bioconda/%s" % self.platform,
            "https://10.2.3.4:8080/conda/bioconda/noarch",
        ]
        assert channel.urls(with_credentials=True) == [
            "https://10.2.3.4:8080/conda/t/x1029384756/bioconda/%s" % self.platform,
            "https://10.2.3.4:8080/conda/t/x1029384756/bioconda/noarch",
        ]


class CustomConfigChannelTests(TestCase):
    """
    Some notes about the tests in this class:
      * The 'pkgs/anaconda' channel is 'migrated' while the 'pkgs/pro' channel is not.
        Thus test_pkgs_free and test_pkgs_pro have substantially different behavior.
    """

    @classmethod
    def setUp(cls):
        string = dals("""
        custom_channels:
          darwin: https://some.url.somewhere/stuff
          chuck: http://user1:pass2@another.url:8080/t/tk-1234/with/path
          pkgs/anaconda: http://192.168.0.15:8080
        migrated_custom_channels:
          darwin: s3://just/cant
          chuck: file:///var/lib/repo/
          pkgs/anaconda: https://repo.continuum.io
        migrated_channel_aliases:
          - https://conda.anaconda.org
        channel_alias: ftp://new.url:8082
        default_channels:
          - http://192.168.0.15:8080/pkgs/anaconda
          - http://192.168.0.15:8080/pkgs/pro
          - http://192.168.0.15:8080/pkgs/msys2
        """)
        reset_context()
        rd = odict(testdata=YamlRawParameter.make_raw_parameters('testdata', yaml_load(string)))
        context._set_raw_data(rd)
        Channel._reset_state()

        cls.platform = context.subdir

        cls.DEFAULT_URLS = ['http://192.168.0.15:8080/pkgs/anaconda/%s' % cls.platform,
                            'http://192.168.0.15:8080/pkgs/anaconda/noarch',
                            'http://192.168.0.15:8080/pkgs/pro/%s' % cls.platform,
                            'http://192.168.0.15:8080/pkgs/pro/noarch',
                            'http://192.168.0.15:8080/pkgs/msys2/%s' % cls.platform,
                            'http://192.168.0.15:8080/pkgs/msys2/noarch',
                            ]

    @classmethod
    def tearDown(cls):
        reset_context()

    def test_pkgs_free(self):
        channel = Channel('pkgs/anaconda')
        assert channel.channel_name == "pkgs/anaconda"
        assert channel.channel_location == "192.168.0.15:8080"
        assert channel.canonical_name == "defaults"
        assert channel.urls() == [
            'http://192.168.0.15:8080/pkgs/anaconda/%s' % self.platform,
            'http://192.168.0.15:8080/pkgs/anaconda/noarch',
        ]

        channel = Channel('https://repo.continuum.io/pkgs/anaconda')
        assert channel.channel_name == "pkgs/anaconda"
        assert channel.channel_location == "192.168.0.15:8080"
        assert channel.canonical_name == "defaults"
        assert channel.urls() == [
            'http://192.168.0.15:8080/pkgs/anaconda/%s' % self.platform,
            'http://192.168.0.15:8080/pkgs/anaconda/noarch',
        ]

        channel = Channel('https://repo.continuum.io/pkgs/anaconda/noarch')
        assert channel.channel_name == "pkgs/anaconda"
        assert channel.channel_location == "192.168.0.15:8080"
        assert channel.canonical_name == "defaults"
        assert channel.urls() == [
            'http://192.168.0.15:8080/pkgs/anaconda/noarch',
        ]

        channel = Channel('https://repo.continuum.io/pkgs/anaconda/label/dev')
        assert channel.channel_name == "pkgs/anaconda/label/dev"
        assert channel.channel_location == "192.168.0.15:8080"
        assert channel.canonical_name == "pkgs/anaconda/label/dev"
        assert channel.urls() == [
            'http://192.168.0.15:8080/pkgs/anaconda/label/dev/%s' % self.platform,
            'http://192.168.0.15:8080/pkgs/anaconda/label/dev/noarch',
        ]

        channel = Channel('https://repo.continuum.io/pkgs/anaconda/noarch/flask-1.0.tar.bz2')
        assert channel.channel_name == "pkgs/anaconda"
        assert channel.channel_location == "192.168.0.15:8080"
        assert channel.platform == "noarch"
        assert channel.package_filename == "flask-1.0.tar.bz2"
        assert channel.canonical_name == "defaults"
        assert channel.urls() == [
            'http://192.168.0.15:8080/pkgs/anaconda/noarch',
        ]

    def test_pkgs_pro(self):
        channel = Channel('pkgs/pro')
        assert channel.channel_name == "pkgs/pro"
        assert channel.channel_location == "192.168.0.15:8080"
        assert channel.canonical_name == "defaults"
        assert channel.urls() == [
            'http://192.168.0.15:8080/pkgs/pro/%s' % self.platform,
            'http://192.168.0.15:8080/pkgs/pro/noarch',
        ]

        channel = Channel('https://repo.continuum.io/pkgs/pro')
        assert channel.channel_name == "pkgs/pro"
        assert channel.channel_location == "repo.continuum.io"
        assert channel.canonical_name == "defaults"
        assert channel.urls() == [
            'https://repo.continuum.io/pkgs/pro/%s' % self.platform,
            'https://repo.continuum.io/pkgs/pro/noarch',
        ]

        channel = Channel('https://repo.continuum.io/pkgs/pro/noarch')
        assert channel.channel_name == "pkgs/pro"
        assert channel.channel_location == "repo.continuum.io"
        assert channel.canonical_name == "defaults"
        assert channel.urls() == [
            'https://repo.continuum.io/pkgs/pro/noarch',
        ]

        channel = Channel('https://repo.continuum.io/pkgs/pro/label/dev')
        assert channel.channel_name == "pkgs/pro/label/dev"
        assert channel.channel_location == "repo.continuum.io"
        assert channel.canonical_name == "pkgs/pro/label/dev"
        assert channel.urls() == [
            'https://repo.continuum.io/pkgs/pro/label/dev/%s' % self.platform,
            'https://repo.continuum.io/pkgs/pro/label/dev/noarch',
        ]

        channel = Channel('https://repo.continuum.io/pkgs/pro/noarch/flask-1.0.tar.bz2')
        assert channel.channel_name == "pkgs/pro"
        assert channel.channel_location == "repo.continuum.io"
        assert channel.platform == "noarch"
        assert channel.package_filename == "flask-1.0.tar.bz2"
        assert channel.canonical_name == "defaults"
        assert channel.urls() == [
            'https://repo.continuum.io/pkgs/pro/noarch',
        ]

    def test_custom_channels(self):
        channel = Channel('darwin')
        assert channel.channel_name == "darwin"
        assert channel.channel_location == "some.url.somewhere/stuff"

        channel = Channel('https://some.url.somewhere/stuff/darwin')
        assert channel.channel_name == "darwin"
        assert channel.channel_location == "some.url.somewhere/stuff"

        channel = Channel('https://some.url.somewhere/stuff/darwin/label/dev')
        assert channel.channel_name == "darwin/label/dev"
        assert channel.channel_location == "some.url.somewhere/stuff"
        assert channel.platform is None

        channel = Channel('https://some.url.somewhere/stuff/darwin/label/dev/linux-64')
        assert channel.channel_name == "darwin/label/dev"
        assert channel.channel_location == "some.url.somewhere/stuff"
        assert channel.platform == 'linux-64'
        assert channel.package_filename is None

        channel = Channel('https://some.url.somewhere/stuff/darwin/label/dev/linux-64/flask-1.0.tar.bz2')
        assert channel.channel_name == "darwin/label/dev"
        assert channel.channel_location == "some.url.somewhere/stuff"
        assert channel.platform == 'linux-64'
        assert channel.package_filename == 'flask-1.0.tar.bz2'
        assert channel.auth is None
        assert channel.token is None
        assert channel.scheme == "https"

        channel = Channel('https://some.url.somewhere/stuff/darwin/label/dev/linux-64/flask-1.0.tar.bz2')
        assert channel.channel_name == "darwin/label/dev"
        assert channel.channel_location == "some.url.somewhere/stuff"
        assert channel.platform == 'linux-64'
        assert channel.package_filename == 'flask-1.0.tar.bz2'
        assert channel.auth is None
        assert channel.token is None
        assert channel.scheme == "https"

    def test_custom_channels_port_token_auth(self):
        channel = Channel('chuck')
        assert channel.channel_name == "chuck"
        assert channel.channel_location == "another.url:8080/with/path"
        assert channel.auth == 'user1:pass2'
        assert channel.token == 'tk-1234'
        assert channel.scheme == "http"

        channel = Channel('https://another.url:8080/with/path/chuck/label/dev/linux-64/flask-1.0.tar.bz2')
        assert channel.channel_name == "chuck/label/dev"
        assert channel.channel_location == "another.url:8080/with/path"
        assert channel.auth == 'user1:pass2'
        assert channel.token == 'tk-1234'
        assert channel.scheme == "https"
        assert channel.platform == 'linux-64'
        assert channel.package_filename == 'flask-1.0.tar.bz2'

    def test_migrated_custom_channels(self):
        channel = Channel('s3://just/cant/darwin/osx-64')
        assert channel.channel_name == "darwin"
        assert channel.channel_location == "some.url.somewhere/stuff"
        assert channel.platform == 'osx-64'
        assert channel.package_filename is None
        assert channel.auth is None
        assert channel.token is None
        assert channel.scheme == "https"
        assert channel.canonical_name == "darwin"
        assert channel.url() == "https://some.url.somewhere/stuff/darwin/osx-64"
        assert channel.urls() == [
            "https://some.url.somewhere/stuff/darwin/osx-64",
            "https://some.url.somewhere/stuff/darwin/noarch",
        ]
        assert Channel(channel.canonical_name).urls() == [
            "https://some.url.somewhere/stuff/darwin/%s" % self.platform,
            "https://some.url.somewhere/stuff/darwin/noarch",
        ]

        channel = Channel('https://some.url.somewhere/stuff/darwin/noarch/a-mighty-fine.tar.bz2')
        assert channel.channel_name == "darwin"
        assert channel.channel_location == "some.url.somewhere/stuff"
        assert channel.platform == 'noarch'
        assert channel.package_filename == 'a-mighty-fine.tar.bz2'
        assert channel.auth is None
        assert channel.token is None
        assert channel.scheme == "https"
        assert channel.canonical_name == "darwin"
        assert channel.url() == "https://some.url.somewhere/stuff/darwin/noarch/a-mighty-fine.tar.bz2"
        assert channel.urls() == [
            "https://some.url.somewhere/stuff/darwin/noarch",
        ]
        assert Channel(channel.canonical_name).urls() == [
            "https://some.url.somewhere/stuff/darwin/%s" % self.platform,
            "https://some.url.somewhere/stuff/darwin/noarch",
        ]

    def test_local_channel(self):
        conda_bld_path = join(gettempdir(), 'conda-bld')
        mkdir_p(conda_bld_path)
        try:
            with env_var('CONDA_CROOT', conda_bld_path, reset_context):
                Channel._reset_state()
                channel = Channel('local')
                assert channel._channels[0].name.rsplit('/', 1)[-1] == 'conda-bld'
                assert channel.channel_name == "local"
                assert channel.platform is None
                assert channel.package_filename is None
                assert channel.auth is None
                assert channel.token is None
                assert channel.scheme is None
                assert channel.canonical_name == "local"
                local_channel_first_subchannel = channel._channels[0].name

                channel = Channel(local_channel_first_subchannel)
                assert channel.channel_name == local_channel_first_subchannel
                assert channel.platform is None
                assert channel.package_filename is None
                assert channel.auth is None
                assert channel.token is None
                assert channel.scheme == "file"
                assert channel.canonical_name == "local"

                assert channel.urls() == Channel(local_channel_first_subchannel).urls()
                assert channel.urls()[0].startswith('file:///')
        finally:
            rm_rf(conda_bld_path)

    def test_defaults_channel(self):
        channel = Channel('defaults')
        assert channel.name == 'defaults'
        assert channel.platform is None
        assert channel.package_filename is None
        assert channel.auth is None
        assert channel.token is None
        assert channel.scheme is None
        assert channel.canonical_name == 'defaults'
        assert channel.urls() == self.DEFAULT_URLS

    def test_file_channel(self):
        channel = Channel("file:///var/folders/cp/7r2s_s593j7_cpdtp/T/5d9f5e45/osx-64/flask-0.10.1-py35_2.tar.bz2")
        assert channel.name == '5d9f5e45'
        assert channel.location == '/var/folders/cp/7r2s_s593j7_cpdtp/T'
        assert channel.platform == 'osx-64'
        assert channel.package_filename == "flask-0.10.1-py35_2.tar.bz2"
        assert channel.auth is None
        assert channel.token is None
        assert channel.scheme == "file"
        assert channel.url() == "file:///var/folders/cp/7r2s_s593j7_cpdtp/T/5d9f5e45/osx-64/flask-0.10.1-py35_2.tar.bz2"
        assert channel.urls() == [
            "file:///var/folders/cp/7r2s_s593j7_cpdtp/T/5d9f5e45/osx-64",
            "file:///var/folders/cp/7r2s_s593j7_cpdtp/T/5d9f5e45/noarch"
        ]
        assert channel.canonical_name == 'file:///var/folders/cp/7r2s_s593j7_cpdtp/T/5d9f5e45'

    def test_old_channel_alias(self):
        cf_urls = ["ftp://new.url:8082/conda-forge/%s" % self.platform,
                   "ftp://new.url:8082/conda-forge/noarch"]
        assert Channel('conda-forge').urls() == cf_urls

        url = "https://conda.anaconda.org/conda-forge/osx-64/some-great-package.tar.bz2"
        assert Channel(url).canonical_name == 'conda-forge'
        assert Channel(url).base_url == 'ftp://new.url:8082/conda-forge'
        assert Channel(url).url() == "ftp://new.url:8082/conda-forge/osx-64/some-great-package.tar.bz2"
        assert Channel(url).urls() == [
            "ftp://new.url:8082/conda-forge/osx-64",
            "ftp://new.url:8082/conda-forge/noarch",
        ]

        channel = Channel("https://conda.anaconda.org/conda-forge/label/dev/linux-64/some-great-package.tar.bz2")
        assert channel.url() == "ftp://new.url:8082/conda-forge/label/dev/linux-64/some-great-package.tar.bz2"
        assert channel.urls() == [
            "ftp://new.url:8082/conda-forge/label/dev/linux-64",
            "ftp://new.url:8082/conda-forge/label/dev/noarch",
        ]


class ChannelAuthTokenPriorityTests(TestCase):

    @classmethod
    def setUpClass(cls):
        string = dals("""
        custom_channels:
          chuck: http://user1:pass2@another.url:8080/with/path/t/tk-1234
          chuck/subchan: http://user33:pass44@another.url:8080/with/path/t/tk-1234
        channel_alias: ftp://nm:ps@new.url:8082/t/zyx-wvut/
        channels:
          - mickey
          - https://conda.anaconda.cloud/t/tk-12-token/minnie
          - http://dont-do:this@4.3.2.1/daffy/label/main
        default_channels:
          - http://192.168.0.15:8080/pkgs/anaconda
          - donald/label/main
          - http://us:pw@192.168.0.15:8080/t/tkn-123/pkgs/r
        """)
        reset_context()
        rd = odict(testdata=YamlRawParameter.make_raw_parameters('testdata', yaml_load(string)))
        context._set_raw_data(rd)
        Channel._reset_state()

        cls.platform = context.subdir

    @classmethod
    def tearDownClass(cls):
        reset_context()

    def test_named_custom_channel(self):
        channel = Channel("chuck")
        assert channel.canonical_name == "chuck"
        assert channel.location == "another.url:8080/with/path"
        assert channel.url() == "http://another.url:8080/with/path/chuck/%s" % self.platform
        assert channel.url(True) == "http://user1:pass2@another.url:8080/with/path/t/tk-1234/chuck/%s" % self.platform
        assert channel.urls() == [
            "http://another.url:8080/with/path/chuck/%s" % self.platform,
            "http://another.url:8080/with/path/chuck/noarch",
        ]
        assert channel.urls(True) == [
            "http://user1:pass2@another.url:8080/with/path/t/tk-1234/chuck/%s" % self.platform,
            "http://user1:pass2@another.url:8080/with/path/t/tk-1234/chuck/noarch",
        ]

        channel = Channel("chuck/label/dev")
        assert channel.canonical_name == "chuck/label/dev"
        assert channel.location == "another.url:8080/with/path"
        assert channel.url() == "http://another.url:8080/with/path/chuck/label/dev/%s" % self.platform
        assert channel.url(True) == "http://user1:pass2@another.url:8080/with/path/t/tk-1234/chuck/label/dev/%s" % self.platform
        assert channel.urls() == [
            "http://another.url:8080/with/path/chuck/label/dev/%s" % self.platform,
            "http://another.url:8080/with/path/chuck/label/dev/noarch",
        ]
        assert channel.urls(True) == [
            "http://user1:pass2@another.url:8080/with/path/t/tk-1234/chuck/label/dev/%s" % self.platform,
            "http://user1:pass2@another.url:8080/with/path/t/tk-1234/chuck/label/dev/noarch",
        ]

    def test_url_custom_channel(self):
        # scheme and credentials within url should override what's registered in config
        channel = Channel("https://newuser:newpass@another.url:8080/with/path/t/new-token/chuck/label/dev")
        assert channel.canonical_name == "chuck/label/dev"
        assert channel.location == "another.url:8080/with/path"
        assert channel.url() == "https://another.url:8080/with/path/chuck/label/dev/%s" % self.platform
        assert channel.url(True) == "https://newuser:newpass@another.url:8080/with/path/t/new-token/chuck/label/dev/%s" % self.platform
        assert channel.urls() == [
            "https://another.url:8080/with/path/chuck/label/dev/%s" % self.platform,
            "https://another.url:8080/with/path/chuck/label/dev/noarch",
        ]
        assert channel.urls(True) == [
            "https://newuser:newpass@another.url:8080/with/path/t/new-token/chuck/label/dev/%s" % self.platform,
            "https://newuser:newpass@another.url:8080/with/path/t/new-token/chuck/label/dev/noarch",
        ]

    def test_named_custom_channel_w_subchan(self):
        channel = Channel("chuck/subchan")
        assert channel.canonical_name == "chuck/subchan"
        assert channel.location == "another.url:8080/with/path"
        assert channel.url() == "http://another.url:8080/with/path/chuck/subchan/%s" % self.platform
        assert channel.url(
            True) == "http://user33:pass44@another.url:8080/with/path/t/tk-1234/chuck/subchan/%s" % self.platform
        assert channel.urls() == [
            "http://another.url:8080/with/path/chuck/subchan/%s" % self.platform,
            "http://another.url:8080/with/path/chuck/subchan/noarch",
        ]
        assert channel.urls(True) == [
            "http://user33:pass44@another.url:8080/with/path/t/tk-1234/chuck/subchan/%s" % self.platform,
            "http://user33:pass44@another.url:8080/with/path/t/tk-1234/chuck/subchan/noarch",
        ]

        channel = Channel("chuck/subchan/label/main")
        assert channel.canonical_name == "chuck/subchan/label/main"
        assert channel.location == "another.url:8080/with/path"
        assert channel.url() == "http://another.url:8080/with/path/chuck/subchan/label/main/%s" % self.platform
        assert channel.url(
            True) == "http://user33:pass44@another.url:8080/with/path/t/tk-1234/chuck/subchan/label/main/%s" % self.platform
        assert channel.urls() == [
            "http://another.url:8080/with/path/chuck/subchan/label/main/%s" % self.platform,
            "http://another.url:8080/with/path/chuck/subchan/label/main/noarch",
        ]
        assert channel.urls(True) == [
            "http://user33:pass44@another.url:8080/with/path/t/tk-1234/chuck/subchan/label/main/%s" % self.platform,
            "http://user33:pass44@another.url:8080/with/path/t/tk-1234/chuck/subchan/label/main/noarch",
        ]

    def test_url_custom_channel_w_subchan(self):
        channel = Channel("http://another.url:8080/with/path/chuck/subchan/label/main")
        assert channel.canonical_name == "chuck/subchan/label/main"
        assert channel.location == "another.url:8080/with/path"
        assert channel.url() == "http://another.url:8080/with/path/chuck/subchan/label/main/%s" % self.platform
        assert channel.url(True) == "http://user33:pass44@another.url:8080/with/path/t/tk-1234/chuck/subchan/label/main/%s" % self.platform
        assert channel.urls() == [
            "http://another.url:8080/with/path/chuck/subchan/label/main/%s" % self.platform,
            "http://another.url:8080/with/path/chuck/subchan/label/main/noarch",
        ]
        assert channel.urls(True) == [
            "http://user33:pass44@another.url:8080/with/path/t/tk-1234/chuck/subchan/label/main/%s" % self.platform,
            "http://user33:pass44@another.url:8080/with/path/t/tk-1234/chuck/subchan/label/main/noarch",
        ]

    def test_channel_alias(self):
        channel = Channel("charlie")
        assert channel.canonical_name == "charlie"
        assert channel.location == "new.url:8082"
        assert channel.url() == "ftp://new.url:8082/charlie/%s" % self.platform
        assert channel.url(True) == "ftp://nm:ps@new.url:8082/t/zyx-wvut/charlie/%s" % self.platform
        assert channel.urls() == [
            "ftp://new.url:8082/charlie/%s" % self.platform,
            "ftp://new.url:8082/charlie/noarch",
        ]
        assert channel.urls(True) == [
            "ftp://nm:ps@new.url:8082/t/zyx-wvut/charlie/%s" % self.platform,
            "ftp://nm:ps@new.url:8082/t/zyx-wvut/charlie/noarch",
        ]

        channel = Channel("charlie/label/dev")
        assert channel.canonical_name == "charlie/label/dev"
        assert channel.location == "new.url:8082"
        assert channel.url() == "ftp://new.url:8082/charlie/label/dev/%s" % self.platform
        assert channel.url(True) == "ftp://nm:ps@new.url:8082/t/zyx-wvut/charlie/label/dev/%s" % self.platform
        assert channel.urls() == [
            "ftp://new.url:8082/charlie/label/dev/%s" % self.platform,
            "ftp://new.url:8082/charlie/label/dev/noarch",
        ]
        assert channel.urls(True) == [
            "ftp://nm:ps@new.url:8082/t/zyx-wvut/charlie/label/dev/%s" % self.platform,
            "ftp://nm:ps@new.url:8082/t/zyx-wvut/charlie/label/dev/noarch",
        ]

        channel = Channel("ftp://nm:ps@new.url:8082/t/new-token/charlie/label/dev")
        assert channel.canonical_name == "charlie/label/dev"
        assert channel.location == "new.url:8082"
        assert channel.url() == "ftp://new.url:8082/charlie/label/dev/%s" % self.platform
        assert channel.url(
            True) == "ftp://nm:ps@new.url:8082/t/new-token/charlie/label/dev/%s" % self.platform
        assert channel.urls() == [
            "ftp://new.url:8082/charlie/label/dev/%s" % self.platform,
            "ftp://new.url:8082/charlie/label/dev/noarch",
        ]
        assert channel.urls(True) == [
            "ftp://nm:ps@new.url:8082/t/new-token/charlie/label/dev/%s" % self.platform,
            "ftp://nm:ps@new.url:8082/t/new-token/charlie/label/dev/noarch",
        ]

    def test_default_channels(self):
        channel = Channel('defaults')
        assert channel.canonical_name == "defaults"
        assert channel.location is None
        assert channel.url() is None
        assert channel.url(True) is None
        assert channel.urls() == [
            "http://192.168.0.15:8080/pkgs/anaconda/%s" % self.platform,
            "http://192.168.0.15:8080/pkgs/anaconda/noarch",
            "ftp://new.url:8082/donald/label/main/%s" % self.platform,
            "ftp://new.url:8082/donald/label/main/noarch",
            "http://192.168.0.15:8080/pkgs/r/%s" % self.platform,
            "http://192.168.0.15:8080/pkgs/r/noarch",
        ]
        assert channel.urls(True) == [
            "http://192.168.0.15:8080/pkgs/anaconda/%s" % self.platform,
            "http://192.168.0.15:8080/pkgs/anaconda/noarch",
            "ftp://nm:ps@new.url:8082/t/zyx-wvut/donald/label/main/%s" % self.platform,
            "ftp://nm:ps@new.url:8082/t/zyx-wvut/donald/label/main/noarch",
            "http://us:pw@192.168.0.15:8080/t/tkn-123/pkgs/r/%s" % self.platform,
            "http://us:pw@192.168.0.15:8080/t/tkn-123/pkgs/r/noarch",
        ]

        channel = Channel("ftp://new.url:8082/donald/label/main")
        assert channel.canonical_name == "defaults"

        channel = Channel("donald/label/main")
        assert channel.canonical_name == "defaults"

        channel = Channel("ftp://new.url:8081/donald")
        assert channel.location == "new.url:8081"
        assert channel.canonical_name == "donald"


class UrlChannelTests(TestCase):

    def test_file_urls(self):
        url = "file:///machine/shared_folder"
        c = Channel(url)
        assert c.scheme == "file"
        assert c.auth is None
        assert c.location == "/machine"
        assert c.token is None
        assert c.name == "shared_folder"
        assert c.platform is None
        assert c.package_filename is None

        assert c.canonical_name == "file:///machine/shared_folder"
        assert c.url() == "file:///machine/shared_folder/%s" % context.subdir
        assert c.urls() == [
            "file:///machine/shared_folder/%s" % context.subdir,
            "file:///machine/shared_folder/noarch",
        ]

    def test_file_url_with_backslashes(self):
        url = "file://\\machine\\shared_folder\\path\\conda"
        c = Channel(url)
        assert c.scheme == "file"
        assert c.auth is None
        assert c.location == "/machine/shared_folder/path"
        assert c.token is None
        assert c.name == "conda"
        assert c.platform is None
        assert c.package_filename is None

        assert c.canonical_name == "file:///machine/shared_folder/path/conda"
        assert c.url() == "file:///machine/shared_folder/path/conda/%s" % context.subdir
        assert c.urls() == [
            "file:///machine/shared_folder/path/conda/%s" % context.subdir,
            "file:///machine/shared_folder/path/conda/noarch",
        ]

    def test_env_var_file_urls(self):
        channels = ("file://\\\\network_share\\shared_folder\\path\\conda,"
                    "https://some.url/ch_name,"
                    "file:///some/place/on/my/machine")
        with env_var("CONDA_CHANNELS", channels, reset_context):
            assert context.channels == (
                "file://\\\\network_share\\shared_folder\\path\\conda",
                "https://some.url/ch_name",
                "file:///some/place/on/my/machine",
            )
            prioritized = prioritize_channels(context.channels)
            assert prioritized == OrderedDict((
                ("file://network_share/shared_folder/path/conda/%s" % context.subdir, ("file://network_share/shared_folder/path/conda", 0)),
                ("file://network_share/shared_folder/path/conda/noarch", ("file://network_share/shared_folder/path/conda", 0)),
                ("https://some.url/ch_name/%s" % context.subdir, ("https://some.url/ch_name", 1)),
                ("https://some.url/ch_name/noarch", ("https://some.url/ch_name", 1)),
                ("file:///some/place/on/my/machine/%s" % context.subdir, ("file:///some/place/on/my/machine", 2)),
                ("file:///some/place/on/my/machine/noarch", ("file:///some/place/on/my/machine", 2)),
            ))


class UnknownChannelTests(TestCase):

    def test_regression_against_unknown_none(self):
        defaults = Channel('defaults')

        channel = Channel(None)
        assert channel.scheme is None
        assert channel.location is None
        assert channel.platform is None
        assert channel.name == "<unknown>"
        assert channel.canonical_name == "<unknown>"

        assert channel.base_url is None
        assert channel.url() == defaults.url()
        assert channel.urls() == defaults.urls()

        channel = Channel('<unknown>')
        assert channel.scheme is None
        assert channel.location is None
        assert channel.platform is None
        assert channel.name == "<unknown>"
        assert channel.canonical_name == "<unknown>"

        assert channel.base_url is None
        assert channel.url() == defaults.url()
        assert channel.urls() == defaults.urls()

        channel = Channel('None:///<unknown>')
        assert channel.scheme is None
        assert channel.location is None
        assert channel.platform is None
        assert channel.name == "<unknown>"
        assert channel.canonical_name == "<unknown>"

        assert channel.base_url is None
        assert channel.url() == defaults.url()
        assert channel.urls() == defaults.urls()

        channel = Channel('None')
        assert channel.scheme is None
        assert channel.location is None
        assert channel.platform is None
        assert channel.name == "<unknown>"
        assert channel.canonical_name == "<unknown>"

        assert channel.base_url is None
        assert channel.url() == defaults.url()
        assert channel.urls() == defaults.urls()
