# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import re
from conda.compat import text_type
from itertools import chain
from logging import getLogger
from os.path import join

from ..base.constants import PLATFORM_DIRECTORIES, RECOGNIZED_URL_SCHEMES
from ..base.context import context
from ..common.compat import odict, with_metaclass
from ..common.url import is_url, path_to_url, urlparse, urlunparse

log = getLogger(__name__)


# backward compatibility for conda-build
def get_conda_build_local_url():
    return context.local_build_root,


def has_scheme(value):
    return bool(urlparse(value).scheme in RECOGNIZED_URL_SCHEMES)


def join_url(*args):
    return '/'.join(args) + '/'


class ChannelType(type):

    def __call__(cls, value):
        if isinstance(value, Channel):
            return value
        elif value in Channel._cache_:
            return Channel._cache_[value]
        elif value in _SPECIAL_CHANNELS:
            self = object.__new__(_SPECIAL_CHANNELS[value])
        elif value.endswith('.tar.bz2'):
            self = object.__new__(UrlChannel)
        elif has_scheme(value):
            self = object.__new__(UrlChannel)
        else:
            self = object.__new__(NamedChannel)
        self.__init__(value)
        Channel._cache_[value] = self
        return self


@with_metaclass(ChannelType)
class Channel(object):
    _cache_ = dict()
    _channel_alias_netloc = (urlparse(context.channel_alias).netloc,
                             urlparse(context.old_channel_alias).netloc)

    @staticmethod
    def _reset_state():
        Channel._cache_ = dict()
        Channel._channel_alias_netloc = (urlparse(context.channel_alias).netloc,
                                         urlparse(context.old_channel_alias).netloc)

    @property
    def base_url(self):
        # TODO: account for context.old_channel_alias
        return urlunparse((self._scheme, self._netloc, self._path.lstrip('/'), None, None, None))

    def __eq__(self, other):
        return self._netloc == other._netloc and self._path == other._path

    def __hash__(self):
        return hash((self._netloc, self._path))

    @property
    def canonical_name(self):
        if self in context.inverted_channel_map:
            return context.inverted_channel_map[self]
        elif self._netloc in Channel._channel_alias_netloc:
            return self._path.strip('/')
        else:
            return self.base_url

    def _urls_helper(self):
        return [join_url(self.base_url, context.subdir), join_url(self.base_url, 'noarch')]
        # if self._platform is None:
        #     return [join_url(self.base_url, context.subdir), join_url(self.base_url, 'noarch')]
        # else:
        #     return [join_url(self.base_url, self._platform)]

    @property
    def urls(self):
        if self.canonical_name in context.channel_map:
            url_channels = context.channel_map[self.canonical_name]
            return list(chain.from_iterable(c._urls_helper() for c in url_channels))
        else:
            return self._urls_helper()

    @property
    def url_channel_wtf(self):
        # return channel, schannel
        # url_channel in >> https://repo.continuum.io/pkgs/free/osx-64/requests-2.0-py27_0.tar.bz2
        # url_channel out >> https://repo.continuum.io/pkgs/free defaults
        return self.base_url, self.canonical_name


def split_platform(value):
    if value is None:
        return '/', None
    value = value.rstrip('/')
    parts = value.rsplit('/', 1)
    if len(parts) == 2 and parts[1] in PLATFORM_DIRECTORIES:
        return parts[0], parts[1]
    else:
        # there is definitely no platform component
        if value in (None, '', '/', '//'):
            return '/', None
        else:
            return value, None


TOKEN_RE = re.compile(r'(/t/[a-z0-9A-Z-]+)?(\S*)?')
def split_token(value):
    token, path = TOKEN_RE.match(value).groups()
    return token, path or '/'


class UrlChannel(Channel):

    def __init__(self, url):
        log.debug("making channel object for url: %s", url)
        if url.endswith('.tar.bz2'):
            # throw away filename from url
            url = url.rsplit('/', 1)[0]
        if not has_scheme(url):
            url = path_to_url(url)
        self._raw_value = url
        parsed = urlparse(url)
        self._scheme = parsed.scheme
        self._netloc = parsed.netloc
        _path, self._platform = split_platform(parsed.path)
        self._token, self._path = split_token(_path)

    def __repr__(self):
        return "UrlChannel(%s)" % urlunparse(('', self._netloc, self._path.lstrip('/'), None, None, None)).lstrip('/')


class NamedChannel(Channel):

    def __init__(self, name):
        log.debug("making channel object for named channel: %s", name)
        self._raw_value = name
        if name in context.custom_channels:
            parsed = urlparse(context.custom_channels[name])
        elif name.split('/')[0] in context.custom_channels:
            parsed = urlparse(context.custom_channels[name.split('/')[0]])
        else:
            parsed = urlparse(context.channel_alias)
        self._scheme = parsed.scheme
        self._netloc = parsed.netloc
        self._path = join(parsed.path, name)
        self._platform = None

    def __repr__(self):
        return "NamedChannel(%s)" % self._raw_value


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
    result = odict()
    for q, chn in enumerate(channels):
        channel = Channel(chn)
        for url in channel.urls:
            if url in result:
                continue
            result[url] = channel.canonical_name, q
    return result


def offline_keep(url):
    return not context.offline or not is_url(url) or url.startswith('file:/')


_SPECIAL_CHANNELS = {
    None: NoneChannel,
}
