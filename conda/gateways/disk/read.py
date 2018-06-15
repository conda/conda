# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from base64 import b64encode
from collections import namedtuple
from errno import ENOENT
from functools import partial
from glob import glob
import hashlib
from itertools import chain
import json
from logging import getLogger
from os import listdir
from os.path import isdir, isfile, join
import shlex
import tarfile

from .link import islink, lexists
from ..._vendor.auxlib.collection import first
from ..._vendor.auxlib.ish import dals
from ...base.constants import PREFIX_PLACEHOLDER
from ...common.compat import ensure_text_type, open
from ...exceptions import CondaUpgradeError, CondaVerificationError, PathNotFoundError
from ...models.channel import Channel
from ...models.enums import FileMode, PathType
from ...models.records import IndexJsonRecord, PackageRecord, PathData, PathDataV1, PathsData
from ...models.package_info import PackageInfo, PackageMetadata

log = getLogger(__name__)

listdir = listdir
lexists, isdir, isfile = lexists, isdir, isfile


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


def find_first_existing(*globs):
    for g in globs:
        for path in glob(g):
            if lexists(path):
                return path
    return None


# ####################################################
# functions supporting read_package_info()
# ####################################################

def read_package_info(record, package_cache_record):
    epd = package_cache_record.extracted_package_dir
    index_json_record = read_index_json(epd)
    icondata = read_icondata(epd)
    package_metadata = read_package_metadata(epd)
    paths_data = read_paths_json(epd)

    return PackageInfo(
        extracted_package_dir=epd,
        channel=Channel(record.schannel or record.channel),
        repodata_record=record,
        url=package_cache_record.url,

        index_json_record=index_json_record,
        icondata=icondata,
        package_metadata=package_metadata,
        paths_data=paths_data,
    )


def read_index_json(extracted_package_directory):
    with open(join(extracted_package_directory, 'info', 'index.json')) as fi:
        record = IndexJsonRecord(**json.load(fi))
    return record


def read_index_json_from_tarball(package_tarball_full_path):
    with tarfile.open(package_tarball_full_path) as tf:
        contents = tf.extractfile('info/index.json').read()
        return IndexJsonRecord(**json.loads(ensure_text_type(contents)))


def read_repodata_json(extracted_package_directory):
    with open(join(extracted_package_directory, 'info', 'repodata_record.json')) as fi:
        record = PackageRecord(**json.load(fi))
    return record


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
        parts = tuple(x.strip('"\'') for x in shlex.split(line, posix=False))
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
