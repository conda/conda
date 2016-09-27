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
from ..common.url import is_url, urlparse, join_url, strip_scheme, split_scheme_auth_token

log = getLogger(__name__)


# backward compatibility for conda-build
def get_conda_build_local_url():
    return context.local_build_root,


def has_scheme(value):
    return bool(urlparse(value).scheme in RECOGNIZED_URL_SCHEMES)




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


def _match_against_known_channel_locations(url):
    # returns the matched channel_location if a match is found
    # otherwise None
    test_url = split_scheme_auth_token(url)[0]
    found_channel_url = first(concatv(itervalues(context.custom_channels),
                                      itervalues(RESERVED_CHANNELS),
                                      context.channel_alias,
                                      ),
                              key=lambda u: test_url.startswith(split_scheme_auth_token(u)[0]))

    return split_scheme_auth_token(found_channel_url)


def _match_against_migrated_channel_locations(url):
    # returns the matched channel_location if a match is found
    # otherwise None
    test_url = split_scheme_auth_token(url)[0]
    found_channel_url = first(concatv(itervalues(context.migrated_custom_channels),
                                     context.migrated_channel_aliases,
                                     ),
                             key=lambda u: test_url.startswith(split_scheme_auth_token(u)[0]))
    return split_scheme_auth_token(found_channel_url)


def _get_location_for_name(channel_name):
    # no platform and no package_filename allowed in channel_name !!!!!
    matches = ((name, url) for name, url in concatv(iteritems(context.custom_channels),
                                                    iteritems(RESERVED_CHANNELS),
                                                    )
               if tokenized_startswith(channel_name.split('/'), name.split('/')))
    if matches:
        # max gives last max, but we want the first, so reverse
        name, channel_url = max(reversed(tuple(matches)), key=lambda x: x[0])

        residual_url = channel_name.replace(name, '', 1).strip('/')
        channel_location, scheme, auth, token = split_scheme_auth_token(channel_url)
    else:
        # no matches with custom_channels or RESERVED_CHANNELS, so use channel_alias
        name = channel_name
        residual_url = None
        channel_location, scheme, auth, token = split_scheme_auth_token(context.channel_alias)

    return scheme, auth, channel_location, token, name.strip('/'), residual_url


def _split_channel_location_name(host, port, path):
    # first look at context.migrated_custom_channels

    test_url = Url(host=host, port=port, path=path).url.rstrip('/')

    # def get_match(name, migrated_url):
    #     migrated_url = strip_scheme(migrated_url)
    #     if not test_url.startswith(migrated_url):
    #         return None
    #
    #     if not migrated_url.endswith(name):
    #         migrated_url = join_url(migrated_url, name)
    #
    #     residual = test_url.replace(migrated_url, '')
    #
    #     if residual and not residual.startswith('/'):
    #         return None
    #
    #     return name, residual.strip('/')  # residual is something like 'label/dev'
    #
    # matches = (match for match in (get_match(name, url)
    #                                for name, url in iteritems(context.migrated_custom_channels))
    #            if match)
    # matches = sorted(matches, key=lambda x: len(x[2]))
    #
    # if matches:
    #     # best match is longest residual
    #     name, residual = matches[-1]


    # second look at context.migrated_channel_aliases

    # if either above hits, will need to translate channel location from old to new
    # using channel_name, and modify test_url

    migrated_channel_location, scheme, auth, token = _match_against_migrated_channel_locations(test_url)
    if migrated_channel_location:
        # find channel name matches
        def get_matches(test_name):
            return (name for name in concatv(iterkeys(context.custom_channels),
                                             iterkeys(RESERVED_CHANNELS))
                    if tokenized_startswith(test_name.split('/'), name.split('/')))

        test_channel_name = test_url.replace(migrated_channel_location, '', 1).strip('/')
        best_match_channel_name = topk(1, get_matches(test_channel_name))[0]
        residual_path = test_channel_name.replace(best_match_channel_name, '', 1).strip('/')

        cn = _get_location_for_name(best_match_channel_name)

        import pdb; pdb.set_trace()




    # now check known channel locations
    #  - custom_channels
    #  - RESERVED_CHANNELS
    #  - channel_alias
    channel_location, scheme, auth, token = _match_against_known_channel_locations(test_url)

    if channel_location is None:
        channel_location = Url(host=host, port=port).url.strip('/')
        channel_name = path.strip('/')
    else:
        channel_name = test_url.replace(channel_location, '', 1).strip('/')
    return channel_location, channel_name, scheme, auth, token


def parse_conda_channel_url(url):
    # first remove an anaconda token from the url
    from conda.gateways.anaconda_client import extract_token_from_url
    cleaned_url, token = extract_token_from_url(url)

    url_parts = urlparse(cleaned_url)
    scheme = url_parts.scheme
    auth = url_parts.auth

    # tear parts off of path for package_filename and platform
    path = url_parts.path
    if path.endswith('.tar.bz2'):
        path, package_filename = path.rsplit('/', 1)
    else:
        package_filename = None
    path, platform = split_platform(path)

    # recombine what's left of path with netloc to get a channel_name and channel_location
    channel_location, channel_name, configured_scheme, configured_auth, configured_token = _split_channel_location_name(url_parts.host, url_parts.port, path)
    # # translate channel_location using context.migrated_channel_aliases and context.migrated_custom_channels
    # def translate_location(location):
    #     for name, url in iteritems(context.migrated_custom_channels):
    #         this_location = strip_scheme(url)
    #         if location == this_location:
    #             return name, this_location



    return CondaChannelUrl(scheme or configured_scheme or 'https',
                           auth or configured_auth,
                           channel_location, token or configured_token,
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
        return conda_channel_url_from_channel_name(channel_name)

    @property
    def canonical_name(self):
        if self.name in chain.from_iterable((iterkeys(context.custom_channels),
                                             iterkeys(RESERVED_CHANNELS))):
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


def conda_channel_url_from_channel_name(channel_name):
    def make(url, name):
        from conda.gateways.anaconda_client import extract_token_from_url
        cleaned_url, token = extract_token_from_url(url)
        url_parts = urlparse(cleaned_url)
        channel_location = Url(host=url_parts.host, port=url_parts.port, path=url_parts.path).url
        return CondaChannelUrl(url_parts.scheme, url_parts.auth, channel_location, token, name)

    if channel_name in context.custom_channels:
        return make(context.custom_channels[channel_name], channel_name)
    elif channel_name in RESERVED_CHANNELS:
        return make(RESERVED_CHANNELS[channel_name], channel_name)
    else:
        return make(context.channel_alias, channel_name)

