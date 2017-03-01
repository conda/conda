# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from ast import literal_eval
import re
import sys

from .dist import Dist
from .index_record import IndexRecord
from ..common.compat import iteritems, string_types, text_type
from ..exceptions import CondaValueError
from ..version import VersionSpec


class MatchSpec(object):
    """
    The easiest way to build `MatchSpec` objects that match to arbitrary fields is to
    use a keyword syntax.  For instance,

        MatchSpec(name='foo', build='py2*', channel='conda-forge')

    matches any package named `foo` built with a Python 2 build string in the
    `conda-forge` channel.

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
        if len(specs) == 1 and not kwargs and isinstance(specs[0], cls):
            return specs[0]
        normalize = kwargs.pop('normalize', False)
        self = object.__new__(cls)
        self.specs = {}

        def push_(*args):
            for field, value in args:
                if value in ('*', None):
                    if field in self.specs:
                        del self.specs[field]
                    continue
                elif field not in IndexRecord.__fields__:
                    raise CondaValueError('Cannot match on field %s' % (field,))
                elif isinstance(value, string_types):
                    value = text_type(value)
                if hasattr(value, 'match'):
                    pass
                elif not isinstance(value, string_types):
                    pass
                elif value.startswith('^') and value.endswith('$'):
                    value = re.compile(value)
                elif field == 'version':
                    value = VersionSpec(value)
                elif '*' in value:
                    value = re.compile(r'^(?:%s)$' % value.replace('*', r'.*'))
                if isinstance(value, VersionSpec) and value.is_exact():
                    value = value.spec
                self.specs[field] = value

        for spec in specs:
            if isinstance(spec, cls):
                kwargs.setdefault('optional', spec.optional)
                if spec.target:
                    kwargs.setdefault('target', spec.target)
                self.specs.update(spec.specs)

            elif isinstance(spec, dict):
                # kwargs take priority
                for k, v in iteritems(spec):
                    kwargs.setdefault(k, v)

            elif isinstance(spec, Dist):
                push_(('fn', spec.to_filename()),
                      ('schannel', spec.channel))

            elif isinstance(spec, IndexRecord):
                push_(('name', spec.name),
                      ('fn', spec.fn),
                      ('schannel', spec.schannel))

            elif isinstance(spec, string_types):
                spec, _, oparts = spec.partition('(')
                parts = spec.strip().split()
                assert 1 <= len(parts) <= 3, repr(spec)
                name, version, build = (parts + ['*', '*'])[:3]
                push_(('name', name), ('version', version), ('build', build))
                if normalize and (self.exact_field('version') is not None and
                                  self.exact_field('build') is None and
                                  self.exact_field('name') is not None):
                    # When someone supplies 'foo=a.b' on the command line, we
                    # want to append an asterisk; e.g., 'foo=a.b.*', but only
                    # if there is not also an exact build and name. In that
                    # case we assume the user is looking for an exact match.
                    ver = self.exact_field('version')
                    self.specs['version'] = VersionSpec(ver + '*')
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
                        elif field == 'target':
                            kwargs.setdefault('target', value)
                        else:
                            push_((field, literal_eval(value)))

            else:
                raise CondaValueError("Cannot construct MatchSpec from: %r" % (spec,))

        self.target = kwargs.pop('target', None)
        self.optional = bool(kwargs.pop('optional', False))
        push_(*iteritems(kwargs))
        return self

    def exact_field(self, fn):
        v = self.specs.get(fn)
        return None if v is None or hasattr(v, 'match') else v

    def is_exact(self):
        return all(self.exact_field(x) is not None for x in ('fn', 'schannel'))

    def is_simple(self):
        return len(self.specs) == 1 and self.exact_field('name') is not None

    def match(self, rec):
        """
        Accepts an `IndexRecord` or dictionary, and matches can pull from any field
        in that record.  Returns True for a match, and False for no match.
        """
        for f, v in iteritems(self.specs):
            val = getattr(rec, f)
            if not (v.match(val) if hasattr(v, 'match') else v == val):
                return False
        return True

    def to_filename(self):
        tmp = self.exact_field('fn')
        if tmp:
            return tmp
        vals = [self.exact_field(x) for x in ('name', 'version', 'build')]
        if not any(x is None for x in vals):
            return '%s-%s-%s.tar.bz2' % tuple(map(str, vals))

    def to_dict(self, args=True):
        res = self.specs.copy()
        if args and self.optional:
            res['optional'] = bool(self.optional)
        if args and self.target is not None:
            res['target'] = self.target
        return res

    def to_string(self, args=True, base=True):
        nf = (3 if 'build' in self.specs else
              (2 if 'version' in self.specs else 1)) if base else 0
        flds = ('name', 'version', 'build')[:nf]
        base = ' '.join(str(self.specs.get(f, '*')) for f in flds)
        xtra = ['%s=%r' % (f, v) for f, v in sorted(iteritems(self.specs))
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

    def __eq__(self, other):
        if isinstance(other, MatchSpec):
            return ((self.specs, self.optional, self.target) ==
                    (other.specs, other.optional, other.target))

    if sys.version_info[0] == 2:
        def __ne__(self, other):
            equal = self.__eq__(other)
            return equal if equal is NotImplemented else not equal

    def __repr__(self):
        return "MatchSpec(%s)" % (self.to_string(args=True, base=False),)

    def __str__(self):
        return self.to_string(args=True, base=True)

    # optional and target should not hash
    def __hash__(self):
        return hash(frozenset(iteritems(self.specs)))

    # Needed for back compatibility with conda-build and even some code
    # within conda itself. Do not remove without coordination with the
    # conda-build team

    @property
    def strictness(self):
        # With the old MatchSpec, strictness==3 if name, version, and
        # build were all specified. We've extended that to include any
        # spec that deviates from the old name/version/build spec:
        # additional fields, wildcard name matching, etc.
        if sum(f in self.specs for f in ('name', 'version', 'build')) < len(self.specs):
            return 3
        elif not self.exact_field('name') or 'build' in self.specs:
            return 3
        elif 'version' in self.specs:
            return 2
        else:
            return 1

    @property
    def name(self):
        return self.exact_field('name') or '*'

    @property
    def spec(self):
        return self.to_string(args=False, base=True)
