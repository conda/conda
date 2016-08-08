# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from conda.models.channel import Channel, DefaultChannel, UrlChannel, split_platform
from logging import getLogger
from unittest import TestCase

try:
    from unittest import mock
except ImportError:
    import mock
patch = mock.patch

log = getLogger(__name__)


class ChannelTests(TestCase):

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
        assert isinstance(dc, DefaultChannel)

        assert dc.base_url == 'https://conda.anaconda.org/defaults'
        assert dc.canonical_name == 'defaults'
        assert dc.urls == ['https://repo.continuum.io/pkgs/free/osx-64/',
                           'https://repo.continuum.io/pkgs/free/noarch/',
                           'https://repo.continuum.io/pkgs/pro/osx-64/',
                           'https://repo.continuum.io/pkgs/pro/noarch/']

        assert dc._scheme == "https"
        assert dc._netloc == "conda.anaconda.org"
        assert dc._path == "/defaults"
        assert dc._platform is None

    def test_url_channel_w_platform(self):
        channel = Channel('https://repo.continuum.io/pkgs/free/osx-64/')
        assert isinstance(channel, UrlChannel)

        assert channel._scheme == "https"
        assert channel._netloc == "repo.continuum.io"
        assert channel._path == "/pkgs/free"
        assert channel._platform == 'osx-64'

        assert channel.base_url == 'https://repo.continuum.io/pkgs/free'
        assert channel.canonical_name == 'defaults'
        assert channel.urls == ['https://repo.continuum.io/pkgs/free/osx-64/']

    def test_url_channel_wo_platform(self):
        channel = Channel('https://repo.continuum.io/pkgs/free/')
        assert isinstance(channel, UrlChannel)

        assert channel._scheme == "https"
        assert channel._netloc == "repo.continuum.io"
        assert channel._path == "/pkgs/free"
        assert channel._platform is None

        assert channel.base_url == 'https://repo.continuum.io/pkgs/free'
        assert channel.canonical_name == 'defaults'
        assert channel.urls == ['https://repo.continuum.io/pkgs/free/osx-64/',
                                'https://repo.continuum.io/pkgs/free/noarch/']

    def test_split_platform(self):
        assert split_platform('/pkgs/free/') == ('/pkgs/free', None)
        assert split_platform('/pkgs/free') == ('/pkgs/free', None)
        assert split_platform('/pkgs/free/osx-64/') == ('/pkgs/free', 'osx-64')
        assert split_platform('/pkgs/free/osx-64') == ('/pkgs/free', 'osx-64')

        assert split_platform('/') == ('/', None)
        assert split_platform('') == ('/', None)
        assert split_platform(None) == ('/', None)
