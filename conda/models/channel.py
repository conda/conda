# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import namedtuple
from conda._vendor.auxlib.collection import first
from conda.compat import itervalues
from itertools import chain
from logging import getLogger
from requests.packages.urllib3.util import Url

try:
    from cytoolz.functoolz import excepts
    from cytoolz.itertoolz import concatv, topk
except ImportError:
    from .._vendor.toolz.functoolz import excepts
    from .._vendor.toolz.itertoolz import concatv, topk

from ..base.constants import PLATFORM_DIRECTORIES, RECOGNIZED_URL_SCHEMES, RESERVED_CHANNELS, NULL
from ..base.context import context
from ..common.compat import odict, with_metaclass, iterkeys, iteritems
from ..common.url import is_url, urlparse, join_url, strip_scheme, split_scheme_auth_token, \
    split_conda_url_easy_parts

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


class ChannelType(type):

    def __call__(cls, value):
        if isinstance(value, Channel):
            return value
        elif value in Channel._cache_:
            return Channel._cache_[value]
        elif value is None:
            self = object.__new__(NoneChannel)
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
    _channel_alias_netloc = urlparse(context.channel_alias).netloc
    _old_channel_alias_netloc = tuple(urlparse(ca).netloc
                                      for ca in context.migrated_channel_aliases)

    @staticmethod
    def _reset_state():
        Channel._cache_ = dict()
        Channel._channel_alias_netloc = urlparse(context.channel_alias).netloc
        Channel._old_channel_alias_netloc = tuple(urlparse(ca).netloc
                                                  for ca in context.migrated_channel_aliases)

    @property
    def base_url(self):
        # _path = excepts(AttributeError, lambda: self._path.lstrip('/'))()
        # if self._token_path:
        #     _path = self._token_path + '/' + _path
        # if self._netloc in Channel._old_channel_alias_netloc:
        #     ca = Channel(context.channel_alias)
        #     return urlunparse((ca._scheme, ca._netloc, _path, None, None, None))
        # else:
        #     return urlunparse((self._scheme, self._netloc, _path, None, None, None))
        return

    def __eq__(self, other):
        return self._netloc == other._netloc and self._path == other._path

    def __hash__(self):
        return hash((self._netloc, self._path))

    # @property
    # def canonical_name(self):
    #     if self in context.inverted_channel_map:
    #         return context.inverted_channel_map[self]
    #     elif self._netloc == Channel._channel_alias_netloc:
    #         return self._path.strip('/')
    #     elif self._netloc in Channel._old_channel_alias_netloc:
    #         return self._path.strip('/')
    #     else:
    #         return self.base_url

    @property
    def canonical_name(self):
        if self.name in chain.from_iterable((iterkeys(context.custom_channels),
                                             iterkeys(RESERVED_CHANNELS))):
            return self.name
        elif self.location == context.channel_alias:
            return self.name
        else:
            return join_url(self.location, self.name)

    def _urls_helper(self):
        return [join_url(self.base_url, context.subdir) + '/',
                join_url(self.base_url, 'noarch') + '/',
                ]

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


# def split_platform(value):
#     if value is None:
#         return '/', None
#     value = value.rstrip('/')
#     parts = value.rsplit('/', 1)
#     if len(parts) == 2 and parts[1] in PLATFORM_DIRECTORIES:
#         return parts[0], parts[1]
#     else:
#         # there is definitely no platform component
#         if value in (None, '', '/', '//'):
#             return '/', None
#         else:
#             return value, None


# TOKEN_RE = re.compile(r'(/t/[a-z0-9A-Z-]+)?(\S*)?')
# def split_token(value):  # NOQA
#     token_path, path = TOKEN_RE.match(value).groups()
#     return token_path, path or '/'




class UrlChannel(Channel):

    # def __init__(self, url):
    #     log.debug("making channel object for url: %s", url)
    #     if url.endswith('.tar.bz2'):
    #         # throw away filename from url
    #         url = url.rsplit('/', 1)[0]
    #     if not has_scheme(url):
    #         url = path_to_url(url)
    #     self._raw_value = url
    #     parsed = urlparse(url)
    #     self._scheme = parsed.scheme
    #     self._netloc = parsed.netloc
    #     _path, self._platform = split_platform(parsed.path)
    #     self._token_path, self._path = split_token(_path)

    def __init__(self, url):
        log.debug("making channel object for url: %s", url)
        self._raw_value = url
        parsed = parse_conda_channel_url(url)
        self.scheme = parsed.scheme
        self.auth = parsed.auth
        self.channel_location = parsed.location
        self.token = parsed.token
        self.channel_name = parsed.name
        self.platform = parsed.platform

    # def __repr__(self):
    #     return "UrlChannel(%s)" % urlunparse(('', self._netloc, self._path.lstrip('/'),
    #                                           None, None, None)).lstrip('/')


# def _match_against_known_channel_locations(url):
#     # returns the matched channel_location if a match is found
#     # otherwise None
#     test_url = strip_scheme(url)
#     channel_location = first(context.known_channel_locations,
#                              key=lambda u: test_url.startswith(strip_scheme(u)),
#                              apply=strip_scheme)
#     return channel_location


def tokenized_startswith(test_iterable, startswith_iterable):
    return all(t == sw for t, sw in zip(test_iterable, startswith_iterable))


def tokenized_conda_url_startswith(test_url, startswith_url):
    test_url, startswith_url = urlparse(test_url), urlparse(startswith_url)
    if test_url.host != startswith_url.host or test_url.port != startswith_url.port:
        return False
    norm_url_path = lambda url: url.path.strip('/') or '/'
    return tokenized_startswith(norm_url_path(test_url).split('/'),
                                norm_url_path(startswith_url).split('/'))


# def _match_against_known_channel_locations(url):
#     # returns the matched channel_location if a match is found
#     # otherwise None
#     test_url = split_scheme_auth_token(url)[0]
#     found_channel_url = first(concatv(itervalues(context.custom_channels),
#                                       itervalues(RESERVED_CHANNELS),
#                                       context.channel_alias,
#                                       ),
#                               key=lambda u: test_url.startswith(split_scheme_auth_token(u)[0]))
#
#     return split_scheme_auth_token(found_channel_url)


# def _match_against_migrated_channel_locations(url):
#     # returns the matched channel_location if a match is found
#     # otherwise None
#     test_url = split_scheme_auth_token(url)[0]
#
#
#     found_channel_url = first(concatv(itervalues(context.migrated_custom_channels),
#                                      context.migrated_channel_aliases,
#                                      ),
#                              key=lambda u: test_url.startswith(split_scheme_auth_token(u)[0]))
#     return split_scheme_auth_token(found_channel_url)


# def _get_location_for_name(channel_name):
#     # no platform and no package_filename allowed in channel_name !!!!!
#     matches = ((name, url) for name, url in concatv(iteritems(context.custom_channels),
#                                                     iteritems(RESERVED_CHANNELS),
#                                                     )
#                if tokenized_startswith(channel_name.split('/'), name.split('/')))
#     if matches:
#         # max gives last max, but we want the first, so reverse
#         name, channel_url = max(reversed(tuple(matches)), key=lambda x: x[0])
#
#         residual_url = channel_name.replace(name, '', 1).strip('/')
#         channel_location, scheme, auth, token = split_scheme_auth_token(channel_url)
#     else:
#         # no matches with custom_channels or RESERVED_CHANNELS, so use channel_alias
#         name = channel_name
#         residual_url = None
#         channel_location, scheme, auth, token = split_scheme_auth_token(context.channel_alias)
#
#     return scheme, auth, channel_location, token, name.strip('/'), residual_url


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

    return None, None, None, None, None


def parse_conda_channel_url(url):
    scheme, auth, token, platform, package_filename, host, port, path, query = split_conda_url_easy_parts(url)

    # recombine host, port, path to get a channel_name and channel_location
    channel_location, channel_name, configured_scheme, configured_auth, configured_token = _read_channel_configuration(host, port, path)

    # if we came out with no channel_location or channel_name, we need to figure it out from host, port, path
    assert channel_location is not None
    assert channel_name is not None

    return CondaChannelUrl(configured_scheme or 'https',
                           auth or configured_auth,
                           channel_location,
                           token or configured_token,
                           channel_name,
                           platform,
                           package_filename)


conda_channel_url_attrs = ['scheme', 'auth', 'location', 'token', 'name',
                           'platform', 'package_filename']


class CondaChannelUrl(namedtuple('CondaChannelUrl', conda_channel_url_attrs)):
    __slots__ = ()

    def __new__(cls, scheme=None, auth=None, location=None, token=None, name=None,
                platform=None, package_filename=None):
        return super(CondaChannelUrl, cls).__new__(cls, scheme, auth, location, token, name,
                                                   platform, package_filename)

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
        name, subname = channel_name.split('/', 1) if '/' in channel_name else (channel_name, None)
        location, scheme, auth, token = _get_location_for_name(name, subname)
        return CondaChannelUrl(scheme, auth, location, token, channel_name)

    @staticmethod
    def from_value(value):
        if value is None:
            self = object.__new__(NoneChannel)
        elif value.endswith('.tar.bz2') or has_scheme(value):
            return CondaChannelUrl.from_url(value)
        else:
            return CondaChannelUrl.from_channel_name(value)

    @property
    def canonical_name(self):
        if self.name in context.custom_channels or self.name in RESERVED_CHANNELS:
            return self.name
        elif self.location == context.channel_alias:
            return self.name
        else:
            return join_url(self.location, self.name)

    @property
    def base_url(self):
        return "%s://%s/%s" % (self.scheme, self.location, self.name)

    def __eq__(self, other):
        return self.location == other.location and self.name == other.name

    def __hash__(self):
        return hash((self.location, self.name))


class NamedChannel(Channel):

    # def __init__(self, name):
    #     log.debug("making channel object for named channel: %s", name)
    #     self._raw_value = name
    #     if name in context.custom_channels:
    #         parsed = urlparse(context.custom_channels[name])
    #     elif name.split('/')[0] in context.custom_channels:
    #         parsed = urlparse(context.custom_channels[name.split('/')[0]])
    #     else:
    #         parsed = urlparse(context.channel_alias)
    #     self._scheme = parsed.scheme
    #     self._netloc = parsed.netloc
    #     self._token_path = None
    #     self._path = join(parsed.path or '/', name)
    #     self._platform = None
    #
    # def __repr__(self):
    #     return "NamedChannel(%s)" % self._raw_value


    def __init__(self, name):
        log.debug("making channel object for named channel: %s", name)
        self._raw_value = name

        self.channel_name = name
        self.platform = None

        parsed = conda_channel_url_from_channel_name(name)
        self.scheme = parsed.scheme
        self.auth = parsed.auth
        self.channel_location = parsed.location
        self.token = parsed.token


class NoneChannel(NamedChannel):

    def __init__(self, value):
        self._raw_value = value
        self._scheme = self._netloc = self._token_path = self._path = self._platform = None

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
