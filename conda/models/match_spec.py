# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from abc import ABCMeta, abstractmethod, abstractproperty
from collections import Mapping
import re

from .channel import Channel
from .dist import Dist
from .index_record import IndexRecord
from .version import BuildNumberMatch, VersionSpec
from .._vendor.auxlib.collection import frozendict
from ..base.constants import CONDA_TARBALL_EXTENSION
from ..common.compat import isiterable, iteritems, string_types, text_type, with_metaclass
from ..common.path import expand
from ..common.url import is_url, path_to_url
from ..exceptions import CondaValueError

try:
    from cytoolz.functoolz import excepts
except ImportError:  # pragma: no cover
    from .._vendor.toolz.functoolz import excepts


class MatchSpecType(type):

    def __call__(cls, spec_arg=None, **kwargs):
        if spec_arg:
            if isinstance(spec_arg, MatchSpec) and not kwargs:
                return spec_arg
            elif isinstance(spec_arg, MatchSpec):
                kwargs.setdefault('optional', spec_arg.optional)
                kwargs.setdefault('target', spec_arg.target)
                kwargs.update(spec_arg._match_components)
                return super(MatchSpecType, cls).__call__(**kwargs)
            elif isinstance(spec_arg, string_types):
                parsed = _parse_spec_str(spec_arg)
                parsed.update(kwargs)
                return super(MatchSpecType, cls).__call__(**parsed)
            elif isinstance(spec_arg, Mapping):
                parsed = dict(spec_arg, **kwargs)
                return super(MatchSpecType, cls).__call__(**parsed)
            elif isinstance(spec_arg, Dist):
                # TODO: remove this branch
                parsed = {
                    'fn': spec_arg.to_filename(),
                    'channel': spec_arg.channel,
                }
                return super(MatchSpecType, cls).__call__(**parsed)
            elif isinstance(spec_arg, IndexRecord):
                # TODO: remove this branch
                parsed = {
                    'name': spec_arg.name,
                    'fn': spec_arg.fn,
                    'channel': spec_arg.channel,
                }
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
    The easiest way to build `MatchSpec` objects that match to arbitrary fields is to
    use a keyword syntax.  For instance,

        MatchSpec(name='foo', build='py2*', channel='conda-forge')

    matches any package named `foo` built with a Python 2 build string in the
    `conda-forge` channel.  Available keywords to be matched against are fields of
    the `IndexRecord` model object.

    Strings are interpreted using the following conventions:
      - If the string begins with `^` and ends with `$`, it is converted to a regex.
      - For the `version` field, non-regex strings are processed by `VersionSpec`.
      - If the string contains an asterisk (`*`), it is transformed from a glob to a regex.
      - Otherwise, an exact match to the string is sought.

    The `.match()` method accepts an `IndexRecord` or dictionary, and matches can pull
    from any field in that record.

    For now, non-string fields (e.g., `build_number`) allow only exact matches.
    However, fully custom matching on a single field is possible simply by feeding
    in an object with a `match` method (which, conveniently, includes regexes and
    `VersionSpec` objects). There is no way to match on a combination of fields in
    a single function, and the tests are combined using logical `and`.

    Great pain has been taken to preserve back-compatibility with the standard
    `name version build` syntax. But strictly speaking it is not necessary. Now, the
    following are all equivalent:
      - `MatchSpec('foo 1.0 py27_0 (optional)')`
      - `MatchSpec("* (name='foo',version='1.0',build='py27_0')", optional=True)`
      - `MatchSpec("foo (version='1.0',optional,build='py27_0')")`
      - `MatchSpec(name='foo', optional=True, version='1.0', build='py27_0')`

    """

    FIELD_NAMES = (
        'channel',
        'subdir',
        'name',
        'version',
        'build',
        'build_number',
        'track_features',
        'md5',
    )

    def __init__(self, optional=False, target=None, **kwargs):
        self.optional = optional
        self.target = target
        self._match_components = self._build_components(**kwargs)

    def exact_field(self, field_name):
        v = self._match_components.get(field_name)
        return v and v.exact_value

    def _is_simple(self):
        return len(self._match_components) == 1 and self.exact_field('name') is not None

    def _is_single(self):
        return len(self._match_components) == 1

    def match(self, rec):
        """
        Accepts an `IndexRecord` or a dict, and matches can pull from any field
        in that record.  Returns True for a match, and False for no match.
        """
        for f, v in iteritems(self._match_components):
            val = getattr(rec, f)
            if not (v.match(val) if hasattr(v, 'match') else v == val):
                return False
        return True

    def _to_filename_do_not_use(self):
        # WARNING: this is potentially unreliable and use should probably be limited
        #   returns None if a filename can't be constructed
        fn_field = self.exact_field('fn')
        if fn_field:
            return fn_field
        vals = tuple(self.exact_field(x) for x in ('name', 'version', 'build'))
        if not any(x is None for x in vals):
            return '%s-%s-%s.tar.bz2' % vals
        else:
            return None

    def __repr__(self):
        builder = []
        builder += ["%s=%r" % (c, self._match_components[c]) for c in self.FIELD_NAMES if c in self._match_components]
        if self.optional:
            builder.append("optional=True")
        if self.target:
            builder.append("target=%r" % self.target)
        return "%s(%s)" % (self.__class__.__name__, ', '.join(builder))

    def __str__(self):
        builder = []

        channel_matcher = self._match_components.get('channel')
        if channel_matcher:
            builder.append(text_type(channel_matcher) + "::")

        builder.append(text_type(self._match_components.get('name', '*')))

        xtra = []

        version = self._match_components.get('version')
        if version:
            version = text_type(version)
            if any(s in version for s in '><$^|,'):
                xtra.append("version='%s'" % version)
            elif version.endswith('.*'):
                builder.append('=' + version[:-2])
            elif version.endswith('*'):
                builder.append('=' + version[:-1])
            else:
                builder.append('==' + version)

        _skip = ('channel', 'name', 'version')
        for key in self.FIELD_NAMES:
            if key not in _skip and key in self._match_components:
                value = text_type(self._match_components[key])
                if any(s in value for s in ', '):
                    xtra.append("%s='%s'" % (key, self._match_components[key]))
                else:
                    xtra.append("%s=%s" % (key, self._match_components[key]))

        if xtra:
            builder.append('[%s]' % ','.join(xtra))

        return ''.join(builder)

    def __eq__(self, other):
        if isinstance(other, MatchSpec):
            self_key = self._match_components, self.optional, self.target
            other_key = other._match_components, other.optional, other.target
            return self_key == other_key
        else:
            return False

    def __hash__(self):
        return hash(self._match_components)

    def __contains__(self, field):
        return field in self._match_components

    @staticmethod
    def _build_components(**kwargs):
        def _make(field_name, value):
            if field_name not in IndexRecord.__fields__:
                raise CondaValueError('Cannot match on field %s' % (field_name,))
            elif isinstance(value, string_types):
                value = text_type(value)

            if hasattr(value, 'match'):
                matcher = value
            elif field_name in _implementors:
                matcher = _implementors[field_name](value)
            elif text_type(value):
                matcher = StrMatch(value)
            else:
                raise NotImplementedError()

            if field_name == 'version':
                value = VersionSpec(value)
                if value.is_exact():
                    value = value.spec
            # elif field_name == "build":
            #     if isinstance(value, string_types) and '_' in value:
            #         bn = text_type(value).rsplit('_', 1)[-1]
            #         build_number = BuildNumberMatch(bn)
            #         if build_number.is_exact():
            #             build_number = build_number.spec
            #         specs_map["build_number"] = build_number

            return matcher

        return frozendict((key, _make(key, value)) for key, value in iteritems(kwargs))

    #
    # Methods for back compatibility with conda-build. Do not remove
    # without coordination with the conda-build team.
    #

    @property
    def strictness(self):
        # With the old MatchSpec, strictness==3 if name, version, and
        # build were all specified.
        s = sum(f in self._match_components for f in ('name', 'version', 'build'))
        if s < len(self._match_components):
            return 3
        elif not self.exact_field('name') or 'build' in self._match_components:
            return 3
        elif 'version' in self._match_components:
            return 2
        else:
            return 1

    @property
    def spec(self):
        return self.__str__()

    @property
    def name(self):
        return self.exact_field('name') or '*'

    @property
    def version(self):
        # in the old MatchSpec object, version was a VersionSpec, not a str
        # so we'll keep that API here
        return self._match_components.get('version')


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


def _parse_spec_str(spec_str):
    # Step 1. strip '#' comment
    if '#' in spec_str:
        ndx = spec_str.index('#')
        spec_str, _ = spec_str[:ndx], spec_str[ndx:]
        spec_str.strip()

    # Step 2. done if spec_str is a tarball
    if spec_str.endswith(CONDA_TARBALL_EXTENSION):
        # treat as a normal url
        if not is_url(spec_str):
            spec_str = path_to_url(expand(spec_str))

        from .channel import Channel
        channel = Channel(spec_str)
        name, version, build = _parse_legacy_dist(channel.package_filename)
        return {
            'channel': channel.canonical_name,
            'subdir': channel.subdir,
            'name': name,
            'version': version,
            'build': build,
        }

    # Step 3. strip off brackets portion
    m1 = re.match(r'^(.*)(\[.*\])$', spec_str)
    if m1:
        spec_str, brackets = m1.groups()
        brackets = brackets[1:-1]
    else:
        brackets = None

    # Step 4. strip off '::' channel and namespace
    m2 = spec_str.rsplit(':', 2)
    m2_len = len(m2)
    if m2_len == 3:
        channel, namespace, spec_str = m2
    elif m2_len == 2:
        namespace, spec_str = m2
        channel = None
    elif m2_len:
        spec_str = m2[0]
        channel, namespace = None, None
    else:
        raise NotImplementedError()

    # Step 5. strip off package name from remaining version + build
    m3 = re.match(r'([^ =<>!]+)?([><!= ].+)?', spec_str)
    if m3:
        name, spec_str = m3.groups()
        if name is None:
            raise CondaValueError("Invalid MatchSpec: %s" % spec_str)
    else:
        raise CondaValueError("Invalid MatchSpec: %s" % spec_str)

    # Step 6. sort out version + build
    spec_str = spec_str and spec_str.strip()
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

    # Step 7. now compile components together
    components = {}
    components['name'] = name if name else '*'
    if channel is not None:
        from .channel import Channel, MultiChannel
        chn = Channel(channel)
        if isinstance(chn, MultiChannel):
            components['channel'] = chn.name
        else:
            components['channel'] = chn.canonical_name
    if namespace is not None:
        # kwargs['namespace'] = namespace
        pass

    if version is not None:
        components['version'] = version
    if build is not None:
        components['build'] = build

    # now parse brackets
    # anything in brackets will strictly override key as set in other area of spec str
    if brackets:
        brackets = brackets.strip("[]\n\r\t ")
        m5 = re.finditer(r'([a-zA-Z0-9_-]+?)=(["\']?)([^\'"]*?)(\2)(?:[, ]|$)', brackets)
        for match in m5:
            key, _, value, _ = match.groups()
            if not key or not value:
                raise CondaValueError("Invalid MatchSpec: %s" % spec_str)
            components[key] = value

    return components


@with_metaclass(ABCMeta)
class MatchInterface(object):
    
    def __init__(self, value):
        self._raw_value = value

    @abstractmethod
    def match(self, other):
        raise NotImplementedError

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


class SplitStrMatch(MatchInterface):
    __slots__ = '_raw_value',

    def __init__(self, value):
        super(SplitStrMatch, self).__init__(self._convert(value))

    def _convert(self, value):
        try:
            return frozenset(value.split())
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
        if len(self._raw_value) > 1:
            return "'%s'" % ','.join(sorted(self._raw_value))
        else:
            return "%s" % next(iter(self._raw_value))

    def __eq__(self, other):
        return self.match(other)

    def __hash__(self):
        return hash(self._raw_value)

    @property
    def exact_value(self):
        return self._raw_value



class ChannelMatch(MatchInterface):
    __slots__ = '_raw_value',

    def __init__(self, value):
        super(ChannelMatch, self).__init__(Channel(value))

    def match(self, other):
        try:
            return self._raw_value.canonical_name == other._raw_value.canonical_name
        except AttributeError:
            return self._raw_value.canonical_name == Channel(other).canonical_name

    def __str__(self):
        return "%s" % self._raw_value.canonical_name

    def __repr__(self):
        return "'%s'" % self._raw_value.canonical_name

    def __eq__(self, other):
        return self.match(other)

    def __hash__(self):
        return hash(self._raw_value)

    @property
    def exact_value(self):
        return self._raw_value


class StrMatch(MatchInterface):
    __slots__ = '_raw_value', '_re_match'

    def __init__(self, value):
        super(StrMatch, self).__init__(value)
        self._re_match = None

        if value.startswith('^') and value.endswith('$'):
            self._re_match = re.compile(value).match
        elif '*' in value:
            self._re_match = re.compile(r'^(?:%s)$' % value.replace('*', r'.*')).match

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
        return self.match(other)

    def __hash__(self):
        return hash(self._raw_value)

    @property
    def exact_value(self):
        return self._raw_value if self._re_match is None else None



_implementors = {
    'features': SplitStrMatch,
    'track_features': SplitStrMatch,
    'version': VersionSpec,
    'build_number': BuildNumberMatch,
    'channel': ChannelMatch,
}
