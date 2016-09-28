# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from itertools import chain
from logging import getLogger
from requests.packages.urllib3.util import Url

try:
    from cytoolz.functoolz import excepts
    from cytoolz.itertoolz import concatv, topk
except ImportError:
    from .._vendor.toolz.functoolz import excepts
    from .._vendor.toolz.itertoolz import concatv, topk

from ..base.constants import RECOGNIZED_URL_SCHEMES, RESERVED_CHANNELS
from ..base.context import context
from ..common.compat import odict, with_metaclass, iteritems
from ..common.url import (is_url, urlparse, join_url, split_scheme_auth_token,
                          split_conda_url_easy_parts, is_windows_path, path_to_url, on_win)

log = getLogger(__name__)


# backward compatibility for conda-build
def get_conda_build_local_url():
    return context.local_build_root,


def has_scheme(value):
    return bool(urlparse(value).scheme in RECOGNIZED_URL_SCHEMES)

"""
scheme <> auth <> location <> token <> channel <> subchannel <> platform <> package_filename

channel <> subchannel <> namespace <> package_name

"""


def tokenized_startswith(test_iterable, startswith_iterable):
    return all(t == sw for t, sw in zip(test_iterable, startswith_iterable))


def tokenized_conda_url_startswith(test_url, startswith_url):
    test_url, startswith_url = urlparse(test_url), urlparse(startswith_url)
    if test_url.host != startswith_url.host or test_url.port != startswith_url.port:
        return False
    norm_url_path = lambda url: url.path.strip('/') or '/'
    return tokenized_startswith(norm_url_path(test_url).split('/'),
                                norm_url_path(startswith_url).split('/'))


def _get_location_for_name(name, subname=None):
    if subname and join_url(name, subname) in context.custom_channels:
        location = context.custom_channels[join_url(name, subname)]
    elif name in context.custom_channels:
        location = context.custom_channels[name]
    elif name in RESERVED_CHANNELS:
        location = RESERVED_CHANNELS[name]
    else:
        location = context.channel_alias

    return split_scheme_auth_token(location)  # location, scheme, auth, token


def _read_channel_configuration(host, port, path):
    # return location, join_url(name, subname), scheme, auth, token

    test_url = Url(host=host, port=port, path=path).url.rstrip('/')

    # Step 1. migrated_custom_channels matches
    for name, location in iteritems(context.migrated_custom_channels):
        location, scheme, auth, token = split_scheme_auth_token(location)
        if tokenized_conda_url_startswith(test_url, join_url(location, name)):
            subname = test_url.replace(join_url(location, name), '', 1).strip('/')
            # translate location to new location, with new credentials
            location, scheme, auth, token = _get_location_for_name(name, subname)
            return location, join_url(name, subname), scheme, auth, token

    # Step 2. migrated_channel_aliases matches
    for migrated_alias in context.migrated_channel_aliases:
        migrated_alias_location, scheme, auth, token = split_scheme_auth_token(migrated_alias)
        if test_url.startswith(migrated_alias_location):
            name = test_url.replace(migrated_alias_location, '', 1).strip('/')
            channel_alias_location, scheme, auth, token = split_scheme_auth_token(context.channel_alias)
            return channel_alias_location, name, scheme, auth, token

    # Step 3. RESERVED_CHANNELS matches
    for name, location in concatv(iteritems(context.custom_channels), iteritems(RESERVED_CHANNELS)):
        location, scheme, auth, token = split_scheme_auth_token(location)
        if tokenized_conda_url_startswith(test_url, join_url(location, name)):
            subname = test_url.replace(join_url(location, name), '', 1).strip('/')
            return location, join_url(name, subname), scheme, auth, token

    # Step 4. channel_alias match
    channel_alias_location, scheme, auth, token = split_scheme_auth_token(context.channel_alias)
    if test_url.startswith(channel_alias_location):
        name = test_url.replace(channel_alias_location, '', 1).strip('/')
        return channel_alias_location, name, scheme, auth, token

    # Step 5. fall through to host:port as channel_location and path as channel_name
    return Url(host=host, port=port).url.rstrip('/'), path.strip('/'), None, None, None


def parse_conda_channel_url(url):
    scheme, auth, token, platform, package_filename, host, port, path, query = split_conda_url_easy_parts(url)

    # recombine host, port, path to get a channel_name and channel_location
    channel_location, channel_name, configured_scheme, configured_auth, configured_token = _read_channel_configuration(host, port, path)

    # if we came out with no channel_location or channel_name, we need to figure it out from host, port, path
    assert channel_location is not None
    assert channel_name is not None

    return Channel(configured_scheme or scheme or 'https',
                   auth or configured_auth,
                   channel_location,
                   token or configured_token,
                   channel_name,
                   platform,
                   package_filename)


def split_name_subname(name):
    return name.split('/', 1) if '/' in name else (name, None)


class ChannelType(type):

    def __call__(cls, *args, **kwargs):
        if len(args) == 1 and not kwargs:
            value = args[0]
            if isinstance(value, Channel):
                return value
            elif value in Channel._cache_:
                return Channel._cache_[value]
            else:
                c = Channel.from_value(value)
                Channel._cache_[value] = c
                return c
        else:
            return super(ChannelType, cls).__call__(*args, **kwargs)


@with_metaclass(ChannelType)
class Channel(object):
    _cache_ = dict()

    @staticmethod
    def _reset_state():
        Channel._cache_ = dict()

    def __init__(self, scheme=None, auth=None, location=None, token=None, name=None,
                 platform=None, package_filename=None):
        self.scheme = scheme
        self.auth = auth
        self.location = location
        self.token = token
        self.name = name
        self.platform = platform
        self.package_filename = package_filename


    @property
    def channel_location(self):
        return self.location

    @property
    def channel_name(self):
        return self.name

    @staticmethod
    def from_url(url):
        return parse_conda_channel_url(url)

    @staticmethod
    def from_channel_name(channel_name):
        name, subname = split_name_subname(channel_name)
        location, scheme, auth, token = _get_location_for_name(name, subname)
        return Channel(scheme, auth, location, token, channel_name)

    @staticmethod
    def from_value(value):
        if value is None:
            return Channel(name="<unknown>")
        elif has_scheme(value):
            if value.startswith('file:') and on_win:
                value = value.replace('\\', '/')
            return Channel.from_url(value)
        elif value.startswith(('./', '..', '~', '/')) or is_windows_path(value):
            return Channel.from_url(path_to_url(value))
        elif value.endswith('.tar.bz2'):
            if value.startswith('file:') and on_win:
                value = value.replace('\\', '/')
            return Channel.from_url(value)
        else:
            # at this point assume we don't have a bare (non-scheme) url
            #   e.g. this would be bad:  repo.continuum.io/pkgs/free
            name, subname = split_name_subname(value)
            if value in context.custom_multichannels:
                return MultiChannel(value, context.custom_multichannels[value])
            elif value == 'defaults':
                return MultiChannel('defaults', context.default_channels)
            else:
                return Channel.from_channel_name(value)

    @property
    def canonical_name(self):
        name, subname = split_name_subname(self.name)

        for multiname, channels in iteritems(context.custom_multichannels):
            for channel in channels:
                this_name, _ = split_name_subname(channel.name)
                if name == this_name:
                    return multiname

        if any(self.name == c.name for c in context.default_channels):
            return 'defaults'

        return self.name  # TODO: review implications with mcg

    @property
    def urls(self):
        # if is multichannel, get all urls
        if self.platform:
            return [join_url(self.base_url, self.platform) + '/']
        else:
            return [
                join_url(self.base_url, context.subdir) + '/',
                join_url(self.base_url, 'noarch') + '/',
            ]

    @property
    def base_url(self):
        return "%s://%s/%s" % (self.scheme, self.location, self.name)

    def __eq__(self, other):
        return self.location == other.location and self.name == other.name

    def __hash__(self):
        return hash((self.location, self.name))

    @property
    def url_channel_wtf(self):
        return self.base_url, self.canonical_name


class MultiChannel(Channel):

    def __init__(self, name, channels):
        self.name = name
        self.location = None
        self._channels = channels

        self.scheme = None
        self.auth = None
        self.token = None
        self.platform = None
        self.package_filename = None

    @property
    def channel_location(self):
        return self.location

    @property
    def canonical_name(self):
        return self.name

    @property
    def urls(self):
        return list(chain.from_iterable(c.urls for c in self._channels))

    @property
    def base_url(self):
        return None


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
