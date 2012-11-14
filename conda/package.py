''' The package module provides the `package` class, which encapsulates information about an Anaconda package,
as well as utility functions for manipulating collections of packages.

'''

from distutils.version import LooseVersion

from requirement import requirement
from verlib import NormalizedVersion, suggest_normalized_version


__all__ = ['package', 'sort_packages_by_version', 'sort_packages_by_name']


def dict_property(name, doc):
    property
    def prop(self):
        return self._info[name]
    return property(fget=prop, doc=doc)


class package(object):
    ''' The package class encapsulates information about an Anaconda package

    Attributes
    ----------
    build
    build_number
    build_target
    canonical_name
    filename
    is_meta
    location
    md5
    name
    requires
    size
    version

    '''

    __slots__ = ['_filename', '_info', '_version', '_requires', '_build_target']

    def __init__(self, pkg_info):
        self._info = pkg_info
        self._filename = '%s-%s-%s.tar.bz2' % (self._info['name'],
                                               self._info['version'],
                                               self._info['build'])
        self._version = LooseVersion(self._info['version'])
        self._requires = set(requirement(req_string)
                             for req_string in self._info['requires'])
        self._build_target = self._info.get('build_target', None)

    name         = dict_property('name', ':ref:`Package name <package_name>` of this package')
    build        = dict_property('build', ':ref:`Build string <build_string>` of this package')
    build_number = dict_property('build_number', 'build number for this package')
    md5          = dict_property('md5', 'md5 hash of package file')
    size         = dict_property('size', 'package file size in bytes')

    @property
    def build_target(self):
        ''' Build target for this package (if it has one)

        The possible values are:
            ``ce``
                package works with Community Edition
            ``pro``
                package works with Anaconda Pro
            None
                package works with any build target

        '''
        return self._build_target

    @property
    def version(self):
        ''' :ref:`Package version <package_version>` of this package '''
        return self._version

    @property
    def requires(self):
        ''' Set of package requirements for this package '''
        return self._requires

    @property
    def canonical_name(self):
        ''' :ref:`Cannonical name <canonical_name>` of this package '''
        return "%s-%s-%s" % (self.name, self.version.vstring, self.build)

    @property
    def filename(self):
        ''' :ref:`Filename <filename>` of this Anaconda package '''
        return self._filename

    @property
    def location(self):
        ''' URL of the Anaconda :ref:`package repository <repository>` this package came from '''
        return self._info.get('location', 'unkown')

    @property
    def is_meta(self):
        ''' Whether or not this package is a meta package '''
        for req in self._requires:
            if req.build is None: return False
        return True

    def matches(self, constraint):
        return constraint.match(self)

    def print_info(self, show_requires=True):
        print "   package: %s-%s" % (self.name, self.version),
        print "[%s]" % self._build_target if self.build_target else ""
        print "  filename: %s" % self.filename
        print "       md5: %s" % self.md5
        if show_requires:
            print "  requires:"
            for req in sorted('%s-%s' % (r.name, r.version.vstring) for r in self.requires):
                print"        %s" % req

    def __str__(self):
        return '%s-%s' % (self.name, self.version.vstring)

    def __repr__(self):
        return 'package(%r)' % self._filename #TODO

    def __hash__(self):
        return hash(self._filename)

    def __cmp__(self, other):
        # NormalizedVersion seems to not work perfectly if 'rc' is adjacent to the last version digit
        sv = self.version.vstring.replace('rc', '.rc')
        ov = other.version.vstring.replace('rc', '.rc')
        try:
            return cmp(
                (self.name, NormalizedVersion(suggest_normalized_version(sv)), self.build_number),
                (other.name, NormalizedVersion(suggest_normalized_version(ov)), other.build_number)
            )
        except:
            return cmp(
                (self.name, self.version.vstring, self.build_number),
                (other.name, other.version.vstring, other.build_number)
            )


def sort_packages_by_version(pkgs, reverse=False):
    ''' sort a collection of packages by their :ref`package versions <package_version>`

    Parameters
    ----------
    pkgs : iterable
        a collection of packages
    reverse : bool, optional
        whether to sort in reverse order

    Returns
    -------
    sorted : list
        list of packages

    '''
    return sorted(
        list(pkgs),
        reverse=reverse,
        key=lambda pkg: pkg.version
    )

def sort_packages_by_name(pkgs, reverse=False):
    ''' sort a collection of packages by their :ref`package names <package_name>`

    Parameters
    ----------
    pkgs : iterable
        a collection of packages
    reverse : bool, optional
        whether to sort in reverse order

    Returns
    -------
    sorted : list
        list of packages

    '''
    return sorted(
        list(pkgs),
        reverse=reverse,
        key=lambda pkg: pkg.name
    )
