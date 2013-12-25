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

#===============================================================================
# Helpers
#===============================================================================
def r_name_to_conda_name(rname):
    if rname == 'R':
        return 'r'
    else:
        return 'r-%s' % rname.lower().replace('.', '')

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
class RPackage(object):
    KEYS_TO_ATTRS = {
        # CRAN Fields
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
        'Path': 'path',
        'Priority': 'priority',
        'Suggests': 'suggests',
        'Version': 'version',

        # Other
        'Title': 'title',
        'Author': 'author',
        'Maintainer': 'maintainer',
    }

    CONDA_ATTRS = [
        'conda_name',
        'conda_version',
        'conda_depends',
        'conda_build_number',

    ]

    CONTEXT_ATTRS = [
        'fn',
        'url',
        'path',
    ]

    OTHER_ATTRS = [
        'bld_bat',
        'build_sh',
        'meta_yaml',
        'meta_path',
        'context_set',
        'meta_yaml_needs_persisting',
    ]

    __slots__ = (
        OTHER_ATTRS +
        CONDA_ATTRS +
        CONTEXT_ATTRS +
        [ k for k in KEYS_TO_ATTRS.values() ]
    )

    def __init__(self, **kwds):
        self._load_from_kwds(kwds)

        self.conda_name = r_name_to_conda_name(self.package)
        self.conda_version = r_version_to_conda_version(self.version)

        self.depends = [ s.strip() for s in self.depends.split(',') ]
        self.imports = [ s.strip() for s in self.imports.split(',') ]

        deps = [ ]

        ignore = R_BASE_PACKAGES | R_RECOMMENDED_PACKAGES

        for pkg in [ d for d in chain(self.depends, self.imports) if d ]:
            dep = parse_version_dependency(pkg)
            name = dep.name
            # Make sure the dependency isn't one of the base or recommended
            # packages.
            if name in ignore:
                continue

            # We can't do anything useful with the version dependency yet as
            # conda doesn't support >=/=<.
            deps.append(r_name_to_conda_name(name))

        self.conda_depends = deps

        self.clear_context(force=True)

    def _load_from_kwds(self, kwds):
        m = self.KEYS_TO_ATTRS
        missing = set(m.keys())
        for (key, value) in kwds.iteritems():
            attr = m.get(key)
            if attr:
                setattr(self, attr, value)
                missing.remove(key)

        for key in missing:
            setattr(self, m[key], '')

    @classmethod
    def from_lines(cls, lines):
        d = {}
        for line in lines:
            (k, v) = line.split(': ')
            d[k] = v
        return cls(**d)

    def set_context(self, url, output_dir):
        assert not self.context_set
        self.url = url
        self.fn = url[url.rfind('/')+1:]
        self.path = join(output_dir, self.conda_name)
        self.meta_path = join(self.path, 'meta.yaml')
        self.build_sh = join(self.path, 'build.sh')
        self.bld_bat = join(self.path, 'bld.bat')
        self.context_set = True
        self._determine_build_number()

    def clear_context(self, force=False):
        if not force:
            assert self.context_set
        self.fn = None
        self.url = None
        self.path = None
        self.meta_path = None
        self.meta_yaml = None
        self.context_set = None
        self.conda_build_number = None
        self.meta_yaml_needs_persisting = None

    def __generate_meta_yaml(self):
        assert self.context_set

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

        if self.md5sum:
            l += [ '    - %s' % self.md5sum ]

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
                '',
            ]

        return '\n'.join(l)

    def _generate_build_sh(self):
        l = [
            '#!/bin/sh',
            '',
            '$R CMD INSTALL --build .',
            ''
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

        yaml_old = yaml.load(old)

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

    def persist(self):
        assert self.context_set
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
