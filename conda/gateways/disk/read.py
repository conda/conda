# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

from base64 import b64encode
from collections import namedtuple
from errno import ENOENT
from functools import partial
import hashlib
from itertools import chain
import json
from logging import getLogger
import os
from os.path import isdir, isfile, join  # noqa

from .link import islink, lexists  # noqa
from .create import TemporaryDirectory
from ...auxlib.collection import first
from ...auxlib.compat import shlex_split_unicode
from ...auxlib.ish import dals
from ...base.constants import PREFIX_PLACEHOLDER
from ...common.compat import open
from ...common.pkg_formats.python import (
    PythonDistribution, PythonEggInfoDistribution, PythonEggLinkDistribution,
    PythonInstalledDistribution,
)
from ...exceptions import CondaUpgradeError, CondaVerificationError, PathNotFoundError
from ...models.channel import Channel
from ...models.enums import FileMode, PackageType, PathType
from ...models.package_info import PackageInfo, PackageMetadata
from ...models.records import PathData, PathDataV1, PathsData, PrefixRecord

log = getLogger(__name__)

listdir = lambda d: list(entry.name for entry in os.scandir(d))  # noqa


def yield_lines(path):
    """Generator function for lines in file.  Empty generator if path does not exist.

    Args:
        path (str): path to file

    Returns:
        iterator: each line in file, not starting with '#'

    """
    try:
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                yield line
    except (IOError, OSError) as e:
        if e.errno == ENOENT:
            pass
        else:
            raise


def _digest_path(algo, path):
    if not isfile(path):
        raise PathNotFoundError(path)

    hasher = hashlib.new(algo)
    with open(path, "rb") as fh:
        for chunk in iter(partial(fh.read, 8192), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_md5sum(file_full_path):
    return _digest_path('md5', file_full_path)


def compute_sha256sum(file_full_path):
    return _digest_path('sha256', file_full_path)


# ####################################################
# functions supporting read_package_info()
# ####################################################

def read_package_info(record, package_cache_record):
    epd = package_cache_record.extracted_package_dir
    icondata = read_icondata(epd)
    package_metadata = read_package_metadata(epd)
    paths_data = read_paths_json(epd)

    return PackageInfo(
        extracted_package_dir=epd,
        package_tarball_full_path=package_cache_record.package_tarball_full_path,
        channel=Channel(record.schannel or record.channel),
        repodata_record=record,
        url=package_cache_record.url,

        icondata=icondata,
        package_metadata=package_metadata,
        paths_data=paths_data,
    )


def read_index_json(extracted_package_directory):
    with open(join(extracted_package_directory, 'info', 'index.json')) as fi:
        return json.load(fi)


def read_index_json_from_tarball(package_tarball_full_path):
    import conda_package_handling.api
    with TemporaryDirectory() as tmpdir:
        conda_package_handling.api.extract(package_tarball_full_path, tmpdir, 'info')
        with open(join(tmpdir, 'info', 'index.json')) as f:
            json_data = json.load(f)
    return json_data


def read_repodata_json(extracted_package_directory):
    with open(join(extracted_package_directory, 'info', 'repodata_record.json')) as fi:
        return json.load(fi)


def read_icondata(extracted_package_directory):
    icon_file_path = join(extracted_package_directory, 'info', 'icon.png')
    if isfile(icon_file_path):
        with open(icon_file_path, 'rb') as f:
            data = f.read()
        return b64encode(data).decode('utf-8')
    else:
        return None


def read_package_metadata(extracted_package_directory):
    def _paths():
        yield join(extracted_package_directory, 'info', 'link.json')
        yield join(extracted_package_directory, 'info', 'package_metadata.json')

    path = first(_paths(), key=isfile)
    if not path:
        return None
    else:
        with open(path, 'r') as f:
            data = json.loads(f.read())
            if data.get('package_metadata_version') != 1:
                raise CondaUpgradeError(dals("""
                The current version of conda is too old to install this package. (This version
                only supports link.json schema version 1.)  Please update conda to install
                this package.
                """))
        package_metadata = PackageMetadata(**data)
        return package_metadata


def read_paths_json(extracted_package_directory):
    info_dir = join(extracted_package_directory, 'info')
    paths_json_path = join(info_dir, 'paths.json')
    if isfile(paths_json_path):
        with open(paths_json_path) as paths_json:
            data = json.load(paths_json)
        if data.get('paths_version') != 1:
            raise CondaUpgradeError(dals("""
            The current version of conda is too old to install this package. (This version
            only supports paths.json schema version 1.)  Please update conda to install
            this package."""))
        paths_data = PathsData(
            paths_version=1,
            paths=(PathDataV1(**f) for f in data['paths']),
        )
    else:
        has_prefix_files = read_has_prefix(join(info_dir, 'has_prefix'))
        no_link = read_no_link(info_dir)

        def read_files_file():
            files_path = join(info_dir, 'files')
            for f in (ln for ln in (line.strip() for line in yield_lines(files_path)) if ln):
                path_info = {"_path": f}
                if f in has_prefix_files.keys():
                    path_info["prefix_placeholder"] = has_prefix_files[f][0]
                    path_info["file_mode"] = has_prefix_files[f][1]
                if f in no_link:
                    path_info["no_link"] = True
                if islink(join(extracted_package_directory, f)):
                    path_info["path_type"] = PathType.softlink
                else:
                    path_info["path_type"] = PathType.hardlink
                yield PathData(**path_info)

        paths = tuple(read_files_file())
        paths_data = PathsData(
            paths_version=0,
            paths=paths,
        )
    return paths_data


def read_has_prefix(path):
    """
    reads `has_prefix` file and return dict mapping filepaths to tuples(placeholder, FileMode)

    A line in `has_prefix` contains one of
      * filepath
      * placeholder mode filepath

    mode values are one of
      * text
      * binary
    """
    ParseResult = namedtuple('ParseResult', ('placeholder', 'filemode', 'filepath'))

    def parse_line(line):
        # placeholder, filemode, filepath
        parts = tuple(x.strip('"\'') for x in shlex_split_unicode(line, posix=False))
        if len(parts) == 1:
            return ParseResult(PREFIX_PLACEHOLDER, FileMode.text, parts[0])
        elif len(parts) == 3:
            return ParseResult(parts[0], FileMode(parts[1]), parts[2])
        else:
            raise CondaVerificationError("Invalid has_prefix file at path: %s" % path)

    parsed_lines = (parse_line(line) for line in yield_lines(path))
    return {pr.filepath: (pr.placeholder, pr.filemode) for pr in parsed_lines}


def read_no_link(info_dir):
    return set(chain(yield_lines(join(info_dir, 'no_link')),
                     yield_lines(join(info_dir, 'no_softlink'))))


def read_soft_links(extracted_package_directory, files):
    return tuple(f for f in files if islink(join(extracted_package_directory, f)))


def read_python_record(prefix_path, anchor_file, python_version):
    """
    Convert a python package defined by an anchor file (Metadata information)
    into a conda prefix record object.
    """
    pydist = PythonDistribution.init(prefix_path, anchor_file, python_version)
    depends, constrains = pydist.get_conda_dependencies()

    if isinstance(pydist, PythonInstalledDistribution):
        channel = Channel("pypi")
        build = "pypi_0"
        package_type = PackageType.VIRTUAL_PYTHON_WHEEL

        paths_tups = pydist.get_paths()
        paths_data = PathsData(paths_version=1, paths=(
            PathDataV1(
                _path=path, path_type=PathType.hardlink, sha256=checksum, size_in_bytes=size
            ) for (path, checksum, size) in paths_tups
        ))
        files = tuple(p[0] for p in paths_tups)

    elif isinstance(pydist, PythonEggLinkDistribution):
        channel = Channel("<develop>")
        build = "dev_0"
        package_type = PackageType.VIRTUAL_PYTHON_EGG_LINK

        paths_data, files = PathsData(paths_version=1, paths=()), ()

    elif isinstance(pydist, PythonEggInfoDistribution):
        channel = Channel("pypi")
        build = "pypi_0"
        if pydist.is_manageable:
            package_type = PackageType.VIRTUAL_PYTHON_EGG_MANAGEABLE

            paths_tups = pydist.get_paths()
            files = tuple(p[0] for p in paths_tups)
            paths_data = PathsData(paths_version=1, paths=(
                PathData(_path=path, path_type=PathType.hardlink) for path in files
            ))
        else:
            package_type = PackageType.VIRTUAL_PYTHON_EGG_UNMANAGEABLE
            paths_data, files = PathsData(paths_version=1, paths=()), ()

    else:
        raise NotImplementedError()

    return PrefixRecord(
        package_type=package_type,
        name=pydist.conda_name,
        version=pydist.version,
        channel=channel,
        subdir="pypi",
        fn=pydist.sp_reference,
        build=build,
        build_number=0,
        paths_data=paths_data,
        files=files,
        depends=depends,
        constrains=constrains,
    )
