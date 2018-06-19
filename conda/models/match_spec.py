# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

from abc import ABCMeta, abstractmethod, abstractproperty
from collections import Mapping
from functools import reduce
from os.path import basename
import re

from .channel import Channel
from .dist import Dist
from .records import PackageRecord, PackageRef
from .version import BuildNumberMatch, VersionSpec
from .._vendor.auxlib.collection import frozendict
from ..base.constants import CONDA_TARBALL_EXTENSION
from ..common.compat import (isiterable, iteritems, itervalues, string_types, text_type,
                             with_metaclass)
from ..common.path import expand
from ..common.url import is_url, path_to_url, unquote
from ..exceptions import CondaValueError

try:
    from cytoolz.itertoolz import concat, concatv, groupby
except ImportError:  # pragma: no cover
    from .._vendor.toolz.itertoolz import concat, concatv, groupby  # NOQA


class MatchSpecType(type):

    def __call__(cls, spec_arg=None, **kwargs):
        if spec_arg:
            if isinstance(spec_arg, MatchSpec) and not kwargs:
                return spec_arg
            elif isinstance(spec_arg, MatchSpec):
                new_kwargs = dict(spec_arg._match_components)
                new_kwargs.setdefault('optional', spec_arg.optional)
                new_kwargs.setdefault('target', spec_arg.target)
                new_kwargs.update(**kwargs)
                return super(MatchSpecType, cls).__call__(**new_kwargs)
            elif isinstance(spec_arg, string_types):
                parsed = _parse_spec_str(spec_arg)
                parsed.update(kwargs)
                return super(MatchSpecType, cls).__call__(**parsed)
            elif isinstance(spec_arg, Mapping):
                parsed = dict(spec_arg, **kwargs)
                return super(MatchSpecType, cls).__call__(**parsed)
            elif isinstance(spec_arg, PackageRef):
                parsed = {
                    'channel': spec_arg.channel,
                    'subdir': spec_arg.subdir,
                    'name': spec_arg.name,
                    'version': spec_arg.version,
                    'build': spec_arg.build,
                }
                parsed.update(kwargs)
                return super(MatchSpecType, cls).__call__(**parsed)
            elif isinstance(spec_arg, Dist):
                # TODO: remove this branch when we get rid of Dist
                parsed = {
                    'name': spec_arg.name,
                    'version': spec_arg.version,
                    'build': spec_arg.build,
                }
                if spec_arg.channel:
                    parsed['channel'] = spec_arg.channel
                if spec_arg.subdir:
                    parsed['subdir'] = spec_arg.subdir
                parsed.update(kwargs)
                return super(MatchSpecType, cls).__call__(**parsed)
            elif hasattr(spec_arg, 'dump'):
                parsed = spec_arg.dump()
                parsed.update(kwargs)
                return super(MatchSpecType, cls).__call__(**parsed)
            else:
                raise CondaValueError("Invalid MatchSpec:\n  spec_arg=%s\n  kwargs=%s"
                                      % (spec_arg, kwargs))
        else:
            return super(MatchSpecType, cls).__call__(**kwargs)


@with_metaclass(MatchSpecType)
class MatchSpec(object):
    """
    :class:`MatchSpec` is, fundamentally, a query language for conda packages.  Any of the fields
    that comprise a :class:`PackageRecord` can be used to compose a :class:`MatchSpec`.

    :class:`MatchSpec` can be composed with keyword arguments, where keys are any of the
    attributes of :class:`PackageRecord`.  Values for keyword arguments are the exact values the
    attribute should match against.  Many fields can also be matched against non-exact values--by
    including wildcard `*` and `>`/`<` ranges--where supported.  Any non-specified field is
    the equivalent of a full wildcard match.

    :class:`MatchSpec` can also be composed using a single positional argument, with optional
    keyword arguments.  Keyword arguments also override any conflicting information provided in
    the positional argument.  The positional argument can be either an existing :class:`MatchSpec`
    instance or a string.  Conda has historically had several string representations for equivalent
    :class:`MatchSpec`s.  This :class:`MatchSpec` should accept any existing valid spec string, and
    correctly compose a :class:`MatchSpec` instance.

    A series of rules are now followed for creating the canonical string representation of a
    :class:`MatchSpec` instance.  The canonical string representation can generically be
    represented by

        (channel(/subdir):(namespace):)name(version(build))[key1=value1,key2=value2]

    where `()` indicate optional fields.  The rules for constructing a canonical string
    representation are:

    1. `name` (i.e. "package name") is required, but its value can be '*'.  Its position is always
       outside the key-value brackets.
    2. If `version` is an exact version, it goes outside the key-value brackets and is prepended
       by `==`. If `version` is a "fuzzy" value (e.g. `1.11.*`), it goes outside the key-value
       brackets with the `.*` left off and is prepended by `=`.  Otherwise `version` is included
       inside key-value brackets.
    3. If `version` is an exact version, and `build` is an exact value, `build` goes outside
       key-value brackets prepended by a `=`.  Otherwise, `build` goes inside key-value brackets.
       `build_string` is an alias for `build`.
    4. The `namespace` position is being held for a future conda feature.
    5. If `channel` is included and is an exact value, a `::` separator is ued between `channel`
       and `name`.  `channel` can either be a canonical channel name or a channel url.  In the
       canonical string representation, the canonical channel name will always be used.
    6. If `channel` is an exact value and `subdir` is an exact value, `subdir` is appended to
       `channel` with a `/` separator.  Otherwise, `subdir` is included in the key-value brackets.
    7. Key-value brackets can be delimited by comma, space, or comma+space.  Value can optionally
       be wrapped in single or double quotes, but must be wrapped if `value` contains a comma,
       space, or equal sign.  The canonical format uses comma delimiters and single quotes.
    8. When constructing a :class:`MatchSpec` instance from a string, any key-value pair given
       inside the key-value brackets overrides any matching parameter given outside the brackets.

    When :class:`MatchSpec` attribute values are simple strings, the are interpreted using the
    following conventions:

      - If the string begins with `^` and ends with `$`, it is converted to a regex.
      - If the string contains an asterisk (`*`), it is transformed from a glob to a regex.
      - Otherwise, an exact match to the string is sought.


    Examples:

        >>> str(MatchSpec(name='foo', build='py2*', channel='conda-forge'))
        'conda-forge::foo[build=py2*]'
        >>> str(MatchSpec('foo 1.0 py27_0'))
        'foo==1.0=py27_0'
        >>> str(MatchSpec('foo=1.0=py27_0'))
        'foo==1.0=py27_0'
        >>> str(MatchSpec('conda-forge::foo[version=1.0.*]'))
        'conda-forge::foo=1.0'
        >>> str(MatchSpec('conda-forge/linux-64::foo>=1.0'))
        "conda-forge/linux-64::foo[version='>=1.0']"
        >>> str(MatchSpec('*/linux-64::foo>=1.0'))
        "foo[subdir=linux-64,version='>=1.0']"

    To fully-specify a package with a full, exact spec, the fields
      - channel
      - subdir
      - name
      - version
      - build
    must be given as exact values.  In the future, the namespace field will be added to this list.
    Alternatively, an exact spec is given by '*[md5=12345678901234567890123456789012]'.

    """

    FIELD_NAMES = (
        'channel',
        'subdir',
        'namespace',
        'name',
        'version',
        'build',
        'build_number',
        'track_features',
        'features',
        'url',
        'md5',
        'license',
        'license_family',
    )

    def __init__(self, optional=False, target=None, **kwargs):
        self.optional = optional
        self.target = target
        self._match_components = self._build_components(**kwargs)

    @classmethod
    def from_dist_str(cls, dist_str):
        parts = {}
        if dist_str.endswith(CONDA_TARBALL_EXTENSION):
            dist_str = dist_str[:-len(CONDA_TARBALL_EXTENSION)]
        if '::' in dist_str:
            channel_str, dist_str = dist_str.split("::", 1)
            parts['channel'] = channel_str
        name, version, build = dist_str.rsplit('-', 2)
        parts.update({
            'name': name,
            'version': version,
            'build': build,
        })
        return cls(**parts)

    def get_exact_value(self, field_name):
        v = self._match_components.get(field_name)
        return v and v.exact_value

    def get_raw_value(self, field_name):
        v = self._match_components.get(field_name)
        return v and v.raw_value

    def get(self, field_name, default=None):
        v = self.get_raw_value(field_name)
        return default if v is None else v

    @property
    def is_name_only_spec(self):
        return (len(self._match_components) == 1
                and 'name' in self._match_components
                and self.name != '*')

    def dist_str(self):
        return self.__str__()

    def match(self, rec):
        """
        Accepts an `IndexRecord` or a dict, and matches can pull from any field
        in that record.  Returns True for a match, and False for no match.
        """
        if isinstance(rec, dict):
            rec = PackageRecord.from_objects(rec)
        for field_name, v in iteritems(self._match_components):
            if not self._match_individual(rec, field_name, v):
                return False
        return True

    def _match_individual(self, record, field_name, match_component):
        val = getattr(record, field_name)
        try:
            return match_component.match(val)
        except AttributeError:
            return match_component == val

    def _is_simple(self):
        return len(self._match_components) == 1 and self.get_exact_value('name') is not None

    def _is_single(self):
        return len(self._match_components) == 1

    def _to_filename_do_not_use(self):
        # WARNING: this is potentially unreliable and use should probably be limited
        #   returns None if a filename can't be constructed
        fn_field = self.get_exact_value('fn')
        if fn_field:
            return fn_field
        vals = tuple(self.get_exact_value(x) for x in ('name', 'version', 'build'))
        if not any(x is None for x in vals):
            return '%s-%s-%s.tar.bz2' % vals
        else:
            return None

    def __repr__(self):
        builder = []
        builder += ["%s=%r" % (c, self._match_components[c])
                    for c in self.FIELD_NAMES if c in self._match_components]
        if self.optional:
            builder.append("optional=True")
        if self.target:
            builder.append("target=%r" % self.target)
        return "%s(%s)" % (self.__class__.__name__, ', '.join(builder))

    def __str__(self):
        builder = []
        brackets = []

        channel_matcher = self._match_components.get('channel')
        if channel_matcher and channel_matcher.exact_value:
            builder.append(text_type(channel_matcher))
        elif channel_matcher and not channel_matcher.matches_all:
            brackets.append("channel=%s" % text_type(channel_matcher))

        subdir_matcher = self._match_components.get('subdir')
        if subdir_matcher:
            if channel_matcher and channel_matcher.exact_value:
                builder.append('/%s' % subdir_matcher)
            else:
                brackets.append("subdir=%s" % subdir_matcher)

        namespace_matcher = self._match_components.get('namespace')
        if namespace_matcher:
            namespace_matcher = text_type(namespace_matcher)
        if namespace_matcher:
            if builder:
                builder.append(':')
            builder.append("%s:" % namespace_matcher)
        elif builder:
            builder.append("::")

        name_matcher = self._match_components.get('name', '*')
        builder.append(text_type(name_matcher))

        version_exact = False
        version = self._match_components.get('version')
        if version:
            version = text_type(version)
            if any(s in version for s in '><$^|,'):
                brackets.append("version='%s'" % version)
            elif version.endswith('.*'):
                builder.append('=' + version[:-2])
            elif version.endswith('*'):
                builder.append('=' + version[:-1])
            elif version.startswith('=='):
                builder.append(version)
                version_exact = True
            else:
                builder.append('==' + version)
                version_exact = True

        build = self._match_components.get('build')
        if build:
            build = text_type(build)
            if any(s in build for s in '><$^|,'):
                brackets.append("build='%s'" % build)
            elif '*' in build:
                brackets.append("build=%s" % build)
            elif version_exact:
                builder.append('=' + build)
            else:
                brackets.append("build=%s" % build)

        _skip = ('channel', 'subdir', 'namespace', 'name', 'version', 'build')
        for key in self.FIELD_NAMES:
            if key not in _skip and key in self._match_components:
                if key == 'url' and channel_matcher:
                    # skip url in canonical str if channel already included
                    continue
                value = text_type(self._match_components[key])
                if any(s in value for s in ', ='):
                    brackets.append("%s='%s'" % (key, value))
                else:
                    brackets.append("%s=%s" % (key, value))

        if brackets:
            builder.append('[%s]' % ','.join(brackets))

        return ''.join(builder)

    def __json__(self):
        return self.__str__()

    def conda_build_form(self):
        builder = []
        name = self.get_exact_value('name')
        assert name
        builder.append(name)

        build = self.get_raw_value('build')
        version = self.get_raw_value('version')

        if build:
            assert version
            builder += [version, build]
        elif version:
            builder.append(version)

        return ' '.join(builder)

    def __eq__(self, other):
        if isinstance(other, MatchSpec):
            self_key = self._match_components, self.optional, self.target
            other_key = other._match_components, other.optional, other.target
            return self_key == other_key
        else:
            return False

    def __hash__(self):
        return hash((self._match_components, self.optional, self.target))

    def __contains__(self, field):
        return field in self._match_components

    @staticmethod
    def _build_components(**kwargs):
        def _make(field_name, value):
            if field_name not in PackageRecord.__fields__ and field_name != 'namespace':
                raise CondaValueError('Cannot match on field %s' % (field_name,))
            elif isinstance(value, string_types):
                value = text_type(value)

            if hasattr(value, 'match'):
                matcher = value
            elif field_name in _implementors:
                matcher = _implementors[field_name](value)
            else:
                matcher = StrMatch(text_type(value))

            return field_name, matcher

        return frozendict(_make(key, value) for key, value in iteritems(kwargs))

    @property
    def name(self):
        return self.get_exact_value('name') or '*'

    #
    # Remaining methods are for back compatibility with conda-build. Do not remove
    # without coordination with the conda-build team.
    #
    @property
    def strictness(self):
        # With the old MatchSpec, strictness==3 if name, version, and
        # build were all specified.
        s = sum(f in self._match_components for f in ('name', 'version', 'build'))
        if s < len(self._match_components):
            return 3
        elif not self.get_exact_value('name') or 'build' in self._match_components:
            return 3
        elif 'version' in self._match_components:
            return 2
        else:
            return 1

    @property
    def spec(self):
        return self.conda_build_form()

    @property
    def version(self):
        # in the old MatchSpec object, version was a VersionSpec, not a str
        # so we'll keep that API here
        return self._match_components.get('version')

    @property
    def fn(self):
        val = self.get_raw_value('fn') or self.get_raw_value('url')
        if val:
            val = basename(val)
        assert val
        return val

    @classmethod
    def merge(cls, match_specs):
        match_specs = tuple(cls(s) for s in match_specs)
        grouped = groupby(lambda spec: spec.get_exact_value('name'), match_specs)
        dont_merge_these = grouped.pop('*', []) + grouped.pop(None, [])
        specs_map = {
            name: reduce(lambda x, y: x._merge(y), specs) if len(specs) > 1 else specs[0]
            for name, specs in iteritems(grouped)
        }
        return tuple(concatv(itervalues(specs_map), dont_merge_these))

    def _merge(self, other):
        if self.optional != other.optional or self.target != other.target:
            raise ValueError("Incompatible MatchSpec merge:  - %s\n  - %s" % (self, other))

        final_components = {}
        component_names = set(self._match_components) | set(other._match_components)
        for component_name in component_names:
            this_component = self._match_components.get(component_name)
            that_component = other._match_components.get(component_name)
            if this_component is None and that_component is None:
                continue
            elif this_component is None:
                final_components[component_name] = that_component
            elif that_component is None:
                final_components[component_name] = this_component
            else:
                final_components[component_name] = this_component.merge(that_component)

        return self.__class__(optional=self.optional, target=self.target, **final_components)


def _parse_version_plus_build(v_plus_b):
    """This should reliably pull the build string out of a version + build string combo.
    Examples:
        >>> _parse_version_plus_build("=1.2.3 0")
        ('=1.2.3', '0')
        >>> _parse_version_plus_build("1.2.3=0")
        ('1.2.3', '0')
        >>> _parse_version_plus_build(">=1.0 , < 2.0 py34_0")
        ('>=1.0,<2.0', 'py34_0')
        >>> _parse_version_plus_build(">=1.0 , < 2.0 =py34_0")
        ('>=1.0,<2.0', 'py34_0')
        >>> _parse_version_plus_build("=1.2.3 ")
        ('=1.2.3', None)
        >>> _parse_version_plus_build(">1.8,<2|==1.7")
        ('>1.8,<2|==1.7', None)
        >>> _parse_version_plus_build("* openblas_0")
        ('*', 'openblas_0')
        >>> _parse_version_plus_build("* *")
        ('*', '*')
    """
    parts = re.search(r'((?:.+?)[^><!,|]?)(?:(?<![=!|,<>])(?:[ =])([^-=,|<>]+?))?$', v_plus_b)
    if parts:
        version, build = parts.groups()
        build = build and build.strip()
    else:
        version, build = v_plus_b, None

    return version and version.replace(' ', ''), build


def _parse_legacy_dist(dist_str):
    """
    Examples:
        >>> _parse_legacy_dist("_license-1.1-py27_1.tar.bz2")
        ('_license', '1.1', 'py27_1')
        >>> _parse_legacy_dist("_license-1.1-py27_1")
        ('_license', '1.1', 'py27_1')
    """
    if dist_str.endswith(CONDA_TARBALL_EXTENSION):
        dist_str = dist_str[:-len(CONDA_TARBALL_EXTENSION)]
    name, version, build = dist_str.rsplit('-', 2)
    return name, version, build


def _parse_channel(channel_val):
    if not channel_val:
        return None, None
    chn = Channel(channel_val)
    channel_name = chn.name
    return channel_name, chn.subdir


def _parse_spec_str(spec_str):
    # pre-step for ugly backward compat
    if spec_str.endswith('@'):
        feature_name = spec_str[:-1]
        return {
            'name': '*',
            'track_features': (feature_name,),
        }

    # Step 1. strip '#' comment
    if '#' in spec_str:
        ndx = spec_str.index('#')
        spec_str, _ = spec_str[:ndx], spec_str[ndx:]
        spec_str.strip()

    # Step 2. done if spec_str is a tarball
    if spec_str.endswith(CONDA_TARBALL_EXTENSION):
        # treat as a normal url
        if not is_url(spec_str):
            spec_str = unquote(path_to_url(expand(spec_str)))

        channel = Channel(spec_str)
        if channel.subdir:
            name, version, build = _parse_legacy_dist(channel.package_filename)
            result = {
                'channel': channel.canonical_name,
                'subdir': channel.subdir,
                'name': name,
                'version': version,
                'build': build,
                'fn': channel.package_filename,
                'url': spec_str,
            }
        else:
            # url is not a channel
            return {
                'name': '*',
                'fn': basename(spec_str),
                'url': spec_str,
            }
        return result

    # Step 3. strip off brackets portion
    brackets = {}
    m3 = re.match(r'.*(?:(\[.*\]))', spec_str)
    if m3:
        brackets_str = m3.groups()[0]
        spec_str = spec_str.replace(brackets_str, '')
        brackets_str = brackets_str[1:-1]
        m3b = re.finditer(r'([a-zA-Z0-9_-]+?)=(["\']?)([^\'"]*?)(\2)(?:[, ]|$)', brackets_str)
        for match in m3b:
            key, _, value, _ = match.groups()
            if not key or not value:
                raise CondaValueError("Invalid MatchSpec: %s" % spec_str)
            brackets[key] = value

    # Step 4. strip off parens portion
    m4 = re.match(r'.*(?:(\(.*\)))', spec_str)
    parens = {}
    if m4:
        parens_str = m4.groups()[0]
        spec_str = spec_str.replace(parens_str, '')
        parens_str = parens_str[1:-1]
        m4b = re.finditer(r'([a-zA-Z0-9_-]+?)=(["\']?)([^\'"]*?)(\2)(?:[, ]|$)', parens_str)
        for match in m4b:
            key, _, value, _ = match.groups()
            parens[key] = value
        if 'optional' in parens_str:
            parens['optional'] = True

    # Step 5. strip off '::' channel and namespace
    m5 = spec_str.rsplit(':', 2)
    m5_len = len(m5)
    if m5_len == 3:
        channel_str, namespace, spec_str = m5
        if not namespace:
            namespace = None
    elif m5_len == 2:
        namespace, spec_str = m5
        channel_str = None
        if not namespace:
            namespace = None
    elif m5_len:
        spec_str = m5[0]
        channel_str, namespace = None, None
    else:
        raise NotImplementedError()
    channel, subdir = _parse_channel(channel_str)
    if 'channel' in brackets:
        b_channel, b_subdir = _parse_channel(brackets.pop('channel'))
        if b_channel:
            channel = b_channel
        if b_subdir:
            subdir = b_subdir
    if 'subdir' in brackets:
        subdir = brackets.pop('subdir')

    # Step 6. strip off package name from remaining version + build
    m3 = re.match(r'([^ =<>!]+)?([><!= ].+)?', spec_str)
    if m3:
        name, spec_str = m3.groups()
        if name is None:
            raise CondaValueError("Invalid MatchSpec: %s" % spec_str)
    else:
        raise CondaValueError("Invalid MatchSpec: %s" % spec_str)

    # Step 7. otherwise sort out version + build
    spec_str = spec_str and spec_str.strip()
    # This was an attempt to make MatchSpec('numpy-1.11.0-py27_0') work like we'd want. It's
    # not possible though because plenty of packages have names with more than one '-'.
    # if spec_str is None and name.count('-') >= 2:
    #     name, version, build = _parse_legacy_dist(name)
    if spec_str:
        if '[' in spec_str:
            raise CondaValueError("Invalid MatchSpec: %s" % spec_str)

        version, build = _parse_version_plus_build(spec_str)

        # translate version '=1.2.3' to '1.2.3*'
        # is it a simple version starting with '='? i.e. '=1.2.3'
        if version.startswith('='):
            test_str = version[1:]
            if version.startswith('==') and build is None:
                version = version[2:]
            elif not any(c in test_str for c in "=,|"):
                if build is None and not test_str.endswith('*'):
                    version = test_str + '*'
                else:
                    version = test_str
    else:
        version, build = None, None

    # Step 8. now compile components together
    components = {}
    components['name'] = name if name else '*'

    if channel is not None:
        components['channel'] = channel
    if subdir is not None:
        components['subdir'] = subdir
    if namespace is not None:
        components['namespace'] = namespace
    if version is not None:
        components['version'] = version
    if build is not None:
        components['build'] = build

    # anything in brackets will now strictly override key as set in other area of spec str
    components.update(brackets)

    return components


@with_metaclass(ABCMeta)
class MatchInterface(object):

    def __init__(self, value):
        self._raw_value = value

    @abstractmethod
    def match(self, other):
        raise NotImplementedError()

    def matches(self, value):
        return self.match(value)

    @property
    def raw_value(self):
        return self._raw_value

    @abstractproperty
    def exact_value(self):
        """If the match value is an exact specification, returns the value.
        Otherwise returns None.
        """
        raise NotImplementedError()

    @abstractmethod
    def merge(self, other):
        raise NotImplementedError()


class SplitStrMatch(MatchInterface):
    __slots__ = '_raw_value',

    def __init__(self, value):
        super(SplitStrMatch, self).__init__(self._convert(value))

    def _convert(self, value):
        try:
            return frozenset(value.replace(' ', ',').split(','))
        except AttributeError:
            if isiterable(value):
                return frozenset(value)
            raise

    def match(self, other):
        try:
            return other and self._raw_value & other._raw_value
        except AttributeError:
            return self._raw_value & self._convert(other)

    def __repr__(self):
        if self._raw_value:
            return "{%s}" % ', '.join("'%s'" % s for s in sorted(self._raw_value))
        else:
            return 'set()'

    def __str__(self):
        # this space delimiting makes me nauseous
        return ' '.join(sorted(self._raw_value))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self._raw_value == other._raw_value

    def __hash__(self):
        return hash(self._raw_value)

    @property
    def exact_value(self):
        return self._raw_value

    def merge(self, other):
        if self.raw_value != other.raw_value:
            raise ValueError("Incompatible component merge:\n  - %r\n  - %r"
                             % (self.raw_value, other.raw_value))
        return self.raw_value


class FeatureMatch(MatchInterface):
    __slots__ = '_raw_value',

    def __init__(self, value):
        super(FeatureMatch, self).__init__(self._convert(value))

    def _convert(self, value):
        if not value:
            return frozenset()
        elif isinstance(value, string_types):
            return frozenset(f for f in (
                ff.strip() for ff in value.replace(' ', ',').split(',')
            ) if f)
        else:
            return frozenset(f for f in (ff.strip() for ff in value) if f)

    def match(self, other):
        other = self._convert(other)
        return self._raw_value == other

    def __repr__(self):
        return "[%s]" % ', '.join("'%s'" % k for k in sorted(self._raw_value))

    def __str__(self):
        return ' '.join(sorted(self._raw_value))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self._raw_value == other._raw_value

    def __hash__(self):
        return hash(self._raw_value)

    @property
    def exact_value(self):
        return self._raw_value

    def merge(self, other):
        if self.raw_value != other.raw_value:
            raise ValueError("Incompatible component merge:\n  - %r\n  - %r"
                             % (self.raw_value, other.raw_value))
        return self.raw_value


class StrMatch(MatchInterface):
    __slots__ = '_raw_value', '_re_match'

    def __init__(self, value):
        super(StrMatch, self).__init__(value)
        self._re_match = None

        if value.startswith('^') and value.endswith('$'):
            self._re_match = re.compile(value).match
        elif '*' in value:
            value = re.escape(value).replace('\\*', r'.*')
            self._re_match = re.compile(r'^(?:%s)$' % value).match

    def match(self, other):
        try:
            _other_val = other._raw_value
        except AttributeError:
            _other_val = text_type(other)

        if self._re_match:
            return self._re_match(_other_val)
        else:
            return self._raw_value == _other_val

    def __str__(self):
        return self._raw_value

    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__, self._raw_value)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self._raw_value == other._raw_value

    def __hash__(self):
        return hash(self._raw_value)

    @property
    def exact_value(self):
        return self._raw_value if self._re_match is None else None

    @property
    def matches_all(self):
        return self._raw_value == '*'

    def merge(self, other):
        if self.raw_value != other.raw_value:
            raise ValueError("Incompatible component merge:\n  - %r\n  - %r"
                             % (self.raw_value, other.raw_value))
        return self.raw_value


class ChannelMatch(StrMatch):

    def __init__(self, value):
        self._re_match = None

        if isinstance(value, string_types):
            if value.startswith('^') and value.endswith('$'):
                self._re_match = re.compile(value).match
            elif '*' in value:
                self._re_match = re.compile(r'^(?:%s)$' % value.replace('*', r'.*')).match
            else:
                value = Channel(value)

        super(StrMatch, self).__init__(value)  # lgtm [py/super-not-enclosing-class]

    def match(self, other):
        try:
            _other_val = Channel(other._raw_value)
        except AttributeError:
            _other_val = Channel(other)

        if self._re_match:
            return self._re_match(_other_val.canonical_name)
        else:
            # assert ChannelMatch('pkgs/free').match('defaults') is False
            # assert ChannelMatch('defaults').match('pkgs/free') is True
            return (self._raw_value.name == _other_val.name
                    or self._raw_value.name == _other_val.canonical_name)

    def __str__(self):
        try:
            return "%s" % self._raw_value.name
        except AttributeError:
            return "%s" % self._raw_value

    def __repr__(self):
        return "'%s'" % self.__str__()

    def merge(self, other):
        if self.raw_value != other.raw_value:
            raise ValueError("Incompatible component merge:\n  - %r\n  - %r"
                             % (self.raw_value, other.raw_value))
        return self.raw_value


class LowerStrMatch(StrMatch):

    def __init__(self, value):
        super(LowerStrMatch, self).__init__(value.lower())


class CaseInsensitiveStrMatch(LowerStrMatch):

    def match(self, other):
        try:
            _other_val = other._raw_value
        except AttributeError:
            _other_val = text_type(other)

        _other_val = _other_val.lower()
        if self._re_match:
            return self._re_match(_other_val)
        else:
            return self._raw_value == _other_val


_implementors = {
    'channel': ChannelMatch,
    'namespace': LowerStrMatch,
    'name': LowerStrMatch,
    'version': VersionSpec,
    'build_number': BuildNumberMatch,
    'track_features': FeatureMatch,
    'features': FeatureMatch,
    'license': CaseInsensitiveStrMatch,
    'license_family': CaseInsensitiveStrMatch,
}
