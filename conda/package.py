# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
''' The package module provides the `package` class, which encapsulates
information about an Anaconda package, as well as utility functions for
manipulating collections of packages.

'''

from distutils.version import LooseVersion
from itertools import combinations, groupby

from package_spec import make_package_spec
from verlib import NormalizedVersion, suggest_normalized_version


def dict_property(name, doc):
    property
    def prop(self):
        return self._info[name]
    return property(fget=prop, doc=doc)


class Package(object):
    ''' The package class encapsulates information about an Anaconda package

    Attributes
    ----------
    build
    build_channel
    build_number
    canonical_name
    features
    filename
    is_meta
    channel
    md5
    name
    options
    requires
    size
    track_features
    version

    '''

    __slots__ = ['_filename', '_info', '_version', '_requires']

    def __init__(self, pkg_info):
        self._info = pkg_info
        self._filename = '%s-%s-%s.tar.bz2' % (self._info['name'],
                                               self._info['version'],
                                               self._info['build'])
        self._version = LooseVersion(self._info['version'])
        self._requires = set(make_package_spec(spec_string)
                             for spec_string in self._info['requires'])

    name         = dict_property('name', ':ref:`Package name <package_name>` of this package')
    build        = dict_property('build', ':ref:`Build string <build_string>` of this package')
    build_number = dict_property('build_number', 'build number for this package')
    md5          = dict_property('md5', 'md5 hash of package file')
    size         = dict_property('size', 'package file size in bytes')

    @property
    def version(self):
        ''' :ref:`Package version <package_version>` of this package '''
        return self._version

    @property
    def features(self):
        ''' Set additional of features provided by this package '''
        return set(self._info.get('features', '').split())


    @property
    def requires(self):
        ''' Set of package specification requirements for this package '''
        return self._requires

    @property
    def track_features(self):
        ''' Set of features this package causes to be tracked in an environment'''
        return set(self._info.get('track_features', '').split())

    @property
    def canonical_name(self):
        ''' :ref:`Cannonical name <canonical_name>` of this package '''
        return "%s-%s-%s" % (self.name, self.version.vstring, self.build)

    @property
    def filename(self):
        ''' :ref:`Filename <filename>` of this Anaconda package '''
        return self._filename

    @property
    def build_channel(self):
        ''' optional string code representing the Anaconda :ref:`channel <channel>` this package came from '''
        return self._info.get('build_channel', '')

    @property
    def channel(self):
        ''' URL of the Anaconda :ref:`channel <channel>` this package came from '''
        return self._info.get('channel', 'unknown')

    @property
    def is_meta(self):
        ''' Whether or not this package is a meta package '''
        if len(self._requires) == 0: return False
        for spec in self._requires:
            if spec.build is None: return False
        return True

    def matches(self, constraint):
        return constraint.match(self)

    def print_info(self, show_requires=True):
        print "   package: %s-%s" % (self.name, self.version),
        print "  filename: %s" % self.filename
        try:
            print "       md5: %s" % self.md5
        except KeyError:
            pass
        if self.features:
            print "  provides: %s" % " ".join(self.features)
        if self.track_features:
            print "    tracks: %s" % " ".join(self.track_features)
        if show_requires:
            print "  requires:"
            for req in sorted(self.requires):
                spec_string = '%s-%s' % (req.name, req.version.vstring)
                print"        %s" % spec_string


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


def find_inconsistent_packages(pkgs):
    ''' Iterates over a set of packages, finding those that share a name but have inconsistent versions

    Parameters
    ----------
    pkgs : iterable collection of :py:class:`Package <conda.package.Package>` objects
        packages to check for inconsistencies

    Returns
    -------
    inconsistent_pkgs : set of :py:class:`Package <conda.package.Package>` objects
        all inconsistent packages present in `pkgs`

    '''

    inconsistent = dict()

    grouped = group_packages_by_name(pkgs)

    for name, pkgs in grouped.items():
        if len(pkgs) < 2: continue
        for s1, s2 in combinations(pkgs, 2):

            if not s1.version or not s2.version: continue

            v1, v2 = tuple(s1.version.version), tuple(s2.version.version)
            vlen = min(len(v1), len(v2))
            if v1[:vlen] != v2[:vlen]:
                inconsistent[name] = pkgs
                break

    return inconsistent


def sort_packages_by_name(pkgs, reverse=False):
    ''' sort a collection of packages by their :ref:`package names <package_name>`

    Parameters
    ----------
    pkgs : iterable of :py:class:`Package <conda.package.Package>`
        a collection of packages to sort by package name
    reverse : bool, optional
        whether to sort in reverse order

    Returns
    -------
    sorted : list of :py:class:`Package <conda.package.Package>`
        packages sorted by package name

    '''
    return sorted(
        list(pkgs),
        reverse=reverse,
        key=lambda pkg: pkg.name
    )

def group_packages_by_name(pkgs):
    ''' group a collection of packages by their :ref:`package names <package_name>`

    Parameters
    ----------
    pkgs : iterable of :py:class:`Package <conda.package.Package>`
        packages to group by package name

    Returns
    -------
    grouped : dict of (str, set of :py:class:`Package <conda.package.Package>`)
        dictionary of sets of packages, indexed by package name

    '''
    return dict((k, set(list(g))) for k,g in groupby(sort_packages_by_name(pkgs), key=lambda pkg: pkg.name))


def sort_packages_by_channel(pkgs, channels, reverse=False):
    ''' sort a collection of packages by their :ref:`channels <channel>`, given
    a specified channel ordering

    Parameters
    ----------
    pkgs : iterable of :py:class:`Package <conda.package.Package>`
        a collection of packages to sort by package name
    channels : list of str
        an list of channels used to order the packages
    reverse : bool, optional
        whether to sort in reverse order

    Returns
    -------
    sorted : list of :py:class:`Package <conda.package.Package>`
        packages sorted by channel

    '''
    return sorted(
        list(pkgs),
        reverse=reverse,
        key=lambda pkg: channels.index(pkg.channel)
    )

def group_packages_by_channel(pkgs, channels):
    ''' group a collection of packages by their :ref:`channel <channel>`, given
    a specified channel ordering

    Parameters
    ----------
    pkgs : iterable of :py:class:`Package <conda.package.Package>`
        packages to group by channel
    channels : list of str
        an list of channels used to order the packages

    Returns
    -------
    grouped : dict of (str, set of :py:class:`Package <conda.package.Package>`)
        dictionary of sets of packages, indexed by channel

    '''
    return dict((k, set(list(g))) for k,g in groupby(sort_packages_by_channel(pkgs, channels), key=lambda pkg: pkg.channel))


def newest_packages(pkgs):
    ''' from a collection of packages, return a set with only the newest version of each package

    Parameters
    ----------
    pkgs : iterable of :py:class:`Package <conda.package.Package>`
        packages to select newest versions from

    Returns
    -------
    newest : set of :py:class:`Package <conda.package.Package>`
        newest packages for each package in `pkgs`

    '''
    grouped = group_packages_by_name(pkgs)

    return set(max(pkgs) for pkgs in grouped.values())


def channel_select(pkgs, channels):
    ''' from a collection of packages, return a set that come only form the first
    channel with matches

    Parameters
    ----------
    pkgs : iterable of :py:class:`Package <conda.package.Package>`
        packages to select newest versions from
    channels : list of str
        an list of channels used to order the packages

    Returns
    -------
    newest : set of :py:class:`Package <conda.package.Package>`
        newest packages for each package in `pkgs`

    '''
    grouped = group_packages_by_channel(pkgs, channels)

    found_names = set()
    results = set()

    for channel in channels:
        pkgs = grouped.get(channel, set())
        named = group_packages_by_name(pkgs)
        for name, pkgs in named.items():
            if name in found_names: continue
            found_names.add(name)
            results |= pkgs

    return results



