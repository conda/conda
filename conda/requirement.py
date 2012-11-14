''' The requirements module contains the requirement class, and utility functions for manipulating sets of requirements.

'''


from distutils.version import LooseVersion

from naming import split_req_string
from verlib import NormalizedVersion, suggest_normalized_version


class requirement(object):
    '''
    Encapsulates a package name and version (or partial version) along with an optional build string for
    use as a package specification.

    Parameters
    ----------
    req_string : str
        a string containing a package name and version and (optional) build string, separated by a spaces or by '='


    Attributes
    ----------
    build : str
    name : str
    version : LooseVersion

    Examples
    --------
    >>> r = requirement("python 2.7")
    >>> r.name
    'python'
    >>> r.version
    LooseVersion('2.7')

    '''

    __slots__ = ['__name', '__version', '__build']

    def __init__(self, req_string):
        components = split_req_string(req_string)
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
            return 'req[%s %s %s]' % (self.name, self.version.vstring, self.build)
        else:
            return 'req[%s %s]' % (self.name, self.version.vstring)

    def __repr__(self):
        if self.build:
            return "requirement('%s %s %s')" % (self.name, self.version.vstring, self.build)
        else:
            return "requirement('%s %s')" % (self.name, self.version.vstring)

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


def find_inconsistent_requirements(reqs):
    '''
    Iterates over a set of requirements, finding those that share a name but have a different version

    Parameters
    ----------
    reqs : iterable collection of :py:class:`requirement <conda.requirement.requirement>` objects
        requirements to check for inconsistencies

    Returns
    -------
    inconsistent_reqs : set of :py:class:`requirement <conda.requirement.requirement>` objects
        all inconsistent requirements present in `reqs`

    Examples
    --------
    >>> r,s,t = requirement('python 2.7'), requirement('python 3.1'), requirement('numpy 1.2.3')
    >>> reqs = [r,s,t]
    >>> find_inconsistent_requirements(reqs)
    set([requirement('python 3.1'), requirement('python 2.7')])

    '''

    results = set()

    tmp = {}
    for req in reqs:
        if req.name not in tmp:
            tmp[req.name] = set()
        tmp[req.name].add((tuple(req.version.version), req))

    for name, tup in tmp.items():
        versions = [t[0] for t in tup]
        reqs = set([t[1] for t in tup])
        if len(versions) < 2: continue
        vlen = min(len(v) for v in versions)
        for v1 in versions:
            for v2 in versions:
                if v1[:vlen] != v2[:vlen]: results = results | reqs

    return results


def apply_default_requirement(reqs, default_req):
    '''
    Examines a collection of requirements and adds default_req to it, if no
    other requirement for the same package specified by default_req is already present.

    Parameters
    ----------
    reqs : set of :py:class:`requirement <conda.requirement.requirement>` objects
        requirements to apply defaults to
    default_req : :py:class:`requirement <conda.requirement.requirement>` object
        default requirement to apply

    Returns
    -------
    updated_reqs : set of :py:class:`requirement <conda.requirement.requirement>` objects
        `reqs` with `default_req` applied, if necessary

    '''

    needs_default = True
    for req in reqs:
        if req.name == default_req.name:
            needs_default = False
            break
    if needs_default: reqs.add(default_req)





