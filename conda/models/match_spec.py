# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from abc import ABCMeta, abstractmethod, abstractproperty
from collections import Mapping
import re

from .channel import Channel, MultiChannel
from .dist import Dist
from .index_record import IndexRecord
from .version import BuildNumberMatch, VersionSpec
from .._vendor.auxlib.collection import frozendict
from ..base.constants import CONDA_TARBALL_EXTENSION
from ..common.compat import isiterable, iteritems, string_types, text_type, with_metaclass
from ..common.path import expand
from ..common.url import is_url, path_to_url, unquote
from ..exceptions import CondaValueError

try:
    from cytoolz.itertoolz import concat
except ImportError:  # pragma: no cover
    from .._vendor.toolz.itertoolz import concat  # NOQA

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
      - If the string contains an asterisk (`*`), it is transformed from a glob to a regex.
      - Otherwise, an exact match to the string is sought.

    The `.match()` method accepts an `IndexRecord` or dictionary, and matches can pull
    from any field in that record.

    Great pain has been taken to preserve back-compatibility with the standard
    `name version build` syntax. But strictly speaking it is not necessary. Now, the
    following are all equivalent:
      - `MatchSpec('foo 1.0 py27_0', optional=True)`
      - `MatchSpec("* [name='foo',version='1.0',build='py27_0']", optional=True)`
      - `MatchSpec("foo[version='1.0',optional,build='py27_0']")`
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

    def get_exact_value(self, field_name):
        v = self._match_components.get(field_name)
        return v and v.exact_value

    def get_raw_value(self, field_name):
        v = self._match_components.get(field_name)
        return v and v.raw_value

    def _is_simple(self):
        return len(self._match_components) == 1 and self.get_exact_value('name') is not None

    def _is_single(self):
        return len(self._match_components) == 1

    def match(self, rec):
        """f
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

        channel_matcher = self._match_components.get('channel')
        if channel_matcher:
            builder.append(text_type(channel_matcher))

        subdir_matcher = self._match_components.get('subdir')
        if subdir_matcher:
            builder.append(('/%s' if builder else '*/%s') % subdir_matcher)

        name_matcher = self._match_components.get('name', '*')
        builder.append(('::%s' if builder else '%s') % name_matcher)

        xtra = []

        version_exact = False
        version = self._match_components.get('version')
        if version:
            version = text_type(version)
            if any(s in version for s in '><$^|,'):
                xtra.append("version='%s'" % version)
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
                xtra.append("build='%s'" % build)
            elif '*' in build:
                xtra.append("build=%s" % build)
            elif version_exact:
                builder.append('=' + build)
            else:
                xtra.append("build=%s" % build)

        _skip = ('channel', 'subdir', 'name', 'version', 'build')
        for key in self.FIELD_NAMES:
            if key not in _skip and key in self._match_components:
                value = text_type(self._match_components[key])
                if any(s in value for s in ', ='):
                    xtra.append("%s='%s'" % (key, self._match_components[key]))
                else:
                    xtra.append("%s=%s" % (key, self._match_components[key]))

        if xtra:
            builder.append('[%s]' % ','.join(xtra))

        return ''.join(builder)

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

            return matcher

        return frozendict((key, _make(key, value)) for key, value in iteritems(kwargs))

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
    channel_name = chn.name if isinstance(chn, MultiChannel) else chn.canonical_name
    return channel_name, chn.subdir


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
            spec_str = unquote(path_to_url(expand(spec_str)))

        channel = Channel(spec_str)
        if not channel.subdir:
            # url is not a channel
            raise CondaValueError("Invalid MatchSpec Channel: %s" % spec_str)
        name, version, build = _parse_legacy_dist(channel.package_filename)
        result = {
            'channel': channel.canonical_name,
            'subdir': channel.subdir,
            'name': name,
            'version': version,
            'build': build,
            'fn': channel.package_filename,
        }
        return result

    # Step 3. strip off brackets portion
    brackets = {}
    m1 = re.match(r'^(.*)(?:\[(.*)\])$', spec_str)
    if m1:
        spec_str, brackets_str = m1.groups()
        brackets_str = brackets_str.strip("[]\n\r\t ")

        m5 = re.finditer(r'([a-zA-Z0-9_-]+?)=(["\']?)([^\'"]*?)(\2)(?:[, ]|$)', brackets_str)
        for match in m5:
            key, _, value, _ = match.groups()
            if not key or not value:
                raise CondaValueError("Invalid MatchSpec: %s" % spec_str)
            brackets[key] = value

    # Step 4. strip off '::' channel and namespace
    m2 = spec_str.rsplit(':', 2)
    m2_len = len(m2)
    if m2_len == 3:
        channel_str, namespace, spec_str = m2
    elif m2_len == 2:
        namespace, spec_str = m2
        channel_str = None
    elif m2_len:
        spec_str = m2[0]
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

    # Step 5. strip off package name from remaining version + build
    m3 = re.match(r'([^ =<>!]+)?([><!= ].+)?', spec_str)
    if m3:
        name, spec_str = m3.groups()
        if name is None:
            raise CondaValueError("Invalid MatchSpec: %s" % spec_str)
    else:
        raise CondaValueError("Invalid MatchSpec: %s" % spec_str)

    # Step 6. otherwise sort out version + build
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

    # Step 7. now compile components together
    components = {}
    components['name'] = name if name else '*'

    if channel is not None:
        components['channel'] = channel
    if subdir is not None:
        components['subdir'] = subdir
    if namespace is not None:
        # components['namespace'] = namespace
        pass
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


class LowerStrMatch(StrMatch):

    def __init__(self, value):
        super(LowerStrMatch, self).__init__(value.lower())


_implementors = {
    'name': LowerStrMatch,
    'features': SplitStrMatch,
    'track_features': SplitStrMatch,
    'version': VersionSpec,
    'build_number': BuildNumberMatch,
    'channel': ChannelMatch,
}
