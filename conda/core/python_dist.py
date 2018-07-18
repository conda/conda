# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import OrderedDict
from glob import glob
from os import listdir
from os.path import basename, isdir, isfile, join, dirname

import csv
import email.parser
import json

from ..common.path import win_path_ok
from ..models.channel import Channel
from ..models.enums import PackageType, PathType
from ..models.records import PathData, PathDataV1, PathsData, PrefixRecord


# Metadata 2.1
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
    'Requires-Python',
))
METADATA_MULTIPLE_KEYS = frozenset((
    'Platform',
    'Supported-Platform',
    'Classifier',
    'Requires-Dist',
    'Requires-External',
    'Project-URL',
    'Provides-Extra',
    'Provides-Dist',
    'Obsoletes-Dist',
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
        """"""
        self._path = path

        metadata_path = self._process_metadata_path(path)
        self._read_metadata(metadata_path)

    def _process_metadata_path(self, path):
        """"""
        if isdir(path):
            for fname in self.METADATA_FILE_NAMES:
                fpath = join(path, fname)
                if isfile(fpath):
                    metadata_path = fpath
                    break
        elif isfile(path):
            # '<pkg>.egg-info' file contains metadata directly
            metadata_path = path
        else:
            raise MetadataConflictError

        return metadata_path

    def _read_metadata(self, fpath):
        """"""
        if isfile(fpath):
            if fpath.endswith('.json'):
                self._data = self._read_json_metadata(fpath)
            else:
                self._data = self._parse_metadata(fpath)
        else:
            self._data = {}

    def _read_json_metadata(self, fpath):
        """"""
        data = None
        if isfile(fpath):
            with open(fpath, 'r') as f:
                data = json.loads(f.read())
        return data

    def _parsed_metadata_to_json(self, data):
        """Parse the original format which is stored as RFC-822 headers."""
        new_data = OrderedDict() if data else None
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

    def _parse_metadata(self, fpath):
        """"""
        data = None
        if isfile(fpath):
            parser = email.parser.HeaderParser()
            with open(fpath, 'r') as fp:
                data = parser.parse(fp)
        return self._parsed_metadata_to_json(data)

    def get_run_requirements(self, exclude_markers=False):
        """"""
        requirements = []
        if self._data:
            raw_requirements = self._data.get('requires_dist', [])
            for req in raw_requirements:
                if exclude_markers:
                    requirements.append(req.split(';')[0].strip())
                else:
                    requirements.append(req.strip())
        return frozenset(requirements)

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

    def _check_record_data(self, path, checksum, size):
        """Normalizes record data content and format."""
        if checksum:
            assert checksum.startswith('sha256='), (self._path, path, checksum)
        else:
            checksum = None
        size = int(size) if size else None

        return path, checksum, size

    def get_records(self):
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
                    path, checksum, size = self._check_record_data(path, checksum, size)
                    records.append((path, checksum, size))
        except Exception as e:
            print(e)

        return records

    def get_run_requirements(self, exclude_markers=False):
        """
        frozenset([u'joblib', u'scikit-learn', u'lockfile', u'nose (>=1.0)'])
        """
        return self._metadata.get_run_requirements(exclude_markers=exclude_markers)

    def get_prefix_records(self):
        """"""
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

    def get_prefix_records(self):
        """"""
        paths_data = []
        records = self.get_records()
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

    def get_prefix_records(self):
        """"""
        paths_data = []
        for path, _, _ in self.get_records():
            paths_data.append(PathData(
                _path=path,
                path_type=PathType.hardlink,
            ))
        return PathsData(paths_version=1, paths=paths_data)


# Helper funcs
# -----------------------------------------------------------------------------
def norm_package_name(name):
    return name.replace('.', '-').replace('_', '-').lower()


def get_conda_anchor_files_and_records(python_records):
    """"""
    anchor_file_endings = ('.egg-info/PKG-INFO', '.dist-info/RECORD', '.egg-info')
    conda_python_packages = {}

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


def get_python_record(anchor_file, prefix_path):
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
        paths_data = pydist.get_prefix_records()
    elif package_type == PackageType.SHADOW_PYTHON_EGG_LINK:
        paths_data = pydist.get_prefix_records()
        channel = Channel('<develop>')
        build = 'dev_0'
    else:
        raise NotImplementedError()

    depends = pydist.get_run_requirements(exclude_markers=True)

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
