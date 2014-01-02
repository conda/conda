"""
Tools for working with R packages.
"""
#===============================================================================
# Imports
#===============================================================================
from __future__ import division, absolute_import

import re
import sys

from os import makedirs
from os.path import join, isdir, exists, isfile

from itertools import chain

try:
    import yaml
except ImportError:
    sys.exit('Error: could not import yaml (required to read meta.yaml '
             'files of conda recipes)')

from yaml.scanner import ScannerError

#===============================================================================
# Globals
#===============================================================================

# The following base/recommended package names are derived from R's source
# tree (R-3.0.2/share/make/vars.mk).  Hopefully they don't change too much
# between versions.
R_BASE_PACKAGE_NAMES = (
    'base',
    'tools',
    'utils',
    'grDevices',
    'graphics',
    'stats',
    'datasets',
    'methods',
    'grid',
    'splines',
    'stats4',
    'tcltk',
    'compiler',
    'parallel',
)
R_BASE_PACKAGES = set(R_BASE_PACKAGE_NAMES)

R_RECOMMENDED_PACKAGE_NAMES = (
    'MASS',
    'lattice',
    'Matrix',
    'nlme',
    'survival',
    'boot',
    'cluster',
    'codetools',
    'foreign',
    'KernSmooth',
    'rpart',
    'class',
    'nnet',
    'spatial',
    'mgcv',
)
R_RECOMMENDED_PACKAGES = set(R_RECOMMENDED_PACKAGE_NAMES)

# Stolen then tweaked from debian.deb822.PkgRelation.__dep_RE.
VERSION_DEPENDENCY_REGEX_PATTERN = (
    r'^\s*(?P<name>[a-zA-Z0-9.+\-]{1,})'
    r'(\s*\(\s*(?P<relop>[>=<]+)\s*'
    r'(?P<version>[0-9a-zA-Z:\-+~.]+)\s*\))'
    r'?(\s*\[(?P<archs>[\s!\w\-]+)\])?\s*$'
)
VERSION_DEPENDENCY_REGEX = re.compile(VERSION_DEPENDENCY_REGEX_PATTERN)

VIM_YAML_MODELINE = '# vim:set ts=8 sw=2 sts=2 tw=78 et:'

#===============================================================================
# Helpers
#===============================================================================
def r_name_to_conda_name(rname):
    if rname == 'R':
        return 'r'

    return 'r-%s' % rname.lower()

def r_version_to_conda_version(rver):
    return rver.replace('-', '.')

class Dict(dict):
    """
    A dict that allows direct attribute access to keys.
    """
    def __init__(self, *args, **kwds):
        dict.__init__(self, *args, **kwds)
    def __getattr__(self, name):
        return self.__getitem__(name)
    def __setattr__(self, name, value):
        return self.__setitem__(name, value)

def parse_version_dependency(s):
    match = VERSION_DEPENDENCY_REGEX.match(s)
    if match:
        return Dict(
            name=match.group('name'),
            archs=match.group('archs'),
            relop=match.group('relop'),
            version=match.group('version'),
        )

#===============================================================================
# Classes
#===============================================================================
class RVersionDependencyMismatch(BaseException):
    pass

class RPackage(object):
    KEYS_TO_ATTRS = {
        'Site': 'site',
        'Archs': 'archs',
        'Depends': 'depends',
        'Enhances': 'enhances',
        'Imports': 'imports',
        'License': 'license',
        'License_is_FOSS': 'license_is_foss',
        'License_restricts_use': 'license_restricts_use',
        'LinkingTo': 'linking_to',
        'MD5sum': 'md5sum',
        'NeedsCompilation': 'needs_compilation',
        'OS_type': 'os_type',
        'Package': 'package',
        'Path': 'repo_path',
        'Priority': 'priority',
        'Suggests': 'suggests',
        'Version': 'version',

        'Title': 'title',
        'Author': 'author',
        'Maintainer': 'maintainer',
    }

    REPODATA_KEYMAP = {
        'fn': 'conda_build_tarball',
        'name': 'conda_name',
        'build': 'conda_build',
        'depends': 'conda_depends',
        'version': 'conda_version',
        'build_number': 'conda_build_number',
    }

    BUILDDATA_KEYMAP = {
        'fn': 'conda_build_tarball',
        'cran': 'cran',
        'name': 'conda_name',
        'build': 'conda_build',
        'depends': 'conda_depends',
        'version': 'conda_version',
        'build_number': 'conda_build_number',
        'reverse_depends': 'conda_reverse_depends',
    }

    CONDA_ATTRS = [
        'conda_name',
        'conda_version',
        'conda_depends',
        'conda_build_number',
        'conda_build_tarball',
        'conda_reverse_depends',
        'conda_unsatisfied_depends',
    ]

    OTHER_ATTRS = [
        'fn',
        'url',
        'path',
        'cran',
        'bld_bat',
        'build_sh',
        'base_url',
        'is_valid',
        'meta_yaml',
        'meta_path',
        'output_dir',
        'meta_yaml_needs_persisting',
    ]

    __slots__ = (
        OTHER_ATTRS +
        CONDA_ATTRS +
        [ k for k in KEYS_TO_ATTRS.values() ]
    )

    def __init__(self, **kwds):
        self._load_from_cran_kwds(kwds)

    def _load_from_cran_kwds(self, kwds):
        self.cran = kwds
        m = self.KEYS_TO_ATTRS
        missing = set(m.keys())
        for (key, value) in kwds.iteritems():
            attr = m.get(key)
            if attr:
                setattr(self, attr, value)
                missing.remove(key)

        for key in missing:
            setattr(self, m[key], '')

    def _to_repodata_dict(self):
        return {
            l: getattr(self, r)
                for (l, r) in self.REPODATA_KEYMAP.iteritems()
        }

    def _to_builddata_dict(self):
        return {
            l: getattr(self, r)
                for (l, r) in self.BUILDDATA_KEYMAP.iteritems()
        }

class CondaRPackage(RPackage):
    def __init__(self, lines, base_url, output_dir):
        self._load_from_cran_lines(lines)

        # CRAN packages that depend on R versions later than the current one
        # appear to have a Path->repo_path attribute.  At the time of writing,
        # the current R version is 3.0.2, and there are two packages at the
        # end of the CRAN PACKAGES file that have a dependency on R 3.1; these
        # both have a 'Path: 3.1.0/Other' entry.  If we detect such a path,
        # raise an exception indicating this package is not applicable.
        if self.repo_path:
            raise RVersionDependencyMismatch()

        self.conda_name = r_name_to_conda_name(self.package)
        self.conda_version = r_version_to_conda_version(self.version)

        self.base_url = base_url + '/' if base_url[-1] != '/' else base_url
        self.output_dir = output_dir

        self.fn = '%s_%s.tar.gz' % (self.package, self.version)
        self.url = self.base_url + self.fn
        self.path = join(output_dir, self.conda_name)

        self.meta_yaml = None
        self.meta_path = join(self.path, 'meta.yaml')
        self.build_sh = join(self.path, 'build.sh')
        self.bld_bat = join(self.path, 'bld.bat')

        self.depends = [ s.strip() for s in self.depends.split(',') ]
        self.imports = [ s.strip() for s in self.imports.split(',') ]

        # Always make R a dependency.
        self.conda_depends = [ 'r', ]

        ignore = R_BASE_PACKAGES | R_RECOMMENDED_PACKAGES

        seen = set()

        for pkg in [ d for d in chain(self.depends, self.imports) if d ]:

            dep = parse_version_dependency(pkg)
            r_name = dep.name
            conda_name = r_name_to_conda_name(r_name)

            # Make sure the dependency isn't one of the base or recommended
            # packages.
            if r_name == 'R' or r_name in ignore:
                continue

            if r_name in seen:
                continue

            seen.add(r_name)

            self.conda_depends.append(conda_name)

        self._determine_build_number()

        self.conda_build = str(self.conda_build_number)
        self.conda_build_tarball = (
            '%s-%s-%d.tar.bz2' % (
                self.conda_name,
                self.conda_version,
                self.conda_build_number,
            )
        )

        self.conda_reverse_depends = []
        self.conda_unsatisfied_depends = []


    def _load_from_cran_lines(self, lines):
        d = {}
        for line in lines:
            if not line:
                continue
            (k, v) = line.split(': ')
            d[k] = v
        self._load_from_cran_kwds(d)

    def __generate_meta_yaml(self):
        md5sum = (('  md5: %s' % self.md5sum) if self.md5sum else '')
        deps = [ '    - %s' % d for d in self.conda_depends ]

        l = [
            'package:',
            '  name: %s' % self.conda_name,
            '  version: %s' % self.conda_version,
            '',
            'source:',
            '  fn: %s' % self.fn,
            '  url: %s' % self.url,
        ]

        if md5sum:
            l += [ md5sum, ]

        l += [
            '',
            'build:',
            '  number: %d' % self.conda_build_number,
            '',
            'requirements:',
            '  build:',
        ] + deps + [ '  run:', ] + deps + [ '', ]

        if self.license:
            l += [
                'about:',
                '  license: %s' % self.license,
            ]

        l += [ '', VIM_YAML_MODELINE, '' ]

        return '\n'.join(l)

    def _generate_build_sh(self):
        l = [
            '#!/bin/sh',
            '',
            '$R CMD INSTALL --build .',
            '',
        ]

        return '\n'.join(l)

    def _generate_bld_bat(self):
        l = [
            '%R_CMD% INSTALL --build .',
            ''
        ]

        return '\n'.join(l)

    def _determine_build_number(self):
        self.meta_yaml_needs_persisting = True

        if not isfile(self.meta_path):
            self.conda_build_number = 0
            return

        # File already exists, see if the version differs.
        with open(self.meta_path, 'r') as f:
            old = f.read()

        try:
            yaml_old = yaml.load(old)
        except ScannerError:
            err = sys.stderr.write
            err("removing corrupt/malformed recipe %s\n" % self.meta_path)
            os.remove(self.meta_path)
            self.conda_build_number = 0
            return

        try:
            old_version = yaml_old['package']['version']
        except KeyError:
            old_version = None

        if old_version != self.conda_version:
            # Version differs, treat this as the first build.
            self.conda_build_number = 0
            return

        # File already exists and version doesn't differ.  If the existing
        # file didn't have a build number set, it would have defaulted to 0,
        # in which case, our next build number is 1.
        try:
            old_build_number = yaml_old['build']['number']
        except KeyError:
            self.conda_build_number = 1
            return

        # File already exists, version is the same, and there was previously a
        # build number specified.  Compare the old file to our newly generated
        # yaml content (excluding the build number artefacts) and see if they
        # differ; if they don't, there haven't been any changes and we don't
        # need to persist the new yaml.

        # Set a temporary build number so the yaml can be generated.
        self.conda_build_number = 0
        new = self.__generate_meta_yaml()
        yaml_new = yaml.load(new)

        del yaml_old['build']['number']
        del yaml_new['build']['number']
        if yaml_old == yaml_new:
            self.conda_build_number = old_build_number
            self.meta_yaml_needs_persisting = False
            self.meta_yaml = new
        else:
            self.conda_build_number = int(old_build_number) + 1

    def write_recipe(self):
        if not isdir(self.path):
            makedirs(self.path)

        if self.meta_yaml_needs_persisting:
            if not self.meta_yaml:
                self.meta_yaml = self.__generate_meta_yaml()
            with open(self.meta_path, 'w') as f:
                f.write(self.meta_yaml)
            self.meta_yaml_needs_persisting = False

        if not isfile(self.build_sh):
            with open(self.build_sh, 'w') as f:
                f.write(self._generate_build_sh())

        if not isfile(self.bld_bat):
            with open(self.bld_bat, 'w') as f:
                f.write(self._generate_bld_bat())

#===============================================================================
# Main
#===============================================================================
def main(args, parser):
    pass

# vim:set ts=8 sw=4 sts=4 tw=78 et:
