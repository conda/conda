# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import Mapping
import re
import sys

from .channel import Channel
from .dist import Dist
from .index_record import IndexRecord
from .version import BuildNumberSpec, VersionSpec
from .._vendor.auxlib.collection import frozendict
from ..base.constants import CONDA_TARBALL_EXTENSION
from ..common.compat import iteritems, string_types, text_type, with_metaclass, isiterable
from ..common.path import expand
from ..common.url import is_url, path_to_url
from ..exceptions import CondaValueError


# class SplitSearch(object):
#     """Implements matching on features or track_features. These strings are actually
#        split by whitespace into sets. We want a string match to be True if it matches
#        any of the elements of this set. However, we also want this to be considered an
#        "exact" match for the purposes of the rest of MatchSpec logic, even though it is
#        possible that there are multiple entries in the set, and only one is matching."""
#     __slots__ = ('exact', 'match')
#
#     def __init__(self, value):
#         self.exact = value  # ensures this is considered an exact match
#         self.match = re.compile(r'(?:^|.* )%s(?:$| )' % value).match
#
#     def __repr__(self):
#         return "'%s'" % self.exact

class SplitStrSpec(object):
    __slots__ = 'exact',

    def __init__(self, value):
        self.exact = self._convert(value)  # ensures this is considered an exact match

    def _convert(self, value):
        try:
            return frozenset(value.split())
        except AttributeError:
            if isiterable(value):
                return frozenset(value)
            raise

    def match(self, other):
        try:
            return other and self.exact & other.exact
        except AttributeError:
            return self.exact & self._convert(other)

    def __repr__(self):
        if len(self.exact) > 1:
            return "'%s'" % ','.join(sorted(self.exact))
        else:
            return "%s" % next(iter(self.exact))

    def __eq__(self, other):
        return self.match(other)

    def __hash__(self):
        return hash(self.exact)


class ChannelSpec(object):
    __slots__ = 'exact',

    def __init__(self, value):
        self.exact = Channel(value)  # ensures this is considered an exact match

    def match(self, other):
        try:
            return self.exact.canonical_name == other.exact.canonical_name
        except AttributeError:
            return self.exact.canonical_name == Channel(other).canonical_name

    def __repr__(self):
        return "'%s'" % self.exact.canonical_name

    def __eq__(self, other):
        return self.match(other)

    def __hash__(self):
        return hash(self.exact)


_implementors = {
    'features': SplitStrSpec,
    'track_features': SplitStrSpec,
    'version': VersionSpec,
    'build_number': BuildNumberSpec,
    'channel': ChannelSpec,
}


class MatchSpecType(type):

    def __call__(cls, spec_arg=None, **kwargs):
        if spec_arg:
            if isinstance(spec_arg, MatchSpec) and not kwargs:
                return spec_arg
            elif isinstance(spec_arg, MatchSpec):
                kwargs.setdefault('optional', spec_arg.optional)
                kwargs.setdefault('target', spec_arg.target)
                kwargs.update(spec_arg._components)
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

    def __init__(self, optional=False, target=None, **kwargs):
        self.optional = optional
        self.target = target
        _components = {}
        self._push(_components, *tuple(iteritems(kwargs)))
        self._components = frozendict(_components)

        # def __new__(cls, *specs, **kwargs):
    #     # only 0 or 1 specs arguments are allowed
    #     len_specs = len(specs)
    #     if len_specs > 1:
    #         raise CondaValueError("Only one spec argument can be provided.\n%r" % specs)
    #     elif len_specs == 1:
    #         spec = specs[0]
    #     else:
    #         spec = None
    #
    #     # memoize spec objects without additional kwargs
    #     if not kwargs and isinstance(spec, cls):
    #         return spec
    #
    #     normalize = kwargs.pop('normalize', False)
    #     self = object.__new__(cls)
    #     _components = {}
    #
    #     if isinstance(spec, string_types):
    #         spec, _, oparts = spec.partition('(')
    #         parts = [spec] if spec.endswith(CONDA_TARBALL_EXTENSION) else spec.split()
    #         assert 1 <= len(parts) <= 3, repr(spec)
    #         name, version, build = (parts + ['*', '*'])[:3]
    #         self._push(_components,
    #                    ('name', name),
    #                    ('version', version),
    #                    ('build', build))
    #
    #         def _exact_field(field_name):
    #             # duplicated self.exact_field(), but for the local _components
    #             v = _components.get(field_name)
    #             return getattr(v, 'exact', None if hasattr(v, 'match') else v)
    #
    #         if normalize and _exact_field('build') is None:
    #             if _exact_field('name') is not None and _exact_field('version') is not None:
    #                 # When someone supplies 'foo=a.b' on the command line, we
    #                 # want to append an asterisk; e.g., 'foo=a.b.*', but only
    #                 # if there is not also an exact build and name. In that
    #                 # case we assume the user is looking for an exact match.
    #                 ver = _exact_field('version')
    #                 _components['version'] = VersionSpec(ver + '*')
    #         if oparts:
    #             if oparts.strip()[-1] != ')':
    #                 raise CondaValueError("Invalid MatchSpec: %s" % spec)
    #             for opart in oparts.strip()[:-1].split(','):
    #                 field, eq, value = (x.strip() for x in opart.partition('='))
    #                 if not field:
    #                     continue
    #                 elif not value and (eq or field != 'optional'):
    #                     raise CondaValueError("Invalid MatchSpec: %s" % spec)
    #                 elif field == 'optional':
    #                     kwargs.setdefault('optional', bool(value) if eq else True)
    #                     if bool(_exact_field('name')) + bool(_exact_field('track_features')) != 1:  # NOQA
    #                         raise CondaValueError("Optional MatchSpec must be tied"
    #                                               " to a name or track_feature (and not both): %s"  # NOQA
    #                                               "" % spec)
    #                 elif field == 'target':
    #                     kwargs.setdefault('target', value)
    #                 else:
    #                     self._push(_components, (field, literal_eval(value)))
    #     elif spec is None:
    #         pass
    #     elif isinstance(spec, cls):
    #         kwargs.setdefault('optional', spec.optional)
    #         if spec.target:
    #             kwargs.setdefault('target', spec.target)
    #         _components.update(spec._components)
    #
    #     elif isinstance(spec, dict):
    #         # kwargs take priority
    #         for k, v in iteritems(spec):
    #             kwargs.setdefault(k, v)
    #
    #     elif isinstance(spec, Dist):
    #         self._push(_components,
    #                    ('fn', spec.to_filename()),
    #                    ('schannel', spec.channel))
    #
    #     elif isinstance(spec, IndexRecord):
    #         self._push(_components,
    #                    ('name', spec.name),
    #                    ('fn', spec.fn),
    #                    ('schannel', spec.schannel))
    #
    #     else:
    #         raise CondaValueError("Cannot construct MatchSpec from: %r" % (spec,))
    #
    #     _target = kwargs.pop('target', None)
    #     _optional = bool(kwargs.pop('optional', False))
    #     self._push(_components, *iteritems(kwargs))
    #
    #     # assign attributes to self
    #     self._components = frozendict(_components)
    #     self.target = _target
    #     self.optional = _optional
    #     return self

    @staticmethod
    def _push(specs_map, *args):
        # format each (field_name, value) arg pair, and add it to specs_map
        for field_name, value in args:
            if value in ('*', None):
                if field_name in specs_map:
                    del specs_map[field_name]
                continue
            elif field_name not in IndexRecord.__fields__:
                raise CondaValueError('Cannot match on field %s' % (field_name,))
            elif isinstance(value, string_types):
                value = text_type(value)

            if hasattr(value, 'match'):
                pass
            elif field_name in _implementors:
                value = _implementors[field_name](value)
            elif not isinstance(value, string_types):
                pass
            elif value.startswith('^') and value.endswith('$'):
                value = re.compile(value)
            elif '*' in value:
                value = re.compile(r'^(?:%s)$' % value.replace('*', r'.*'))

            if field_name == 'version':
                value = VersionSpec(value)
                if value.is_exact():
                    value = value.spec
            elif field_name == "build":
                if isinstance(value, string_types) and '_' in value:
                    bn = text_type(value).rsplit('_', 1)[-1]
                    build_number = BuildNumberSpec(bn)
                    if build_number.is_exact():
                        build_number = build_number.spec
                    specs_map["build_number"] = build_number

            specs_map[field_name] = value

    def exact_field(self, field_name):
        v = self._components.get(field_name)
        return getattr(v, 'exact', None if hasattr(v, 'match') else v)

    def is_exact(self):
        return all(self.exact_field(x) is not None for x in ('fn', 'channel'))

    def is_simple(self):
        return len(self._components) == 1 and self.exact_field('name') is not None

    def is_single(self):
        return len(self._components) == 1

    def match(self, rec):
        """
        Accepts an `IndexRecord` or a dict, and matches can pull from any field
        in that record.  Returns True for a match, and False for no match.
        """
        for f, v in iteritems(self._components):
            val = getattr(rec, f)
            if not (v.match(val) if hasattr(v, 'match') else v == val):
                return False
        return True

    def to_filename(self):
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

    # def to_dict(self, args=True):
    #     # arg=True adds 'optional' and 'target' fields to the dict
    #     res = self._components.copy()
    #     if args and self.optional:
    #         res['optional'] = bool(self.optional)
    #     if args and self.target is not None:
    #         res['target'] = self.target
    #     return res

    def _to_string(self, args=True, base=True):
        # arg=True adds 'optional' and 'target' fields to the dict
        nf = (3 if 'build' in self._components else
              (2 if 'version' in self._components else 1)) if base else 0
        flds = ('name', 'version', 'build')[:nf]
        base = ' '.join(str(self._components.get(f, '*')) for f in flds)
        xtra = ['%s=%r' % (f, v) for f, v in sorted(iteritems(self._components))
                if f not in flds]
        # if args and self.optional:
        #     xtra.append('optional' if base else 'optional=True')
        # if args and self.target:
        #     xtra.append('target=' + self.target)
        xtra = ','.join(xtra)
        if not base:
            return xtra
        elif xtra:
            return '%s[%s]' % (base, xtra)
        else:
            return base

    def _to_str(self):
        builder = []
        order = (
            # 'channel',
            # 'subdir',
            # 'version',
            'build',
            'build_number',
            'track_features',
            'md5',
        )

        channel = self._components.get('channel')
        if channel:
            builder.append(channel.exact.canonical_name + "::")

        builder.append(self._components.get('name', '*'))

        xtra = []

        version = self._components.get('version')
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
                # xtra.append("version=%s" % version)

        for key in order:
            if key in self._components:
                xtra.append("%s=%s" % (key, self._components[key]))

        if xtra:
            builder.append('[%s]' % ','.join(xtra))

        return ''.join(builder)



        # version_type = 'complex'
        # version = self._components.get('version')
        # if version:
        #     version = text_type(version)
        #     if not any(s in version for s in '|,$^'):
        #         version_type = 'simple'
        #         if version.endswith('.*'):
        #             version = '=' + version[:-2]
        #         elif version.endswith('*'):
        #             version = '=' + version[:-1]
        #         else:
        #             version = version
        #
        # if version_type == 'simple':
        #     return "%s%s" % (name, version)
        # else:
        #     return "%s[version='%s']" % (name, version)

    def __str__(self):
        return self._to_str()






    def _eq_key(self):
        return self._components, self.optional, self.target

    def __eq__(self, other):
        return isinstance(other, MatchSpec) and self._eq_key() == other._eq_key()

    def __hash__(self):
        return hash(self._components)

    if sys.version_info[0] == 2:
        def __ne__(self, other):
            equal = self.__eq__(other)
            return equal if equal is NotImplemented else not equal

    def __repr__(self):
        return "MatchSpec(%s)" % (self._to_string(args=True, base=False),)

    def __contains__(self, field):
        return field in self._components

    # def __str__(self):
    #     return self._to_string(args=True, base=True)

    # Needed for back compatibility with conda-build. Do not remove
    # without coordination with the conda-build team.

    @property
    def strictness(self):
        # With the old MatchSpec, strictness==3 if name, version, and
        # build were all specified.
        s = sum(f in self._components for f in ('name', 'version', 'build'))
        if s < len(self._components):
            return 3
        elif not self.exact_field('name') or 'build' in self._components:
            return 3
        elif 'version' in self._components:
            return 2
        else:
            return 1

    @property
    def spec(self):
        return self._to_string(args=False, base=True)

    @property
    def name(self):
        return self.exact_field('name') or '*'

    @property
    def version(self):
        # in the old MatchSpec object, version was a VersionSpec, not a str
        # so we'll keep that API here
        return self._components.get('version')


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
