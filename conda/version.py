from __future__ import print_function, division, absolute_import

import operator as op
import re

from conda.compat import zip_longest, string_types, zip

# normalized_version() is needed by conda-env
# It is currently being pulled from resolve instead, but
# eventually it ought to come from here
def normalized_version(version):
    return VersionOrder(version)

def ver_eval(vtest, spec):
    return VersionSpec(spec).match(vtest)

version_check_re = re.compile(r'^[\*\.\+!_0-9a-z]+$')
version_split_re = re.compile('([0-9]+|[^0-9]+)')
class VersionOrder(object):
    '''
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
    '''
    def __init__(self, version):
        # when fillvalue ==  0  =>  1.1 == 1.1.0
        # when fillvalue == -1  =>  1.1  < 1.1.0
        self.fillvalue = 0

        message = "Malformed version string '%s': " % version
        # version comparison is case-insensitive
        version = version.strip().rstrip().lower()
        # basic validity checks
        if version == '':
            raise ValueError("Empty version string.")
        invalid = not version_check_re.match(version)
        if invalid and '-' in version and '_' not in version:
            # Allow for dashes as long as there are no underscores
            # as well, by converting the former to the latter.
            version = version.replace('-', '_')
            invalid = not version_check_re.match(version)
        if invalid:
            raise ValueError(message + "invalid character(s).")
        self.norm_version = version

        # find epoch
        version = version.split('!')
        if len(version) == 1:
            # epoch not given => set it to '0'
            epoch = ['0']
        elif len(version) == 2:
            # epoch given, must be an integer
            if not version[0].isdigit():
                raise ValueError(message + "epoch must be an integer.")
            epoch = [version[0]]
        else:
            raise ValueError(message + "duplicated epoch separator '!'.")

        # find local version string
        version = version[-1].split('+')
        if len(version) == 1:
            # no local version
            self.local = ['0']
        elif len(version) == 2:
            # local version given
            self.local = version[1].replace('_', '.').split('.')
        else:
            raise ValueError(message + "duplicated local version separator '+'.")

        # split version
        self.version = epoch + version[0].replace('_', '.').split('.')

        # split components into runs of numerals and non-numerals,
        # convert numerals to int, handle special strings
        for v in (self.version, self.local):
            for k in range(len(v)):
                c = version_split_re.findall(v[k])
                if not c:
                    raise ValueError(message + "empty version component.")
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

    def __str__(self):
        return self.norm_version

    def __eq__(self, other):
        for t1, t2 in zip([self.version, self.local], [other.version, other.local]):
            for v1, v2 in zip_longest(t1, t2, fillvalue=[self.fillvalue]):
                for c1, c2 in zip_longest(v1, v2, fillvalue=self.fillvalue):
                    if c1 != c2:
                        return False
        return True

    def __ne__(self, other):
        return not (self == other)

    def __lt__(self, other):
        for t1, t2 in zip([self.version, self.local], [other.version, other.local]):
            for v1, v2 in zip_longest(t1, t2, fillvalue=[self.fillvalue]):
                for c1, c2 in zip_longest(v1, v2, fillvalue=self.fillvalue):
                    if isinstance(c1, string_types):
                        if not isinstance(c2, string_types):
                            # str < int
                            return True
                    else:
                        if isinstance(c2, string_types):
                            # not (int < str)
                            return False
                    # c1 and c2 have the same type
                    if c1 < c2:
                        return True
                    if c2 < c1:
                        return False
                    # c1 == c2 => advance
        # self == other
        return False

    def __gt__(self, other):
        return other < self

    def __le__(self, other):
        return not (other < self)

    def __ge__(self, other):
        return not (self < other)


# This RE matches the operators '==', '!=', '<=', '>=', '<', '>'
# followed by a version string. It rejects expressions like
# '<= 1.2' (space after operator), '<>1.2' (unknown operator),
# and '<=!1.2' (nonsensical operator).
version_relation_re = re.compile(r'(==|!=|<=|>=|<|>)(?![=<>!])(\S+)$')
opdict = {'==': op.__eq__, '!=': op.__ne__, '<=': op.__le__,
          '>=': op.__ge__, '<': op.__lt__, '>': op.__gt__}

class VersionSpec(object):
    def regex_match_(self, vspec):
        return bool(self.regex.match(vspec))

    def veval_match_(self, vspec):
        return self.op(VersionOrder(vspec), self.cmp)

    def all_match_(self, vspec):
        return all(s.match(vspec) for s in self.spec[1])

    def any_match_(self, vspec):
        return any(s.match(vspec) for s in self.spec[1])

    def __new__(cls, spec):
        if isinstance(spec, cls):
            return spec
        self = object.__new__(cls)
        self.spec = spec
        if isinstance(spec, tuple):
            self.match = self.all_match_ if spec[0] == 'all' else self.any_match_
        elif '|' in spec:
            return VersionSpec(('any', tuple(VersionSpec(s) for s in spec.split('|'))))
        elif ',' in spec:
            return VersionSpec(('all', tuple(VersionSpec(s) for s in spec.split(','))))
        elif spec.startswith(('=', '<', '>', '!')):
            m = version_relation_re.match(spec)
            if m is None:
                raise RuntimeError('Invalid version spec: %s' % spec)
            op, b = m.groups()
            self.op = opdict[op]
            self.cmp = VersionOrder(b)
            self.match = self.veval_match_
        else:
            self.spec = spec
            rx = spec.replace('.', r'\.')
            rx = rx.replace('+', r'\+')
            rx = rx.replace('*', r'.*')
            rx = r'(%s)$' % rx
            self.regex = re.compile(rx)
            self.match = self.regex_match_
        return self

    def str(self, inand=False):
        s = self.spec
        if isinstance(s, tuple):
            newand = not inand and s[0] == all
            inand = inand and s[0] == any
            s = (',' if s[0] == 'all' else '|').join(x.str(newand) for x in s[1])
            if inand:
                s = '(%s)' % s
        return s

    def __str__(self):
        return self.str()

    def __repr__(self):
        return "VersionSpec('%s')" % self.str()

    def __and__(self, other):
        if not isinstance(other, VersionSpec):
            other = VersionSpec(other)
        return VersionSpec((all, (self, other)))

    def __or__(self, other):
        if not isinstance(other, VersionSpec):
            other = VersionSpec(other)
        return VersionSpec((any, (self, other)))
