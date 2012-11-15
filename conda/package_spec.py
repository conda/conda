''' The package_spec module contains the package_spec class, and utility functions for manipulating sets of package specifications.

'''


from distutils.version import LooseVersion

from naming import split_spec_string
from verlib import NormalizedVersion, suggest_normalized_version


class package_spec(object):
    '''
    Encapsulates a package name and version (or partial version) along with an optional build string for
    use as a package specification.

    Parameters
    ----------
    spec_string : str
        a string containing a package name and version and (optional) build string, separated by a spaces or by '='


    Attributes
    ----------
    build : str
    name : str
    version : LooseVersion

    Examples
    --------
    >>> spec = package_spec("python 2.7")
    >>> spec.name
    'python'
    >>> spec.version
    LooseVersion('2.7')

    '''

    __slots__ = ['__name', '__version', '__build']

    def __init__(self, spec_string):
        components = split_spec_string(spec_string)
        self.__name = components[0]
        self.__version = LooseVersion(components[1])
        self.__build = None
        if len(components) == 3:
            self.__build = components[2]

    @property
    def name(self):
        ''' package name

        '''
        return self.__name

    @property
    def version(self):
        ''' package version or partial version

        '''
        return self.__version

    @property
    def build(self):
        ''' package build string (or None)

        '''
        return self.__build

    def __str__(self):
        if self.build:
            return 'spec[%s %s %s]' % (self.name, self.version.vstring, self.build)
        else:
            return 'spec[%s %s]' % (self.name, self.version.vstring)

    def __repr__(self):
        if self.build:
            return "package_spec('%s %s %s')" % (self.name, self.version.vstring, self.build)
        else:
            return "package_spec('%s %s')" % (self.name, self.version.vstring)

    def __hash__(self):
        return hash((self.name, self.version.vstring, self.build))

    def __cmp__(self, other):
        # NormalizedVersion seems to not work perfectly if 'rc' is adjacent to the last version digit
        sv = self.version.vstring.replace('rc', '.rc')
        ov = other.version.vstring.replace('rc', '.rc')
        try:
            return cmp(
                (self.name, NormalizedVersion(suggest_normalized_version(sv)), self.build),
                (other.name, NormalizedVersion(suggest_normalized_version(ov)), other.build)
            )
        except:
            return cmp(
                (self.name, self.version.vstring, self.build),
                (other.name, other.version.vstring, other.build)
            )


def find_inconsistent_specs(specs):
    ''' Iterates over a set of package specifications, finding those that share a name
    but have a different version

    Parameters
    ----------
    specs : iterable collection of :py:class:`package_spec <conda.package_spec.package_spec>` objects
        package specifications to check for inconsistencies

    Returns
    -------
    inconsistent_specs : set of :py:class:`package_spec <conda.package_spec.package_spec>` objects
        all inconsistent package specifications present in `specs`

    Examples
    --------
    >>> r,s,t = package_spec('python 2.7'), package_spec('python 3.1'), package_spec('numpy 1.2.3')
    >>> specs = [r,s,t]
    >>> find_inconsistent_specs(specs)
    set([package_spec('python 3.1'), package_spec('python 2.7')])

    '''

    results = set()

    tmp = {}
    for spec in specs:
        if spec.name not in tmp:
            tmp[spec.name] = set()
        tmp[spec.name].add((tuple(spec.version.version), spec))

    for name, tup in tmp.items():
        versions = [t[0] for t in tup]
        reqs = set([t[1] for t in tup])
        if len(versions) < 2: continue
        vlen = min(len(v) for v in versions)
        for v1 in versions:
            for v2 in versions:
                if v1[:vlen] != v2[:vlen]: results = results | reqs

    return results


def apply_default_spec(specs, default_spec):
    '''
    Examines a collection of package specifications and adds default_spec to it, if no
    other package specification for the same package specified by default_spec is already present.

    Parameters
    ----------
    specs : set of :py:class:`package_spec <conda.package_spec.package_spec>` objects
        package specifications to apply defaults to
    default_spec : :py:class:`package_spec <conda.package_spec.package_spec>` object
        default package specification to apply to `specs`

    Returns
    -------
    updated_specs : set of :py:class:`package_spec <conda.package_spec.package_spec>` objects
        `specs` with `default_sepc` applied, if necessary

    '''

    needs_default = True
    for spec in specs:
        if spec.name == default_spec.name:
            needs_default = False
            break
    if needs_default: specs.add(default_spec)





