# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from ast import literal_eval
import re
import sys

from conda.base.constants import CONDA_TARBALL_EXTENSION

from .dist import Dist
from .index_record import IndexRecord
from .version import VersionSpec
from .._vendor.auxlib.collection import frozendict
from ..common.compat import iteritems, string_types, text_type
from ..exceptions import CondaValueError


class SplitSearch(object):
    """Implements matching on features or track_features. These strings are actually
       split by whitespace into sets. We want a string match to be True if it matches
       any of the elements of this set. However, we also want this to be considered an
       "exact" match for the purposes of the rest of MatchSpec logic, even though it is
       possible that there are multiple entries in the set, and only one is matching."""
    __slots__ = ['exact', 'match']

    def __init__(self, value):
        self.exact = value  # ensures this is considered an exact match
        self.match = re.compile(r'(?:^|.* )%s(?:$| )' % value).match

    def __repr__(self):
        return "'%s'" % self.exact


_implementors = {
    'features': SplitSearch,
    'track_features': SplitSearch,
    'version': VersionSpec
}


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

    def __new__(cls, *specs, **kwargs):
        # only 0 or 1 specs arguments are allowed
        len_specs = len(specs)
        if len_specs > 1:
            raise CondaValueError("Only one spec argument can be provided.\n%r" % specs)
        elif len_specs == 1:
            spec = specs[0]
        else:
            spec = None

        # memoize spec objects without additional kwargs
        if not kwargs and isinstance(spec, cls):
            return spec

        normalize = kwargs.pop('normalize', False)
        self = object.__new__(cls)
        _specs_map = {}

        if isinstance(spec, string_types):
            spec, _, oparts = spec.partition('(')
            parts = [spec] if spec.endswith(CONDA_TARBALL_EXTENSION) else spec.split()
            assert 1 <= len(parts) <= 3, repr(spec)
            name, version, build = (parts + ['*', '*'])[:3]
            self._push(_specs_map,
                       ('name', name),
                       ('version', version),
                       ('build', build))

            def _exact_field(field_name):
                # duplicated self.exact_field(), but for the local _specs_map
                v = _specs_map.get(field_name)
                return getattr(v, 'exact', None if hasattr(v, 'match') else v)

            if normalize and _exact_field('build') is None:
                if _exact_field('name') is not None and _exact_field('version') is not None:
                    # When someone supplies 'foo=a.b' on the command line, we
                    # want to append an asterisk; e.g., 'foo=a.b.*', but only
                    # if there is not also an exact build and name. In that
                    # case we assume the user is looking for an exact match.
                    ver = _exact_field('version')
                    _specs_map['version'] = VersionSpec(ver + '*')
            if oparts:
                if oparts.strip()[-1] != ')':
                    raise CondaValueError("Invalid MatchSpec: %s" % spec)
                for opart in oparts.strip()[:-1].split(','):
                    field, eq, value = (x.strip() for x in opart.partition('='))
                    if not field:
                        continue
                    elif not value and (eq or field != 'optional'):
                        raise CondaValueError("Invalid MatchSpec: %s" % spec)
                    elif field == 'optional':
                        kwargs.setdefault('optional', bool(value) if eq else True)
                        if bool(_exact_field('name')) + bool(_exact_field('track_features')) != 1:
                            raise CondaValueError("Optional MatchSpec must be tied"
                                                  " to a name or track_feature (and not both): %s"
                                                  "" % spec)
                    elif field == 'target':
                        kwargs.setdefault('target', value)
                    else:
                        self._push(_specs_map, (field, literal_eval(value)))
        elif spec is None:
            pass
        elif isinstance(spec, cls):
            kwargs.setdefault('optional', spec.optional)
            if spec.target:
                kwargs.setdefault('target', spec.target)
            _specs_map.update(spec._specs_map)

        elif isinstance(spec, dict):
            # kwargs take priority
            for k, v in iteritems(spec):
                kwargs.setdefault(k, v)

        elif isinstance(spec, Dist):
            self._push(_specs_map,
                       ('fn', spec.to_filename()),
                       ('schannel', spec.channel))

        elif isinstance(spec, IndexRecord):
            self._push(_specs_map,
                       ('name', spec.name),
                       ('fn', spec.fn),
                       ('schannel', spec.schannel))

        else:
            raise CondaValueError("Cannot construct MatchSpec from: %r" % (spec,))

        _target = kwargs.pop('target', None)
        _optional = bool(kwargs.pop('optional', False))
        self._push(_specs_map, *iteritems(kwargs))

        # assign attributes to self
        self._specs_map = frozendict(_specs_map)
        self.target = _target
        self.optional = _optional
        return self

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

            if isinstance(value, VersionSpec) and value.is_exact():
                value = value.spec

            specs_map[field_name] = value

    def exact_field(self, field_name):
        v = self._specs_map.get(field_name)
        return getattr(v, 'exact', None if hasattr(v, 'match') else v)

    def is_exact(self):
        return all(self.exact_field(x) is not None for x in ('fn', 'schannel'))

    def is_simple(self):
        return len(self._specs_map) == 1 and self.exact_field('name') is not None

    def is_single(self):
        return len(self._specs_map) == 1

    def match(self, rec):
        """
        Accepts an `IndexRecord` or a dict, and matches can pull from any field
        in that record.  Returns True for a match, and False for no match.
        """
        for f, v in iteritems(self._specs_map):
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

    def to_dict(self, args=True):
        # arg=True adds 'optional' and 'target' fields to the dict
        res = self._specs_map.copy()
        if args and self.optional:
            res['optional'] = bool(self.optional)
        if args and self.target is not None:
            res['target'] = self.target
        return res

    def _to_string(self, args=True, base=True):
        # arg=True adds 'optional' and 'target' fields to the dict
        nf = (3 if 'build' in self._specs_map else
              (2 if 'version' in self._specs_map else 1)) if base else 0
        flds = ('name', 'version', 'build')[:nf]
        base = ' '.join(str(self._specs_map.get(f, '*')) for f in flds)
        xtra = ['%s=%r' % (f, v) for f, v in sorted(iteritems(self._specs_map))
                if f not in flds]
        if args and self.optional:
            xtra.append('optional' if base else 'optional=True')
        if args and self.target:
            xtra.append('target=' + self.target)
        xtra = ','.join(xtra)
        if not base:
            return xtra
        elif xtra:
            return '%s (%s)' % (base, xtra)
        else:
            return base

    def _eq_key(self):
        return self._specs_map, self.optional, self.target

    def __eq__(self, other):
        return isinstance(other, MatchSpec) and self._eq_key() == other._eq_key()

    def __hash__(self):
        return hash(self._specs_map)

    if sys.version_info[0] == 2:
        def __ne__(self, other):
            equal = self.__eq__(other)
            return equal if equal is NotImplemented else not equal

    def __repr__(self):
        return "MatchSpec(%s)" % (self._to_string(args=True, base=False),)

    def __contains__(self, field):
        return field in self._specs_map

    def __str__(self):
        return self._to_string(args=True, base=True)

    # Needed for back compatibility with conda-build and even some code
    # within conda itself. Do not remove without coordination with the
    # conda-build team

    @property
    def strictness(self):
        # With the old MatchSpec, strictness==3 if name, version, and
        # build were all specified. We've extended that to include any
        # spec that deviates from the old name/version/build spec:
        # additional fields, wildcard name matching, etc.
        if sum(f in self._specs_map for f in ('name', 'version', 'build')) < len(self._specs_map):
            return 3
        elif not self.exact_field('name') or 'build' in self._specs_map:
            return 3
        elif 'version' in self._specs_map:
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
        return self._specs_map.get('version')
