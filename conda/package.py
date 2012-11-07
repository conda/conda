from distutils.version import LooseVersion

from requirement import requirement
from verlib import NormalizedVersion, suggest_normalized_version



__all__ = ['package', 'sort_packages_by_version', 'sort_packages_by_name']


def dict_property(name):
    @property
    def prop(self):
        return self._info[name]
    return prop

class package(object):

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

    name         = dict_property('name')
    build        = dict_property('build')
    build_number = dict_property('build_number')
    arch         = dict_property('arch')
    platform     = dict_property('platform')
    md5          = dict_property('md5')
    size         = dict_property('size')

    @property
    def build_target(self):
        return self._build_target

    @property
    def version(self):
        return self._version

    @property
    def requires(self):
        return self._requires

    @property
    def canonical_name(self):
        return "%s-%s-%s" % (self.name, self.version.vstring, self.build)

    @property
    def filename(self):
        return self._filename

    @property
    def location(self):
        return self._info.get('location', 'unkown')

    def matches(self, constraint):
        return constraint.match(self)

    def print_info(self, show_requires=True):
        print "   package: %s-%s" % (self.name, self.version),
        print "[%s]" % self._build_target if self.build_target else ""
        print "      arch: %s" % self.arch
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
                (self.name, NormalizedVersion(suggest_normalized_version(sv)), self.build),
                (other.name, NormalizedVersion(suggest_normalized_version(ov)), other.build)
            )
        except:
            return cmp(
                (self.name, self.version.vstring, self.build),
                (other.name, other.version.vstring, other.build)
            )


def sort_packages_by_version(pkgs, reverse=False):
    return sorted(
        list(pkgs),
        reverse=reverse,
        key=lambda pkg: pkg.version
    )

def sort_packages_by_name(pkgs, reverse=False):
    return sorted(
        list(pkgs),
        reverse=reverse,
        key=lambda pkg: pkg.name
    )
