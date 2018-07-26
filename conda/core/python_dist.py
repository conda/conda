# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import namedtuple
from glob import glob
from os import listdir
from os.path import basename, isdir, isfile, join, dirname

import re
import csv
import email.parser
import json

from ..common.compat import odict
from ..common.path import win_path_ok
from ..models.channel import Channel
from ..models.enums import PackageType, PathType
from ..models.records import PathData, PathDataV1, PathsData, PrefixRecord


# TODO: complete this list
_PYPI_TO_CONDA = {
    'graphviz': 'python-graphviz',
}
# TODO: complete pattern with comments
PYPI_SPEC_PATTERN = re.compile(r'(^[a-z|A-Z|_][a-zA-Z0-9_\-\.]*)(\[.*?\])?\(?(.*)\)?')


PySpec = namedtuple('PySpec', ['name', 'extra', 'version', 'markers'])


# Python Packages Metadata 2.1
# -----------------------------------------------------------------------------
METADATA_SINGLE_KEYS = frozenset((
    'Metadata-Version',
    'Name',
    'Version',
    'Summary',
    'Description',
    'Description-Content-Type',
    'Keywords',
    'Home-page',
    'Download-URL',
    'Author',
    'Author-email',
    'Maintainer',
    'Maintainer-email',
    'License',
    # Deprecated
    'Obsoleted-By',
    'Private-Version',
))
METADATA_MULTIPLE_KEYS = frozenset((
    'Platform',
    'Supported-Platform',
    'Classifier',
    'Requires-Dist',
    'Requires-External',
    'Requires-Python',
    'Project-URL',
    'Provides-Extra',
    'Provides-Dist',
    'Obsoletes-Dist',
    # Deprecated
    'Extension',
    'Obsoletes',
    'Provides',
    'Requires',
    'Setup-Requires-Dist',
))


class MetadataConflictError(Exception):
    pass


class PythonDistributionMetadata(object):
    """
    The canonical method to transform metadata fields into such a data
    structure is as follows:
      - The original key-value format should be read with
        email.parser.HeaderParser
      - All transformed keys should be reduced to lower case. Hyphens should
        be replaced with underscores, but otherwise should retain all other
        characters
      - The transformed value for any field marked with "(Multiple-use")
        should be a single list containing all the original values for the
        given key
      - The Keywords field should be converted to a list by splitting the
        original value on whitespace characters
      - The message body, if present, should be set to the value of the
        description key.
      - The result should be stored as a string-keyed dictionary.

    Notes
    -----
      - Metadata 2.1: https://www.python.org/dev/peps/pep-0566/
      - Metadata 2.0: https://www.python.org/dev/peps/pep-0426/
      - Metadata 1.2: https://www.python.org/dev/peps/pep-0345/
      - Metadata 1.1: https://www.python.org/dev/peps/pep-0314/
      - Metadata 1.0: https://www.python.org/dev/peps/pep-0241/
      - https://packaging.python.org/specifications/core-metadata/
    """

    # TODO: Define precedence
    METADATA_FILE_NAMES = ('METADATA', 'PKG-INFO', 'metadata.json')

    def __init__(self, path):
        metadata_path = self._process_metadata_path(path, self.METADATA_FILE_NAMES)
        self._path = path
        self._data = self._read_metadata(metadata_path)

    @staticmethod
    def _process_metadata_path(path, metadata_filenames):
        """"""
        if isdir(path):
            for fname in metadata_filenames:
                fpath = join(path, fname)
                if isfile(fpath):
                    metadata_path = fpath
                    break
        elif isfile(path):
            # '<pkg>.egg-info' file contains metadata directly
            metadata_path = path
        else:
            metadata_path = None
            # raise MetadataConflictError

        return metadata_path

    @classmethod
    def _read_metadata(cls, fpath):
        """"""
        if isfile(fpath):
            if fpath.endswith('.json'):
                data = cls._read_json_metadata(fpath)
            else:
                data = cls._parse_metadata(fpath)
        else:
            data = {}
        return data

    @staticmethod
    def _read_json_metadata(fpath):
        """"""
        data = None
        if isfile(fpath):
            with open(fpath, 'r') as f:
                data = json.loads(f.read())
        return data

    @staticmethod
    def _parsed_metadata_to_json(data):
        """Parse the original format which is stored as RFC-822 headers."""
        new_data = odict()

        if data:
            for key, value in data.items():
                new_key = key.lower().replace('-', '_')
                if key in METADATA_MULTIPLE_KEYS:
                    if new_key not in new_data:
                        new_data[new_key] = [value]
                    else:
                        new_data[new_key].append(value)
                elif key in METADATA_SINGLE_KEYS:
                    new_data[new_key] = value
                else:
                    raise MetadataConflictError

            # TODO: If we need to handle ALL edge cases we might just use the
            # current metadata.py in distlib, or we could use a trimmed down
            # version

            # Multiple values should use plural keys?
            # Handle body?
            # Handle license?

            # Handle keywords
            if 'keywords' in new_data:
                # TODO: Handle comma, semicolon?
                new_data['keywords'] = new_data['keywords'].split()

        return new_data

    @classmethod
    def _parse_metadata(cls, fpath):
        """"""
        data = {}
        if isfile(fpath):
            parser = email.parser.HeaderParser()
            with open(fpath, 'r') as fp:
                data = parser.parse(fp)
        return cls._parsed_metadata_to_json(data)

    def _get_multiple_data(self, key, exclude_markers=False):
        """Helper method to get multiple data values by key."""
        data = []
        if self._data:
            raw_data = self._data.get(key, [])
            for req in raw_data:
                if exclude_markers:
                    data.append(req.split(';')[0].strip())
                else:
                    data.append(req.strip())
        return frozenset(data)

    def get_dist_requirements(self, exclude_markers=False):
        """
        Changed in version 2.1: The field format specification was relaxed to
        accept the syntax used by popular publishing tools.

        Each entry contains a string naming some other distutils project
        required by this distribution.

        The format of a requirement string contains from one to four parts:
          - A project name, in the same format as the Name: field. The only
            mandatory part.
          - A comma-separated list of ‘extra’ names. These are defined by the
            required project, referring to specific features which may need
            extra dependencies.
          - A version specifier. Tools parsing the format should accept
            optional parentheses around this, but tools generating it should
            not use parentheses.
          - An environment marker after a semicolon. This means that the
            requirement is only needed in the specified conditions.

        Example
        -------
        frozenset(['pkginfo', 'PasteDeploy', 'zope.interface (>3.5.0)',
                   'pywin32 >1.0; sys_platform == "win32"'])
        """
        return self._get_multiple_data('requires_dist', exclude_markers=exclude_markers)

    def get_extra_requirements(self, exclude_markers=False):
        """"""
        return self._get_multiple_data('requires_extra', exclude_markers=exclude_markers)

    def get_python_requirements(self, exclude_markers=False):
        """
        New in version 1.2.

        This field specifies the Python version(s) that the distribution is
        guaranteed to be compatible with. Installation tools may look at this
        when picking which version of a project to install.

        The value must be in the format specified in Version specifiers.

        This field may be followed by an environment marker after a semicolon.

        Example
        -------
        frozenset(['>=3', '>2.6,!=3.0.*,!=3.1.*', '~=2.6',
                   '>=3; sys_platform == "win32"'])
        """
        return self._get_multiple_data('requires_python', exclude_markers=exclude_markers)

    def get_external_requirements(self, exclude_markers=False):
        """
        Changed in version 2.1: The field format specification was relaxed to
        accept the syntax used by popular publishing tools.

        Each entry contains a string describing some dependency in the system
        that the distribution is to be used. This field is intended to serve
        as a hint to downstream project maintainers, and has no semantics
        which are meaningful to the distutils distribution.

        The format of a requirement string is a name of an external dependency,
        optionally followed by a version declaration within parentheses.

        This field may be followed by an environment marker after a semicolon.

        Because they refer to non-Python software releases, version numbers for
        this field are not required to conform to the format specified in PEP
        440: they should correspond to the version scheme used by the external
        dependency.

        Notice that there’s is no particular rule on the strings to be used!

        Example
        -------
        frozenset(['C', 'libpng (>=1.5)', 'make; sys_platform != "win32"'])
        """
        return self._get_multiple_data('requires_external', exclude_markers=exclude_markers)

    def get_extra_provides(self, exclude_markers=False):
        """"""
        return self._get_multiple_data('provides_extra', exclude_markers=exclude_markers)

    @property
    def name(self):
        return self._data.get('name')  # TODO: Check for existence?

    @property
    def version(self):
        return self._data.get('version')  # TODO: Check for existence?


# Dist classes
# -----------------------------------------------------------------------------
class BasePythonDistribution(object):
    """"""
    SOURCES_FILES = ()  # Should be one, but many different options
    REQUIRED_FILES = ()

    def __init__(self, path):
        """"""
        self._path = path
        self._check_files()
        self._source_file = None
        self._metadata = PythonDistributionMetadata(path)

    def _check_files(self):
        """Check the existence of mandatory files for a given distribution."""
        if isdir(self._path):
            for fname in self.REQUIRED_FILES:
                fpath = join(self._path, fname)
                assert isfile(fpath)
        elif isfile(self._path):
            pass

    def _check_path_data(self, path, checksum, size):
        """Normalizes record data content and format."""
        if checksum:
            assert checksum.startswith('sha256='), (self._path, path, checksum)
        else:
            checksum = None
        size = int(size) if size else None

        return path, checksum, size

    def get_paths(self):
        """
        Read the list of installed files from record or source files.

        [(u'skdata/__init__.py', u'sha256=47DEQpj8HBSa-_TImW-5JCeuQeRkm5NMpJWZG3hSuFU', u'0'),
         (u'skdata/diabetes.py', None, None),
         ...
        ]
        """
        records = []
        for fname in self.SOURCES_FILES:
            fpath = join(self._path, fname)
            if isfile(fpath):
                self._source_file = fpath
                break
        try:
            with open(fpath, newline='') as csvfile:
                record_reader = csv.reader(csvfile, delimiter=',')

                for row in record_reader:
                    missing = [None for i in range(len(row), 3)]
                    path, checksum, size = row + missing
                    path, checksum, size = self._check_path_data(path, checksum, size)
                    records.append((path, checksum, size))
        except Exception as e:
            print(e)

        return records

    def get_dist_requirements(self, exclude_markers=False):
        return self._metadata.get_dist_requirements(exclude_markers=exclude_markers)

    def get_extra_requirements(self, exclude_markers=False):
        return self._metadata.get_extra_requirements(exclude_markers=exclude_markers)

    def get_extra_provides(self, exclude_markers=False):
        return self._metadata.get_extra_provides(exclude_markers=exclude_markers)

    def get_python_requirements(self, exclude_markers=False):
        return self._metadata.get_python_requirements(exclude_markers=exclude_markers)

    # Conda dependencies format
    def get_dependencies(self, python_version=None):
        reqs = self.get_dist_requirements(exclude_markers=True)
        norm_reqs = set([])
        for req in reqs:
            parts = req.split(' ')
            if len(parts) > 1:
                name, ver = parts
                req = norm_package_name(name) + ' ' + ''.join(parts[1:])
            norm_reqs.add(req)

        python_versions = self.get_python_requirements(exclude_markers=True)
        if python_versions:
            pyvers = []
            for pyver in python_versions:
                parts = [i.strip() for i in pyver.split(',')]
                pyver = 'python (' + ','.join(parts) + ')'
                pyvers.append(pyver)
            pyver = pyvers[0]
        elif python_version:
            # FIXME: fixed current one
            pyver = 'python (==' + python_version + ')'
        else:
            # FIXME: current one?
            pyver = 'python'

        norm_reqs.add(pyver)
        return frozenset(norm_reqs)

    def get_optional_dependencies(self):
        raise NotImplementedError

    def get_paths_data(self):
        raise NotImplementedError

    @property
    def name(self):
        return self._metadata.name

    @property
    def version(self):
        return self._metadata.version


class PythonInstalledDistribution(BasePythonDistribution):
    """
    Notes
    -----
      - https://www.python.org/dev/peps/pep-0376/
    """
    SOURCES_FILES = ('RECORD', )
    REQUIRED_FILES = ('METADATA', 'RECORD', 'INSTALLER')

    def get_paths_data(self):
        """"""
        paths_data = []
        records = self.get_paths()
        for (path, checksum, size) in records:
            sha256 = checksum[7:] if checksum else None
            paths_data.append(PathDataV1(
                _path=path,
                path_type=PathType.hardlink,
                sha256=sha256,
                size_in_bytes=size
            ))
        return PathsData(paths_version=1, paths=paths_data)


class PythonEggInfoDistribution(BasePythonDistribution):
    """
    Notes
    -----
      - http://peak.telecommunity.com/DevCenter/EggFormats
    """
    SOURCES_FILES = ('SOURCES', 'SOURCES.txt')
    REQUIRED_FILES = ()

    def get_paths_data(self):
        """"""
        paths_data = []
        for path, _, _ in self.get_paths():
            paths_data.append(PathData(
                _path=path,
                path_type=PathType.hardlink,
            ))
        return PathsData(paths_version=1, paths=paths_data)


# Helper funcs
# -----------------------------------------------------------------------------
def norm_package_name(name):
    """"""
    return name.replace('.', '-').replace('_', '-').lower()


def norm_package_version(version):
    """"""
    if version:
        version = ','.join(v.strip() for v in version.split(',')).strip()

        if version.startswith('(') and version.endswith(')'):
            version = version[1:-1]

        version = ''.join(v for v in version if v.strip())

    return version


def parse_requirement(requirement):
    """"""
    parts = requirement.split(';')
    if len(parts) == 1:
        spec = requirement
        markers = None
    else:
        spec, markers = parts
        markers = markers.strip()

    name, extra, version = PYPI_SPEC_PATTERN.match(spec).groups()
    name = norm_package_name(name).strip()
    extra = extra[1:-1] if extra else None
    version = norm_package_version(version) if version else None

    return PySpec(name, extra, version, markers)


def get_conda_anchor_files_and_records(python_records):
    """"""
    anchor_file_endings = ('.egg-info/PKG-INFO', '.dist-info/RECORD', '.egg-info')
    conda_python_packages = odict()

    for prefix_record in python_records:
        for fpath in prefix_record.files:
            if fpath.endswith(anchor_file_endings) and 'site-packages' in fpath:
                # Then 'fpath' is an anchor file
                conda_python_packages[fpath] = prefix_record

    return conda_python_packages


def get_site_packages_anchor_files(site_packages_path, site_packages_dir):
    """"""
    site_packages_anchor_files = set()
    for fname in listdir(site_packages_path):
        if fname.endswith('.dist-info'):
            anchor_file = "%s/%s/%s" % (site_packages_dir, fname, 'RECORD')
        elif fname.endswith(".egg-info"):
            if isfile(join(site_packages_path, fname)):
                anchor_file = "%s/%s" % (site_packages_dir, fname)
            else:
                anchor_file = "%s/%s/%s" % (site_packages_dir, fname, "PKG-INFO")
        elif fname.endswith('.egg-link'):
            anchor_file = "%s/%s" % (site_packages_dir, fname)
        elif fname.endswith('.pth'):
            continue
        else:
            continue
        site_packages_anchor_files.add(anchor_file)

    return site_packages_anchor_files


def get_dist_file_from_egg_link(egg_link_file, prefix_path):
    """"""
    egg_info_full_path = None

    with open(join(prefix_path, win_path_ok(egg_link_file))) as fh:
        # TODO: Will an egg-link always contain a single entry?
        egg_link_contents = fh.readlines()[0].strip()

    egg_info_fnames = glob(join(egg_link_contents, "*.egg-info"))
    if egg_info_fnames:
        assert len(egg_info_fnames) == 1, (egg_link_file, egg_info_fnames)
        egg_info_full_path = join(egg_link_contents, egg_info_fnames[0])

        if isdir(egg_info_full_path):
            egg_info_full_path = join(egg_info_full_path, "PKG-INFO")

    return egg_info_full_path


def get_python_distribution_info(anchor_file, prefix_path):
    """"""
    if anchor_file.endswith('.egg-link'):
        sp_reference = None
        dist_file = get_dist_file_from_egg_link(anchor_file, prefix_path)
        dist_cls = PythonEggInfoDistribution
        package_type = PackageType.SHADOW_PYTHON_EGG_LINK
    elif ".dist-info" in anchor_file:
        sp_reference = basename(dirname(anchor_file))
        dist_file = join(prefix_path, win_path_ok(dirname(anchor_file)))
        dist_cls = PythonInstalledDistribution
        package_type = PackageType.SHADOW_PYTHON_DIST_INFO
    elif anchor_file.endswith(".egg-info"):
        sp_reference = basename(anchor_file)
        dist_file = join(prefix_path, win_path_ok(anchor_file))
        dist_cls = PythonEggInfoDistribution
        package_type = PackageType.SHADOW_PYTHON_EGG_INFO_FILE
    elif ".egg-info" in anchor_file:
        sp_reference = basename(dirname(anchor_file))
        dist_file = join(prefix_path, win_path_ok(dirname(anchor_file)))
        dist_cls = PythonEggInfoDistribution
        package_type = PackageType.SHADOW_PYTHON_EGG_INFO_DIR
    else:
        raise NotImplementedError()

    try:
        pydist = dist_cls(dist_file)
    except MetadataConflictError:
        print("MetadataConflictError:", anchor_file)
        pydist = None

    return pydist, sp_reference, package_type


def get_python_record(anchor_file, prefix_path, python_version=None):
    """
    Convert a python package defined by an anchor file (Metadata information)
    into a conda prefix record object.
    """
    # TODO: normalize names against '.', '-', '_'
    # TODO: ensure that this dist is *actually* the dist that matches conda-meta
    # TODO: need to add entry points, "exports," and other files that might not be in RECORD  # NOQA
    # TODO: need to add python (with version?) to deps

    pydist, sp_reference, package_type = get_python_distribution_info(anchor_file, prefix_path)

    if pydist is None:
        return None
    channel = Channel('pypi')
    build = 'pypi_0'

    if package_type == PackageType.SHADOW_PYTHON_EGG_INFO_FILE:
        paths_data = None
    elif package_type in (PackageType.SHADOW_PYTHON_DIST_INFO,
                          PackageType.SHADOW_PYTHON_EGG_INFO_DIR):
        paths_data = pydist.get_paths_data()
    elif package_type == PackageType.SHADOW_PYTHON_EGG_LINK:
        paths_data = pydist.get_paths_data()
        channel = Channel('<develop>')
        build = 'dev_0'
    else:
        raise NotImplementedError()

    depends = pydist.get_dependencies()
    print(pydist.name.lower())
    print(depends)
    print(pydist.get_extra_provides())
    print('\n')

    python_rec = PrefixRecord(
        package_type=package_type,
        name=pydist.name.lower(),
        version=pydist.version,
        channel=channel,
        subdir='pypi',
        fn=sp_reference,
        build=build,
        build_number=0,
        paths_data=paths_data,
        depends=depends,
    )

    return python_rec
