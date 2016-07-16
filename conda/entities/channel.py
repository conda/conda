# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import OrderedDict
from itertools import chain
from logging import getLogger
from os.path import exists, join

from conda.base.constants import PLATFORM_DIRECTORIES, RECOGNIZED_URL_SCHEMES
from ..base.context import subdir, context
from ..compat import urlparse
from ..utils import path_to_url

log = getLogger(__name__)


def get_local_urls():
    # Note, get_*_urls() return unnormalized urls.
    try:
        from conda_build.config import croot
        if exists(croot):
            return [path_to_url(croot)]
    except ImportError:
        pass
    return []


def has_scheme(value):
    return bool(urlparse.urlparse(value).scheme in RECOGNIZED_URL_SCHEMES)


def join_url(*args):
    return '/'.join(args) + '/'


class Channel(object):
    """
    Examples:

    types:
      - url: has_scheme
      - local path
      - just a name

    """

    def __new__(cls, value):
        if isinstance(value, cls):
            return value
        if value is None:
            self = object.__new__(NoneChannel)
        elif value.endswith('.tar.bz2'):
            self = object.__new__(UrlChannel)
        elif value == 'defaults':
            self = object.__new__(DefaultChannel)
        elif value == 'local':
            self = object.__new__(LocalChannel)
        elif has_scheme(value):
            self = object.__new__(UrlChannel)
        else:
            self = object.__new__(NamedChannel)
        return self

    @property
    def base_url(self):
        return urlparse.urlunparse((self._scheme, self._netloc, self._path, None, None, None))

    def __eq__(self, other):
        return self._netloc == other._netloc and self._path == other._path

    @property
    def canonical_name(self):
        if any(self == Channel(c) for c in context.default_channels):
            return 'defaults'
        elif any(self == Channel(c) for c in get_local_urls()):
            return 'local'
        elif self._netloc == Channel(context.channel_alias)._netloc:
            return self._path.lstrip('/')
        else:
            return self.base_url

    @property
    def urls(self):
        if self._platform is None:
            return [join_url(self.base_url, subdir), join_url(self.base_url, 'noarch')]
        else:
            return [join_url(self.base_url, self._platform)]

    @property
    def url_channel_wtf(self):
        # return channel, schannel
        # url_channel in >> https://repo.continuum.io/pkgs/free/osx-64/requests-2.10.0-py27_0.tar.bz2
        # url_channel out >> https://repo.continuum.io/pkgs/free defaults
        return self.base_url, self.canonical_name

    # @staticmethod
    # def url_channel(url):
    #     parts = (url or '').rsplit('/', 2)
    #     if len(parts) == 1:
    #         return '<unknown>', '<unknown>'
    #     if len(parts) == 2:
    #         return parts[0], parts[0]
    #     if url.startswith('file://') and parts[1] not in ('noarch', subdir):
    #         # Explicit file-based URLs are denoted with a '/' in the schannel
    #         channel = parts[0] + '/' + parts[1]
    #         schannel = channel + '/'
    #     else:
    #         channel = parts[0]
    #         schannel = Channel(channel).canonical_name
    #     return channel, schannel
    #
    # @staticmethod
    # def prioritize_channels(channels):
    #     newchans = OrderedDict()
    #     priority = 0
    #     schans = {}
    #     for channel in channels:
    #         channel = channel.rstrip('/') + '/'
    #         if channel not in newchans:
    #             channel_s = canonical_channel_name(channel.rsplit('/', 2)[0])
    #             if channel_s not in schans:
    #                 priority += 1
    #                 schans[channel_s] = priority
    #             newchans[channel] = (channel_s, schans[channel_s])
    #     return newchans
    #
    # @staticmethod
    # def normalize_urls(urls, platform=None):
    #     defaults = tuple(x.rstrip('/') + '/' for x in get_default_urls(False))
    #     newurls = []
    #     while urls:
    #         url = urls[0]
    #         urls = urls[1:]
    #         if url == "system" and rc_path:
    #             urls = get_rc_urls() + urls
    #             continue
    #         elif url in ("defaults", "system"):
    #             t_urls = defaults
    #         elif url == "local":
    #             t_urls = get_local_urls()
    #         else:
    #             t_urls = [url]
    #         for url0 in t_urls:
    #             url0 = url0.rstrip('/')
    #             if not is_url(url0):
    #                 url0 = channel_prefix(True) + url0
    #             else:
    #                 url0 = add_binstar_tokens(url0)
    #             for plat in (platform or subdir, 'noarch'):
    #                 newurls.append('%s/%s/' % (url0, plat))
    #     return newurls


def split_platform(value):
    parts = value.rstrip('/').rsplit('/', 1)
    if len(parts) == 2 and parts[1] in PLATFORM_DIRECTORIES:
        return parts[0], parts[1]
    else:
        return value, None


class UrlChannel(Channel):

    def __init__(self, url):
        if url.endswith('.tar.bz2'):
            url = url.rsplit('/', 1)[0]
        self._raw_value = url
        parsed = urlparse.urlparse(url)
        self._scheme = parsed.scheme
        self._netloc = parsed.netloc
        self._path, self._platform = split_platform(parsed.path)


class NamedChannel(Channel):

    def __init__(self, name):
        self._raw_value = name
        parsed = urlparse.urlparse(context.channel_alias)
        self._scheme = parsed.scheme
        self._netloc = parsed.netloc
        self._path = join(parsed.path, name)
        self._platform = None


class DefaultChannel(NamedChannel):

    @property
    def canonical_name(self):
        return "defaults"

    @property
    def urls(self):
        return list(chain.from_iterable(Channel(c).urls for c in context.default_channels))


class LocalChannel(UrlChannel):

    def __init__(self, _):
        super(LocalChannel, self).__init__(get_local_urls()[0])

    @property
    def canonical_name(self):
        return "local"


class NoneChannel(NamedChannel):

    def __init__(self, value):
        self._raw_value = value
        self._scheme = self._netloc = self._path = self._platform = None

    @property
    def canonical_name(self):
        return "<unknown>"

    @property
    def urls(self):
        return tuple()


def prioritize_channels(channels):
    # ('https://conda.anaconda.org/conda-forge/osx-64/', ('conda-forge', 1))
    result = OrderedDict()
    for q, c in enumerate(channels):
        channel = Channel(c)
        for url in channel.urls:
            result[url] = channel.canonical_name, q
    return result


def offline_keep(url):
    return not context.offline or not is_url(url) or url.startswith('file:/')


def is_url(url):
    if url:
        p = urlparse.urlparse(url)
        return p.netloc != "" or p.scheme == "file"


if __name__ == "__main__":
    print(Channel('kalefranz').base_url)
    print(Channel('kalefranz').canonical_name)
    print(Channel('http://repo.continuum.io/pkgs/pro').base_url)
    print(Channel('http://repo.continuum.io/pkgs/pro').canonical_name)
    print(Channel('https://repo.continuum.io/pkgs/free/osx-64/_license-1.1-py27_1.tar.bz2').canonical_name)
