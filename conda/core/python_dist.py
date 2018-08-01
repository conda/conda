# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import namedtuple
from glob import glob
from os import listdir
from os.path import basename, isdir, isfile, join, dirname

import csv
import email.parser
import os
import platform
import re
import sys
import warnings

from .._vendor.frozendict import frozendict
from ..common.compat import odict
from ..common.path import win_path_ok
from ..models.channel import Channel
from ..models.enums import PackageType, PathType
from ..models.records import PathData, PathDataV1, PathsData, PrefixRecord


# TODO: complete this list
PYPI_TO_CONDA = {
    'graphviz': 'python-graphviz',
}
# TODO: complete this list
PYPI_CONDA_DEPS = {
    'graphviz': ['graphviz'],  # What versions?
}
# This regex can process requirement including or not including name.
# This is useful for parsing, for example, `Python-Version`
PARTIAL_PYPI_SPEC_PATTERN = re.compile(r'''
    # Text needs to be stripped and all extra spaces replaced by single spaces
    (?P<name>^[A-Z0-9][A-Z0-9._-]*)?
    \s?
    (\[(?P<extras>.*)\])?
    \s?
    (?P<constraints>\(? \s? ([\w\d<>=!~,\s\.\*]*) \s? \)? )?
    \s?
''', re.VERBOSE | re.IGNORECASE)
PySpec = namedtuple('PySpec', ['name', 'extras', 'constraints', 'marker', 'url'])


class MetadataWarning(Warning):
    pass


class PythonDistributionMetadata(object):
    """
    Object representing the metada of a Python Distribution given by anchor
    file (or directory) path.

    Notes
    -----
      - https://packaging.python.org/specifications/core-metadata/
      - Metadata 2.1: https://www.python.org/dev/peps/pep-0566/
      - Metadata 2.0: https://www.python.org/dev/peps/pep-0426/ (Withdrawn)
      - Metadata 1.2: https://www.python.org/dev/peps/pep-0345/
      - Metadata 1.1: https://www.python.org/dev/peps/pep-0314/
      - Metadata 1.0: https://www.python.org/dev/peps/pep-0241/
    """
    FILE_NAMES = ('METADATA', 'PKG-INFO')

    # Python Packages Metadata 2.1
    # -----------------------------------------------------------------------------
    SINGLE_USE_KEYS = frozendict([
        ('Metadata-Version', 'metadata_version'),
        ('Name', 'name'),
        ('Version', 'version'),
        ('Summary', 'summary'),
        ('Description', 'description'),
        ('Description-Content-Type', 'description_content_type'),
        ('Keywords', 'keywords'),
        ('Home-page', 'home_page'),
        ('Download-URL', 'download_url'),
        ('Author', 'author'),
        ('Author-email', 'author_email'),
        ('Maintainer', 'maintainer'),
        ('Maintainer-email', 'maintainer_email'),
        ('License', 'license'),
        # Deprecated
        ('Obsoleted-By', 'obsoleted_by'),  # Note: See 2.0
        ('Private-Version', 'private_version'),  # Note: See 2.0
    ])
    MULTIPLE_USE_KEYS = frozendict([
        ('Platform', 'platform'),
        ('Supported-Platform', 'supported_platform'),
        ('Classifier', 'classifier'),
        ('Requires-Dist', 'requires_dist'),
        ('Requires-External', 'requires_external'),
        ('Requires-Python', 'requires_python'),
        ('Project-URL', 'project_url'),
        ('Provides-Extra', 'provides_extra'),
        ('Provides-Dist', 'provides_dist'),
        ('Obsoletes-Dist', 'obsoletes_dist'),
        # Deprecated
        ('Extension', 'extension'),  # Note: See 2.0
        ('Obsoletes', 'obsoletes'),
        ('Provides', 'provides'),
        ('Requires', 'requires'),
        ('Setup-Requires-Dist', 'setup_requires_dist'),  # Note: See 2.0
    ])

    def __init__(self, path):
        metadata_path = self._process_path(path, self.FILE_NAMES)
        self._path = path
        self._data = self._read_metadata(metadata_path)

    @staticmethod
    def _process_path(path, metadata_filenames):
        """Find metadata file inside dist-info folder, or check direct file."""
        metadata_path = None
        if path:
            if isdir(path):
                for fname in metadata_filenames:
                    fpath = join(path, fname)
                    if isfile(fpath):
                        metadata_path = fpath
                        break
            elif isfile(path):
                # '<pkg>.egg-info' file contains metadata directly
                filenames = ['.egg-info']
                if metadata_filenames:
                    filenames.extend(metadata_filenames)
                assert any(path.endswith(filename) for filename in filenames)
                metadata_path = path
            else:
                # `path` does not exist
                warnings.warn("Metadata path not found", MetadataWarning)
        else:
            warnings.warn("Metadata path not found", MetadataWarning)

        return metadata_path

    @classmethod
    def _message_to_dict(cls, message):
        """
        Convert the RFC-822 headers data into a dictionary.

        `message` is an email.parser.Message instance.

        The canonical method to transform metadata fields into such a data
        structure is as follows:
          - The original key-value format should be read with
            email.parser.HeaderParser
          - All transformed keys should be reduced to lower case. Hyphens
            should be replaced with underscores, but otherwise should retain
            all other characters
          - The transformed value for any field marked with "(Multiple-use")
            should be a single list containing all the original values for the
            given key
          - The Keywords field should be converted to a list by splitting the
            original value on whitespace characters
          - The message body, if present, should be set to the value of the
            description key.
          - The result should be stored as a string-keyed dictionary.
        """
        new_data = odict()

        if message:
            for key, value in message.items():

                if key in cls.MULTIPLE_USE_KEYS:
                    new_key = cls.MULTIPLE_USE_KEYS[key]
                    if new_key not in new_data:
                        new_data[new_key] = [value]
                    else:
                        new_data[new_key].append(value)

                elif key in cls.SINGLE_USE_KEYS:
                    new_key = cls.SINGLE_USE_KEYS[key]
                    new_data[new_key] = value

                else:
                    new_key = key.replace('-', '_').lower()
                    new_data[new_key] = value
                    # FIXME: Add this key anyway or just warn? Raise Exception?
                    # Add as single key or as multiple key?
                    warnings.warn("Key '{}' not recognized".format(key),
                                  MetadataWarning)

            # TODO: Handle license later on for convenience
            # Check classifiers or license key

            # Handle keywords
            if 'keywords' in new_data:
                keywords = new_data['keywords']
                if ';' in keywords:
                    new_data['keywords'] = new_data['keywords'].split(';')
                elif ',' in keywords:
                    new_data['keywords'] = new_data['keywords'].split(',')
                else:
                    new_data['keywords'] = new_data['keywords'].split(' ')

        return new_data

    @classmethod
    def _read_metadata(cls, fpath):
        """
        Read the original format which is stored as RFC-822 headers.
        """
        data = odict()
        if fpath and isfile(fpath):
            parser = email.parser.HeaderParser()

            with open(fpath, 'r') as fp:
                data = parser.parse(fp)

        return cls._message_to_dict(data)

    def _get_multiple_data(self, keys, exclude_markers=False):
        """
        Helper method to get multiple data values by keys.

        Keys is an iterable including the prefered key in order, to include
        values of key that might have been replaced (deprecated), for example
        keys can be ['requires_dist', 'requires'], where the key 'requires' is
        deprecated and replaced by 'requires_dist'.
        """
        data = []
        if self._data:
            for key in keys:
                raw_data = self._data.get(key, [])
                for req in raw_data:
                    if exclude_markers:
                        data.append(req.split(';')[0].strip())
                    else:
                        data.append(req.strip())
                if data:
                    break

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

        Return 'Requires' if 'Requires-Dist' is empty.
        """
        return self._get_multiple_data(['requires_dist', 'requires'],
                                       exclude_markers=exclude_markers)

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
        return self._get_multiple_data(['requires_python'],
                                       exclude_markers=exclude_markers)

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
        return self._get_multiple_data(['requires_external'],
                                       exclude_markers=exclude_markers)

    def get_extra_provides(self):
        """
        New in version 2.1.

        A string containing the name of an optional feature. Must be a valid
        Python identifier. May be used to make a dependency conditional on
        hether the optional feature has been requested.

        Example
        -------
        frozenset(['pdf', 'doc', 'test', 'other ; some_marker >= 2.7'])
        """
        return self._get_multiple_data(['provides_extra'])

    def get_dist_provides(self, exclude_markers=False):
        """
        Return `Provides` in case `Provides-Dist` is empty.
        """
        return self._get_multiple_data(['provides_dist', 'provides'],
                                       exclude_markers=exclude_markers)

    def get_dist_obsolete(self, exclude_markers=False):
        """
        New in version 1.2.

        Changed in version 2.1: The field format specification was relaxed to
        accept the syntax used by popular publishing tools.

        Each entry contains a string describing a distutils project’s
        distribution which this distribution renders obsolete, meaning that
        the two projects should not be installed at the same time.

        Version declarations can be supplied. Version numbers must be in the
        format specified in Version specifiers [1].

        The most common use of this field will be in case a project name
        changes, e.g. Gorgon 2.3 gets subsumed into Torqued Python 1.0. When
        you install Torqued Python, the Gorgon distribution should be removed.

        Return `Obsoletes` in case `Obsoletes-Dist` is empty.

        Example
        -------
        frozenset(['Gorgon', "OtherProject (<3.0) ; python_version == '2.7'"])

        Notes
        -----
        - [1] https://packaging.python.org/specifications/version-specifiers/
        """

        return self._get_multiple_data(['obsoletes_dist', 'obsoletes'],
                                       exclude_markers=exclude_markers)

    def get_classifiers(self, exclude_markers=False):
        """
        Classifiers are described in PEP 301, and the Python Package Index
        publishes a dynamic list of currently defined classifiers.
        """
        return self._get_multiple_data(['classifier'],
                                       exclude_markers=exclude_markers)

    @property
    def name(self):
        return self._data.get('name')  # TODO: Check for existence?

    @property
    def version(self):
        return self._data.get('version')  # TODO: Check for existence?


# Dist classes
# -----------------------------------------------------------------------------
class BasePythonDistribution(object):
    """
    Base object describing a python distribution based on path to anchor file.
    """
    SOURCES_FILES = ()  # Should be one, but many different options
    REQUIRED_FILES = ()
    ENTRY_POINTS_FILES = ('entry_points.txt')

    def __init__(self, path):
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
        Read the list of installed paths from record or source file.

        [(u'skdata/__init__.py', u'sha256=47DEQpj8HBSa-_TImW-5JCeuQeRkm5NMpJWZG3hSuFU', u'0'),
         (u'skdata/diabetes.py', None, None),
         ...
        ]
        """
        records = []
        if isdir(self._path):
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

    def get_python_requirements(self, exclude_markers=False):
        return self._metadata.get_python_requirements(exclude_markers=exclude_markers)

    def get_external_requirements(self, exclude_markers=False):
        return self._metadata.get_external_requirements(exclude_markers=exclude_markers)

    def get_extra_provides(self):
        return self._metadata.get_extra_provides()

    # Conda dependencies format
    def get_dependencies(self, context):
        """
        Process metadata fields providing dependency information.

        This includes normalizing fields, and evaluation environment markers.
        """
        # Process dependencies
        reqs = self.get_dist_requirements(exclude_markers=False)
        extras = self.get_extra_provides()
        norm_reqs = set([])
        for req in reqs:
            spec = parse_specification(req)
            if evaluate_marker(spec.marker, context, extras):
                norm_name = norm_package_name(spec.name)
                conda_name = pypi_name_to_conda_name(norm_name)
                if spec.constraints:
                    norm_req = conda_name + ' ' + spec.constraints
                else:
                    norm_req = conda_name
                norm_reqs.add(norm_req)

        # Add python dependency
        context_py_ver = context.get('python_version')
        python_versions = self.get_python_requirements(exclude_markers=False)
        if python_versions:
            pyvers = []
            # print('python_versions', python_versions)
            for pyver_req in python_versions:
                pyspec = parse_specification(pyver_req)
                if evaluate_marker(pyspec.marker, context, []):
                    pyvers.append(pyspec.constraints)
            if pyvers:
                pyver = 'python ' + ','.join(pyvers)
            else:
                pyver = 'python'
        elif context_py_ver:
            pyver = 'python ==' + '.'.join(context_py_ver.split('.')[:2])
        else:
            pyver = 'python'

        norm_reqs.add(pyver)

        return frozenset(norm_reqs)

    def get_optional_dependencies(self):
        raise NotImplementedError

    def get_entry_points(self):
        raise NotImplementedError
        # TODO: need to add entry points, "exports," and other files that might
        # not be in RECORD
        # config = ConfigParser.RawConfigParser()

    def get_paths_data(self):
        raise NotImplementedError

    @property
    def name(self):
        return self._metadata.name

    @property
    def norm_name(self):
        return norm_package_name(self.name)

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
        paths_data = []
        for (path, checksum, size) in self.get_paths():
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
    return name.replace('.', '-').replace('_', '-').lower() if name else ''


def pypi_name_to_conda_name(pypi_name):
    return PYPI_TO_CONDA.get(pypi_name, pypi_name) if pypi_name else ''


def norm_package_version(version):
    """Normalize a version by removing extra spaces and parentheses."""
    if version:
        version = ','.join(v.strip() for v in version.split(',')).strip()

        if version.startswith('(') and version.endswith(')'):
            version = version[1:-1]

        version = ''.join(v for v in version if v.strip())

    return version


def split_spec(spec, sep):
    """Split a spec by separator and return stripped start and end parts."""
    parts = spec.rsplit(sep, 1)
    spec_start = parts[0].strip()
    spec_end = ''
    if len(parts) == 2:
        spec_end = parts[-1].strip()
    return spec_start, spec_end


def parse_specification(spec):
    """
    Parse a requirement from a python distribution metadata and return a
    namedtuple with name, extras, constraints, marker and url components.

    This method does not enforce strict specifications but extracts the
    information which is assumed to be *correct*. As such no errors are raised.

    Example
    -------
    >>> parse_specification('requests[security]>=3.3.0 ; foo >= 2.7 or bar == 1')
    PySpec(name='requests', extras=['security'], constraints='>=3.3.0',
           marker='foo >= 2.7 or bar == 1', url=''])
    """
    name, extras, const = spec, [], ''

    # Remove excess whitespace
    spec = ' '.join(p for p in spec.split(' ') if p).strip()

    # Extract marker (Assumes that there can only be one ';' inside the spec)
    spec, marker = split_spec(spec, ';')

    # Extract url (Assumes that there can only be one '@' inside the spec)
    spec, url = split_spec(spec, '@')

    # Find name, extras and constraints
    r = PARTIAL_PYPI_SPEC_PATTERN.match(spec)
    if r:
        # Normalize name
        name = r.group('name')
        name = norm_package_name(name)  # TODO: Do we want this or not?

        # Clean extras
        extras = r.group('extras')
        extras = [e.strip() for e in extras.split(',') if e] if extras else []

        # Clean constraints
        const = r.group('constraints')
        const = ''.join(c for c in const.split(' ') if c).strip()
        if const.startswith('(') and const.endswith(')'):
            # Remove parens
            const = const[1:-1]

    return PySpec(name=name, extras=extras, constraints=const, marker=marker, url=url)


def get_conda_anchor_files_and_records(python_records):
    """Return the anchor files for the conda records of python packages."""
    anchor_file_endings = ('.egg-info/PKG-INFO', '.dist-info/RECORD', '.egg-info')
    conda_python_packages = odict()

    for prefix_record in python_records:
        for fpath in prefix_record.files:
            if fpath.endswith(anchor_file_endings) and 'site-packages' in fpath:
                # Then 'fpath' is an anchor file
                conda_python_packages[fpath] = prefix_record

    return conda_python_packages


def get_site_packages_anchor_files(site_packages_path, site_packages_dir):
    """Get all the anchor files for the site packages directory."""
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
    """
    Return the egg info file path following an egg link.

    Return `None` if no egg-info is found or the path is no longer there.
    """
    egg_info_full_path = None

    with open(join(prefix_path, win_path_ok(egg_link_file))) as fh:
        # Only the first item of an egg-link file is used
        egg_link_contents = fh.readlines()[0].strip()

    egg_info_fnames = glob(join(egg_link_contents, "*.egg-info"))

    if egg_info_fnames:
        assert len(egg_info_fnames) == 1, (egg_link_file, egg_info_fnames)
        egg_info_full_path = join(egg_link_contents, egg_info_fnames[0])

        if isdir(egg_info_full_path):
            egg_info_full_path = join(egg_info_full_path, "PKG-INFO")

    return egg_info_full_path


def get_python_distribution_info(anchor_file, prefix_path):
    """
    For a given anchor file return the python distribution.

    Return `None` if the information was not found (can happen with egg-links).
    """
    if anchor_file.endswith('.egg-link'):
        sp_reference = None
        # This can be None in case the egg-info is no longer there
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

    pydist = None

    # An egg-link might reference a folder where egg-info is not available
    if dist_file is not None:
        try:
            pydist = dist_cls(dist_file)
        except Exception as error:
            print('ERROR', error)

    return pydist, sp_reference, package_type


def get_python_record(anchor_file, prefix_path, context):
    """
    Convert a python package defined by an anchor file (Metadata information)
    into a conda prefix record object.

    Return `None` if the python record cannot be created.
    """
    # TODO: ensure that this dist is actually the dist that matches conda-meta
    pydist, sp_reference, package_type = get_python_distribution_info(anchor_file, prefix_path)

    if pydist is None:
        return None

    pypi_name = pydist.norm_name
    conda_name = pypi_name_to_conda_name(pypi_name)

    # TODO: Handle packages with different names (graphviz vs python-graphviz)
    channel_name = 'pypi' if conda_name == pypi_name else 'pypi:' + pypi_name
    channel = Channel(channel_name)
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

    # TODO: This is currently adding additional conda dependencies for graphviz
    # only, but other packages need something similar. This info should (could)
    # be on the 'external_requirements', but that field is free form.
    dependencies = pydist.get_dependencies(context)
    extra_dependencies = PYPI_CONDA_DEPS.get(pypi_name, [])
    all_dependencies = list(dependencies) + extra_dependencies
    # print('{0} ({1})'.format(conda_name, pypi_name))
    # for dependency in sorted(all_dependencies):
    #     print('\t{}'.format(dependency))
    # print('\n')

    python_rec = PrefixRecord(
        package_type=package_type,
        name=conda_name,
        version=pydist.version,
        channel=channel,
        subdir='pypi',
        fn=sp_reference,
        build=build,
        build_number=0,
        paths_data=paths_data,
        depends=all_dependencies,
    )

    return python_rec


def get_python_records(anchor_files, prefix_path, python_version):
    """
    Process all anchor files and return a python record.

    This method evaluates the context needed for marker evaluation.
    """
    python_records = []
    context = update_marker_context(python_version)
    for anchor_file in sorted(anchor_files):
        python_record = get_python_record(anchor_file, prefix_path, context)
        if python_record:
            python_records.append(python_record)
    return python_records


# Marker helper funcs
# -----------------------------------------------------------------------------
def evaluate_marker(marker_expr, context, extras):
    """
    Temporal simplified (and unsafe) version of marker evaluation.
    """
    # _safer_eval is a POC to test the logic, but the micro language will no
    # longer be a subset of python so a specific lexer/parser is needed.
    # TODO: The version used in distlib is compact, we could vendor that part?
    # https://bitbucket.org/pypa/distlib/src/c9984aa2ecff1f9931cf4354d1abe5bdb415ea07/distlib/util.py
    def _safer_eval(expr, local_context):
        _local_context = frozendict(local_context.items())
        try:
            result = eval(expr, {"__builtins__": None}, _local_context)
        except Exception as e:
            result = True
            print(e)

        return result

    if marker_expr:
        # Extras may or may not be provided by the metadata, for every extra
        # we evaluate the markers to obtain *all* possible packages.
        # FIXME: This leads to including extra packages only used for doc
        # generation or test running. Names are not standard, but a cleanup
        # could be performed based on 'test', 'tests', 'doc' 'docs', 'doctest'
        # 'doctests' etc.
        if extras:
            marker_results = []
            for extra in extras:
                context.update({'extra': extra})
                # FIXME: Temporal eval to test functionality
                marker_result = _safer_eval(marker_expr, context)
                marker_results.append(marker_result)
            marker_result = any(marker_results)
        else:
            # FIXME: Temporal eval to test functionality
            marker_result = _safer_eval(marker_expr, context)
        # print(marker_expr, marker_result)
    else:
        marker_result = True

    return marker_result


def update_marker_context(python_version):
    """Update default marker context to include environment python version."""
    updated_context = DEFAULT_MARKER_CONTEXT.copy()
    context = {
        'python_full_version': python_version,
        'python_version': '.'.join(python_version.split('.')[:2]),
        'extra': '',
    }
    updated_context.update(context)
    return updated_context


def get_default_marker_context():
    """Return the default context dictionary to use when parsing markers."""

    def format_full_version(info):
        version = '%s.%s.%s' % (info.major, info.minor, info.micro)
        kind = info.releaselevel
        if kind != 'final':
            version += kind[0] + str(info.serial)
        return version

    if hasattr(sys, 'implementation'):
        implementation_version = format_full_version(sys.implementation.version)
        implementation_name = sys.implementation.name
    else:
        implementation_version = '0'
        implementation_name = ''

    result = {
        # See: https://www.python.org/dev/peps/pep-0508/#environment-markers
        'implementation_name': implementation_name,
        'implementation_version': implementation_version,
        'os_name': os.name,
        'platform_machine': platform.machine(),
        'platform_python_implementation': platform.python_implementation(),
        'platform_release': platform.release(),
        'platform_system': platform.system(),
        'platform_version': platform.version(),
        'python_full_version': platform.python_version(),
        'python_version': '.'.join(platform.python_version().split('.')[:2]),
        'sys_platform': sys.platform,
        # See: https://www.python.org/dev/peps/pep-0345/#environment-markers
        'os.name': os.name,
        'platform.python_implementation': platform.python_implementation(),
        'platform.version': platform.version(),
        'platform.machine': platform.machine(),
        'sys.platform': sys.platform,
    }
    return result


DEFAULT_MARKER_CONTEXT = get_default_marker_context()
