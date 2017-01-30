# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import namedtuple
import json
from logging import getLogger
import re

from .channel import Channel
from .index_record import IndexRecord
from .package_info import PackageInfo
from .. import CondaError
from ..base.constants import CONDA_TARBALL_EXTENSION, DEFAULTS_CHANNEL_NAME, UNKNOWN_CHANNEL
from ..common.compat import ensure_text_type, string_types, text_type, with_metaclass
from ..common.constants import NULL
from ..common.url import has_platform, is_url

log = getLogger(__name__)
DistDetails = namedtuple('DistDetails', ('name', 'version', 'build_string', 'build_number',
                                         'dist_name'))


def parse_legacy_dist_str(string):
    if isinstance(string, string_types):
        original_string = string
        try:
            string = ensure_text_type(string)

            no_tar_bz2_string = (string[:-len(CONDA_TARBALL_EXTENSION)]
                                 if string.endswith(CONDA_TARBALL_EXTENSION)
                                 else string)

            # remove any directory or channel information
            if '::' in no_tar_bz2_string:
                dist_name = no_tar_bz2_string.rsplit('::', 1)[-1]
            else:
                dist_name = no_tar_bz2_string.rsplit('/', 1)[-1]

            parts = dist_name.rsplit('-', 2)

            name = parts[0]
            version = parts[1]
            build_string = parts[2] if len(parts) >= 3 else ''
            build_number_as_string = ''.join(filter(lambda x: x.isdigit(),
                                                    (build_string.rsplit('_')[-1]
                                                     if build_string else '0')))
            build_number = int(build_number_as_string) if build_number_as_string else 0

            return DistDetails(name, version, build_string, build_number, dist_name)

        except:
            raise CondaError("dist_name is not a valid conda package: %s" % original_string)
    else:
        s = string
        return DistDetails(s.name, s.version, s.build, s.build_number, s.dist_name)


class DistType(type):

    def __call__(cls, *args, **kwargs):
        if len(args) == 1 and not kwargs:
            value = args[0]
            if isinstance(value, Dist):
                return value
            elif isinstance(value, string_types):
                return Dist.from_string(value)
            elif isinstance(value, IndexRecord):
                return Dist(value.schannel, '-'.join((value.name, value.version, value.build)), value.with_features_depends)
            elif isinstance(value, PackageInfo):
                v = value.repodata_record
                return Dist(value.channel.canonical_name, '-'.join((v.name, v.version, v.build)), v.with_features_depends)
            elif isinstance(value, Channel):
                raise NotImplementedError()
            else:
                return Dist.from_string(value)
        else:
            return super(DistType, cls).__call__(*args, **kwargs)

    def __new__(cls, name, bases, dct):
         dct['__slots__'] = ('channel', 'dist_name', 'with_features_depends')
         return type.__new__(cls, name, bases, dct)


@with_metaclass(DistType)
class Dist(object):

    def __init__(self, channel, dist_name=None, with_features_depends=None):
        self.channel = channel
        self.dist_name = dist_name
        self.with_features_depends = with_features_depends

    @property
    def base_url(self):
        raise NotImplementedError()

    @property
    def platform(self):
        raise NotImplementedError()

    @property
    def pkey(self):
        return self.__str__()

    def __hash__(self):
        return hash(self.pkey)

    def __eq__(self, other):
        return hash(self) == hash(other)

    @property
    def full_name(self):
        return self.__str__()

    @property
    def pair(self):
        return self.channel or DEFAULTS_CHANNEL_NAME, self.dist_name

    @property
    def triple(self):
        res = self.dist_name.rsplit('-', 2) + ['', '']
        return tuple(res[:3])

    @property
    def name(self):
        return self.triple[0]

    @property
    def version(self):
        return self.triple[1]

    @property
    def build(self):
        return self.triple[2]

    @property
    def build_string(self):
        return self.triple[2]

    @property
    def build_number(self):
        try:
            return int(self.build.rsplit('_', 1)[-1])
        except ValueError:
            return 0

    @property
    def quad(self):
        # returns: name, version, build_string, channel
        return self.triple + (self.channel or DEFAULTS_CHANNEL_NAME,)

    def __str__(self):
        if self.is_feature_package:
            return self.dist_name
        base = "%s::%s" % (self.channel, self.dist_name) if self.channel else self.dist_name
        if self.with_features_depends:
            return "%s[%s]" % (base, self.with_features_depends)
        else:
            return base

    def __repr__(self):
        args = tuple("%s=%s" % (s, getattr(self, s)) for s in self.__slots__)
        return "%s(%s)" % (self.__class__.__name__, ', '.join(args))

    def dump(self):
        return {s: getattr(self, s) for s in self.__slots__}

    def json(self):
        return json.dumps(self.dump())

    @property
    def is_feature_package(self):
        return self.dist_name.endswith('@')

    def to_filename(self, extension='.tar.bz2'):
        if self.is_feature_package:
            return self.dist_name
        else:
            return self.dist_name + extension

    def to_matchspec(self):
        return ' '.join(self.quad[:3])

    @classmethod
    def from_string(cls, string, channel_override=NULL):
        string = text_type(string)

        if is_url(string) and channel_override == NULL:
            return cls.from_url(string)

        if string.endswith('@'):
            return cls(channel='@',
                       dist_name=string,
                       with_features_depends=None)

        REGEX_STR = (r'(?:([^\s\[\]]+)::)?'        # optional channel
                     r'([^\s\[\]]+)'               # 3.x dist
                     r'(?:\[([a-zA-Z0-9_-]+)\])?'  # with_features_depends
                     )
        channel, original_dist, w_f_d = re.search(REGEX_STR, string).groups()

        if original_dist.endswith(CONDA_TARBALL_EXTENSION):
            original_dist = original_dist[:-len(CONDA_TARBALL_EXTENSION)]

        if channel_override != NULL:
            channel = channel_override
        elif channel is None:
            channel = DEFAULTS_CHANNEL_NAME

        return cls(channel=channel,
                   dist_name=original_dist,
                   with_features_depends=w_f_d)

    @staticmethod
    def parse_dist_name(string):
        original_string = string
        try:
            string = ensure_text_type(string)

            no_tar_bz2_string = (string[:-len(CONDA_TARBALL_EXTENSION)]
                                 if string.endswith(CONDA_TARBALL_EXTENSION)
                                 else string)

            # remove any directory or channel information
            if '::' in no_tar_bz2_string:
                dist_name = no_tar_bz2_string.rsplit('::', 1)[-1]
            else:
                dist_name = no_tar_bz2_string.rsplit('/', 1)[-1]

            return dist_name
        except:
            raise CondaError("dist_name is not a valid conda package: %s" % original_string)

    @classmethod
    def from_url(cls, url):
        assert is_url(url), url
        if not url.endswith(CONDA_TARBALL_EXTENSION) and '::' not in url:
            raise CondaError("url '%s' is not a conda package" % url)

        dist_name = cls.parse_dist_name(url)
        if '::' in url:
            url_no_tarball = url.rsplit('::', 1)[0]
            base_url = url_no_tarball.split('::')[0]
            channel = text_type(Channel(base_url))
        else:
            url_no_tarball = url.rsplit('/', 1)[0]
            platform = has_platform(url_no_tarball)
            base_url = url_no_tarball.rsplit('/', 1)[0] if platform else url_no_tarball
            channel = Channel(base_url).canonical_name if platform else UNKNOWN_CHANNEL

        return cls(channel=channel, dist_name=dist_name)

    def __key__(self):
        return self.channel, self.dist_name, self.with_features_depends

    def __lt__(self, other):
        assert isinstance(other, self.__class__)
        return self.__key__() < other.__key__()

    def __gt__(self, other):
        assert isinstance(other, self.__class__)
        return self.__key__() > other.__key__()

    def __le__(self, other):
        assert isinstance(other, self.__class__)
        return self.__key__() <= other.__key__()

    def __ge__(self, other):
        assert isinstance(other, self.__class__)
        return self.__key__() >= other.__key__()

    def __ne__(self, other):
        return not self.__eq__(other)

    # ############ conda-build compatibility ################

    def split(self, sep=None, maxsplit=-1):
        assert sep == '::'
        return [self.channel, self.dist_name] if self.channel else [self.dist_name]

    def rsplit(self, sep=None, maxsplit=-1):
        assert sep == '-'
        assert maxsplit == 2
        name = '%s::%s' % (self.channel, self.quad[0]) if self.channel else self.quad[0]
        return name, self.quad[1], self.quad[2]

    def startswith(self, match):
        return self.dist_name.startswith(match)

    def __contains__(self, item):
        item = ensure_text_type(item)
        if item.endswith(CONDA_TARBALL_EXTENSION):
            item = item[:-len(CONDA_TARBALL_EXTENSION)]
        return item in self.__str__()

    @property
    def fn(self):
        return self.to_filename()
