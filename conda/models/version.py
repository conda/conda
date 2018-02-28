# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals
from logging import getLogger
import operator as op
import re

from ..common.compat import string_types, zip, zip_longest, text_type
from ..exceptions import CondaValueError, InvalidVersionSpecError

try:
    from cytoolz.functoolz import excepts
except ImportError:  # pragma: no cover
    from .._vendor.toolz.functoolz import excepts

log = getLogger(__name__)

# normalized_version() is needed by conda-env
# It is currently being pulled from resolve instead, but
# eventually it ought to come from here
def normalized_version(version):
    return VersionOrder(version)


def ver_eval(vtest, spec):
    return VersionSpec(spec).match(vtest)


version_check_re = re.compile(r'^[\*\.\+!_0-9a-z]+$')
version_split_re = re.compile('([0-9]+|[*]+|[^0-9*]+)')
version_cache = {}


class VersionOrder(object):
    """
    This class implements an order relation between version strings.
    Version strings can contain the usual alphanumeric characters
    (A-Za-z0-9), separated into components by dots and underscores. Empty
    segments (i.e. two consecutive dots, a leading/trailing underscore)
    are not permitted. An optional epoch number - an integer
    followed by '!' - can preceed the actual version string
    (this is useful to indicate a change in the versioning
    scheme itself). Version comparison is case-insensitive.

    Conda supports six types of version strings:

    * Release versions contain only integers, e.g. '1.0', '2.3.5'.
    * Pre-release versions use additional letters such as 'a' or 'rc',
      for example '1.0a1', '1.2.beta3', '2.3.5rc3'.
    * Development versions are indicated by the string 'dev',
      for example '1.0dev42', '2.3.5.dev12'.
    * Post-release versions are indicated by the string 'post',
      for example '1.0post1', '2.3.5.post2'.
    * Tagged versions have a suffix that specifies a particular
      property of interest, e.g. '1.1.parallel'. Tags can be added
      to any of the preceding four types. As far as sorting is concerned,
      tags are treated like strings in pre-release versions.
    * An optional local version string separated by '+' can be appended
      to the main (upstream) version string. It is only considered
      in comparisons when the main versions are equal, but otherwise
      handled in exactly the same manner.

    To obtain a predictable version ordering, it is crucial to keep the
    version number scheme of a given package consistent over time.
    Specifically,

    * version strings should always have the same number of components
      (except for an optional tag suffix or local version string),
    * letters/strings indicating non-release versions should always
      occur at the same position.

    Before comparison, version strings are parsed as follows:

    * They are first split into epoch, version number, and local version
      number at '!' and '+' respectively. If there is no '!', the epoch is
      set to 0. If there is no '+', the local version is empty.
    * The version part is then split into components at '.' and '_'.
    * Each component is split again into runs of numerals and non-numerals
    * Subcomponents containing only numerals are converted to integers.
    * Strings are converted to lower case, with special treatment for 'dev'
      and 'post'.
    * When a component starts with a letter, the fillvalue 0 is inserted
      to keep numbers and strings in phase, resulting in '1.1.a1' == 1.1.0a1'.
    * The same is repeated for the local version part.

    Examples:

        1.2g.beta15.rc  =>  [[0], [1], [2, 'g'], [0, 'beta', 15], [0, 'rc']]
        1!2.15.1_ALPHA  =>  [[1], [2], [15], [1, '_alpha']]

    The resulting lists are compared lexicographically, where the following
    rules are applied to each pair of corresponding subcomponents:

    * integers are compared numerically
    * strings are compared lexicographically, case-insensitive
    * strings are smaller than integers, except
    * 'dev' versions are smaller than all corresponding versions of other types
    * 'post' versions are greater than all corresponding versions of other types
    * if a subcomponent has no correspondent, the missing correspondent is
      treated as integer 0 to ensure '1.1' == '1.1.0'.

    The resulting order is:

           0.4
         < 0.4.0
         < 0.4.1.rc
        == 0.4.1.RC   # case-insensitive comparison
         < 0.4.1
         < 0.5a1
         < 0.5b3
         < 0.5C1      # case-insensitive comparison
         < 0.5
         < 0.9.6
         < 0.960923
         < 1.0
         < 1.1dev1    # special case 'dev'
         < 1.1a1
         < 1.1.0dev1  # special case 'dev'
        == 1.1.dev1   # 0 is inserted before string
         < 1.1.a1
         < 1.1.0rc1
         < 1.1.0
        == 1.1
         < 1.1.0post1 # special case 'post'
        == 1.1.post1  # 0 is inserted before string
         < 1.1post1   # special case 'post'
         < 1996.07.12
         < 1!0.4.1    # epoch increased
         < 1!3.1.1.6
         < 2!0.4.1    # epoch increased again

    Some packages (most notably openssl) have incompatible version conventions.
    In particular, openssl interprets letters as version counters rather than
    pre-release identifiers. For openssl, the relation

      1.0.1 < 1.0.1a   =>   True   # for openssl

    holds, whereas conda packages use the opposite ordering. You can work-around
    this problem by appending a dash to plain version numbers:

      1.0.1a  =>  1.0.1post.a      # ensure correct ordering for openssl
    """

    def __new__(cls, vstr):
        if isinstance(vstr, cls):
            return vstr
        self = version_cache.get(vstr)
        if self is not None:
            return self

        message = "Malformed version string '%s': " % vstr
        # version comparison is case-insensitive
        version = vstr.strip().rstrip().lower()
        # basic validity checks
        if version == '':
            raise CondaValueError("Empty version string.")
        invalid = not version_check_re.match(version)
        if invalid and '-' in version and '_' not in version:
            # Allow for dashes as long as there are no underscores
            # as well, by converting the former to the latter.
            version = version.replace('-', '_')
            invalid = not version_check_re.match(version)
        if invalid:
            raise CondaValueError(message + "invalid character(s).")
        self = version_cache.get(version)
        if self is not None:
            version_cache[vstr] = self
            return self

        # when fillvalue ==  0  =>  1.1 == 1.1.0
        # when fillvalue == -1  =>  1.1  < 1.1.0
        self = version_cache[vstr] = version_cache[version] = object.__new__(cls)
        self.norm_version = version
        self.fillvalue = 0

        # find epoch
        version = version.split('!')
        if len(version) == 1:
            # epoch not given => set it to '0'
            epoch = ['0']
        elif len(version) == 2:
            # epoch given, must be an integer
            if not version[0].isdigit():
                raise CondaValueError(message + "epoch must be an integer.")
            epoch = [version[0]]
        else:
            raise CondaValueError(message + "duplicated epoch separator '!'.")

        # find local version string
        version = version[-1].split('+')
        if len(version) == 1:
            # no local version
            self.local = []
        elif len(version) == 2:
            # local version given
            self.local = version[1].replace('_', '.').split('.')
        else:
            raise CondaValueError(message + "duplicated local version separator '+'.")

        # split version
        self.version = epoch + version[0].replace('_', '.').split('.')

        # split components into runs of numerals and non-numerals,
        # convert numerals to int, handle special strings
        for v in (self.version, self.local):
            for k in range(len(v)):
                c = version_split_re.findall(v[k])
                if not c:
                    raise CondaValueError(message + "empty version component.")
                for j in range(len(c)):
                    if c[j].isdigit():
                        c[j] = int(c[j])
                    elif c[j] == 'post':
                        # ensure number < 'post' == infinity
                        c[j] = float('inf')
                    elif c[j] == 'dev':
                        # ensure '*' < 'DEV' < '_' < 'a' < number
                        # by upper-casing (all other strings are lower case)
                        c[j] = 'DEV'
                if v[k][0].isdigit():
                    v[k] = c
                else:
                    # components shall start with a number to keep numbers and
                    # strings in phase => prepend fillvalue
                    v[k] = [self.fillvalue] + c

        return self

    def __str__(self):
        return self.norm_version

    def _eq(self, t1, t2):
        for v1, v2 in zip_longest(t1, t2, fillvalue=[]):
            for c1, c2 in zip_longest(v1, v2, fillvalue=self.fillvalue):
                if c1 != c2:
                    return False
        return True

    def __eq__(self, other):
        return (self._eq(self.version, other.version) and
                self._eq(self.local, other.local))

    def startswith(self, other):
        # Tests if the version lists match up to the last element in "other".
        if other.local:
            if not self._eq(self.version, other.version):
                return False
            t1 = self.local
            t2 = other.local
        else:
            t1 = self.version
            t2 = other.version
        nt = len(t2) - 1
        if not self._eq(t1[:nt], t2[:nt]):
            return False
        v1 = [] if len(t1) <= nt else t1[nt]
        v2 = t2[nt]
        nt = len(v2) - 1
        if not self._eq([v1[:nt]], [v2[:nt]]):
            return False
        c1 = self.fillvalue if len(v1) <= nt else v1[nt]
        c2 = v2[nt]
        if isinstance(c2, string_types):
            return isinstance(c1, string_types) and c1.startswith(c2)
        return c1 == c2

    def __ne__(self, other):
        return not (self == other)

    def __lt__(self, other):
        for t1, t2 in zip([self.version, self.local], [other.version, other.local]):
            for v1, v2 in zip_longest(t1, t2, fillvalue=[]):
                for c1, c2 in zip_longest(v1, v2, fillvalue=self.fillvalue):
                    if c1 == c2:
                        continue
                    elif isinstance(c1, string_types):
                        if not isinstance(c2, string_types):
                            # str < int
                            return True
                    elif isinstance(c2, string_types):
                            # not (int < str)
                            return False
                    # c1 and c2 have the same type
                    return c1 < c2
        # self == other
        return False

    def __gt__(self, other):
        return other < self

    def __le__(self, other):
        return not (other < self)

    def __ge__(self, other):
        return not (self < other)


# each token slurps up leading whitespace, which we strip out.
VSPEC_TOKENS = (r'\s*\^[^$]*[$]|'  # regexes
                r'\s*[()|,]|'      # parentheses, logical and, logical or
                r'[^()|,]+')       # everything else


def treeify(spec_str):
    """
    Examples:
        >>> treeify("1.2.3")
        '1.2.3'
        >>> treeify("1.2.3,>4.5.6")
        (',', '1.2.3', '>4.5.6')
        >>> treeify("1.2.3,4.5.6|<=7.8.9")
        ('|', (',', '1.2.3', '4.5.6'), '<=7.8.9')
        >>> treeify("(1.2.3|4.5.6),<=7.8.9")
        (',', ('|', '1.2.3', '4.5.6'), '<=7.8.9')
        >>> treeify("((1.5|((1.6|1.7), 1.8), 1.9 |2.0))|2.1")
        ('|', '1.5', (',', ('|', '1.6', '1.7'), '1.8', '1.9'), '2.0', '2.1')
        >>> treeify("1.5|(1.6|1.7),1.8,1.9|2.0|2.1")
        ('|', '1.5', (',', ('|', '1.6', '1.7'), '1.8', '1.9'), '2.0', '2.1')
    """
    # Converts a VersionSpec expression string into a tuple-based
    # expression tree.
    assert isinstance(spec_str, string_types)
    tokens = re.findall(VSPEC_TOKENS, '(%s)' % spec_str)
    output = []
    stack = []

    def apply_ops(cstop):
        # cstop: operators with lower precedence
        while stack and stack[-1] not in cstop:
            if len(output) < 2:
                raise InvalidVersionSpecError(spec_str)
            c = stack.pop()
            r = output.pop()
            # Fuse expressions with the same operator; e.g.,
            #   ('|', ('|', a, b), ('|', c, d))becomes
            #   ('|', a, b, c d)
            # We're playing a bit of a trick here. Instead of checking
            # if the left or right entries are tuples, we're counting
            # on the fact that if we _do_ see a string instead, its
            # first character cannot possibly be equal to the operator.
            r = r[1:] if r[0] == c else (r,)
            left = output.pop()
            left = left[1:] if left[0] == c else (left,)
            output.append((c,)+left+r)

    for item in tokens:
        item = item.strip()
        if item == '|':
            apply_ops('(')
            stack.append('|')
        elif item == ',':
            apply_ops('|(')
            stack.append(',')
        elif item == '(':
            stack.append('(')
        elif item == ')':
            apply_ops('(')
            if not stack or stack[-1] != '(':
                raise InvalidVersionSpecError(spec_str)
            stack.pop()
        else:
            output.append(item)
    if stack:
        raise InvalidVersionSpecError(spec_str)
    return output[0]


def untreeify(spec, _inand=False):
    """
    Examples:
        >>> untreeify('1.2.3')
        '1.2.3'
        >>> untreeify((',', '1.2.3', '>4.5.6'))
        '1.2.3,>4.5.6'
        >>> untreeify(('|', (',', '1.2.3', '4.5.6'), '<=7.8.9'))
        '1.2.3,4.5.6|<=7.8.9'
        >>> untreeify((',', ('|', '1.2.3', '4.5.6'), '<=7.8.9'))
        '(1.2.3|4.5.6),<=7.8.9'
        >>> untreeify(('|', '1.5', (',', ('|', '1.6', '1.7'), '1.8', '1.9'), '2.0', '2.1'))
        '1.5|(1.6|1.7),1.8,1.9|2.0|2.1'
    """
    if isinstance(spec, tuple):
        if spec[0] == '|':
            res = '|'.join(map(untreeify, spec[1:]))
            if _inand:
                res = '(%s)' % res
        else:
            res = ','.join(map(lambda x: untreeify(x, _inand=True), spec[1:]))
        return res
    return spec


# This RE matches the operators '==', '!=', '<=', '>=', '<', '>'
# followed by a version string. It rejects expressions like
# '<= 1.2' (space after operator), '<>1.2' (unknown operator),
# and '<=!1.2' (nonsensical operator).
version_relation_re = re.compile(r'(==|!=|<=|>=|<|>)(?![=<>!])(\S+)$')
regex_split_re = re.compile(r'.*[()|,^$]')
opdict = {'==': op.__eq__, '!=': op.__ne__, '<=': op.__le__,
          '>=': op.__ge__, '<': op.__lt__, '>': op.__gt__}


class VersionSpec(object):
    def exact_match_(self, vspec):
        return self.spec == vspec

    def regex_match_(self, vspec):
        return bool(self.regex.match(vspec))

    def veval_match_(self, vspec):
        return self.op(VersionOrder(vspec), self.cmp)

    def all_match_(self, vspec):
        return all(s.match(vspec) for s in self.tup)

    def any_match_(self, vspec):
        return any(s.match(vspec) for s in self.tup)

    def triv_match_(self, vspec):
        return True

    def __new__(cls, spec):
        if isinstance(spec, cls):
            return spec
        if isinstance(spec, string_types) and regex_split_re.match(spec):
            spec = treeify(spec)

        self = object.__new__(cls)
        if isinstance(spec, tuple):
            self.tup = tup = tuple(VersionSpec(s) for s in spec[1:])
            self.match = self.any_match_ if spec[0] == '|' else self.all_match_
            self.spec = untreeify((spec[0],) + tuple(t.spec for t in tup))
            self.depth = 2
            return self

        self.depth = 0
        self.spec = spec = text_type(spec).strip()
        if spec.startswith('^') or spec.endswith('$'):
            if not spec.startswith('^') or not spec.endswith('$'):
                raise InvalidVersionSpecError(spec)
            self.regex = re.compile(spec)
            self.match = self.regex_match_
        elif spec.startswith(('=', '<', '>', '!')):
            m = version_relation_re.match(spec)
            if m is None:
                raise InvalidVersionSpecError(spec)
            op, b = m.groups()
            self.op = opdict[op]
            self.cmp = VersionOrder(b)
            self.match = self.veval_match_
        elif spec == '*':
            self.match = self.triv_match_
        elif '*' in spec.rstrip('*'):
            self.spec = spec
            rx = spec.replace('.', r'\.')
            rx = rx.replace('+', r'\+')
            rx = rx.replace('*', r'.*')
            rx = r'^(?:%s)$' % rx
            self.regex = re.compile(rx)
            self.match = self.regex_match_
        elif spec.endswith('*'):
            if not spec.endswith('.*'):
                self.spec = spec = spec[:-1] + '.*'
            self.op = VersionOrder.startswith
            self.cmp = VersionOrder(spec.rstrip('*').rstrip('.'))
            self.match = self.veval_match_
        elif '@' not in spec:
            self.op = opdict["=="]
            self.cmp = VersionOrder(spec)
            self.match = self.veval_match_
        else:
            self.match = self.exact_match_
        return self

    def is_exact(self):
        return (self.match == self.exact_match_
                or self.match == self.veval_match_ and self.op == op.__eq__)

    def __eq__(self, other):
        try:
            other = VersionSpec(other)
            return self.spec == other.spec
        except Exception as e:
            log.debug('%r', e)
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.spec)

    def __str__(self):
        return self.spec

    def __repr__(self):
        return "VersionSpec('%s')" % self.spec

    @property
    def raw_value(self):
        return self.spec

    @property
    def exact_value(self):
        return self.is_exact() and self.spec or None

    def merge(self, other):
        assert isinstance(other, self.__class__)
        return self.__class__('%s,%s' % (self.raw_value, other.raw_value))


class BuildNumberMatch(object):

    def __new__(cls, spec):
        if isinstance(spec, cls):
            return spec

        self = object.__new__(cls)
        try:
            spec = int(spec)
        except ValueError:
            pass
        else:
            self.spec = spec
            self.match = self.exact_match_
            return self

        _spec = spec
        self.spec = spec = text_type(spec).strip()
        if spec == '*':
            self.match = self.triv_match_
        elif spec.startswith(('=', '<', '>', '!')):
            m = version_relation_re.match(spec)
            if m is None:
                raise InvalidVersionSpecError(spec)
            op, b = m.groups()
            self.op = opdict[op]
            self.cmp = VersionOrder(b)
            self.match = self.veval_match_
        elif spec.startswith('^') or spec.endswith('$'):
            if not spec.startswith('^') or not spec.endswith('$'):
                raise InvalidVersionSpecError(spec)
            self.regex = re.compile(spec)
            self.match = self.regex_match_
        elif hasattr(spec, 'match'):
            self.spec = _spec
            self.match = spec.match
        else:
            self.match = self.exact_match_
        return self

    def exact_match_(self, vspec):
        try:
            return int(self.spec) == int(vspec)
        except ValueError:
            return False

    def veval_match_(self, vspec):
        return self.op(VersionOrder(text_type(vspec)), self.cmp)

    def triv_match_(self, vspec):
        return True

    def regex_match_(self, vspec):
        return bool(self.regex.match(vspec))

    def is_exact(self):
        return self.match == self.exact_match_

    def __eq__(self, other):
        if isinstance(other, BuildNumberMatch):
            return self.spec == other.spec
        return False

    def __ne__(self, other):
        if isinstance(other, BuildNumberMatch):
            return self.spec != other.spec
        return True

    def __hash__(self):
        return hash(self.spec)

    def __str__(self):
        return text_type(self.spec)

    def __repr__(self):
        # return "BuildNumberSpec('%s')" % self.spec
        return text_type(self.spec)

    @property
    def raw_value(self):
        return self.spec

    @property
    def exact_value(self):
        return excepts(ValueError, int(self.raw_value))

    def merge(self, other):
        if self.raw_value != other.raw_value:
            raise ValueError("Incompatible component merge:\n  - %r\n  - %r"
                             % (self.raw_value, other.raw_value))
        return self.raw_value
