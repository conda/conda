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
from os import X_OK, access, listdir
from os.path import isdir, isfile, join, lexists
import shlex

from .link import islink
from ..._vendor.auxlib.collection import first
from ..._vendor.auxlib.ish import dals
from ...base.constants import PREFIX_PLACEHOLDER
from ...common.compat import on_win
from ...exceptions import CondaFileNotFoundError, CondaUpgradeError
from ...models.channel import Channel
from ...models.enums import FileMode, PathType
from ...models.index_record import IndexRecord
from ...models.package_info import PackageInfo, PackageMetadata, PathData, PathDataV1, PathsData

log = getLogger(__name__)

listdir = listdir
lexists, isdir, isfile, islink = lexists, isdir, isfile, islink


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
            raise StopIteration
        else:
            raise


def compute_md5sum(file_full_path):
    if not isfile(file_full_path):
        raise CondaFileNotFoundError(file_full_path)

    hash_md5 = hashlib.md5()
    with open(file_full_path, "rb") as fh:
        for chunk in iter(partial(fh.read, 4096), b''):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def is_exe(path):
    return isfile(path) and (access(path, X_OK) or (on_win and path.endswith(('.exe', '.bat'))))


def find_first_existing(*globs):
    for g in globs:
        for path in glob(g):
            if lexists(path):
                return path
    return None


# ####################################################
# functions supporting read_package_info()
# ####################################################

def read_package_info(record, extracted_package_directory):
    index_json_record = read_index_json(extracted_package_directory)
    icondata = read_icondata(extracted_package_directory)
    package_metadata = read_package_metadata(extracted_package_directory)
    paths_data = read_paths_json(extracted_package_directory)

    return PackageInfo(
        extracted_package_dir=extracted_package_directory,
        channel=Channel(record.schannel or record.channel),
        repodata_record=record,
        url=record.url,

        index_json_record=index_json_record,
        icondata=icondata,
        package_metadata=package_metadata,
        paths_data=paths_data,
    )


def read_index_json(extracted_package_directory):
    with open(join(extracted_package_directory, 'info', 'index.json')) as fi:
        record = IndexRecord(**json.load(fi))  # TODO: change to LinkedPackageData
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
            package_metadata = PackageMetadata(**json.loads(f.read()))
            if package_metadata.package_metadata_version != 1:
                raise CondaUpgradeError(dals("""
                The current version of conda is too old to install this package. (This version
                only supports link.json schema version 1.)  Please update conda to install
                this package."""))
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

        paths_data = PathsData(
            paths_version=0,
            paths=read_files_file(),
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
            raise RuntimeError("Invalid has_prefix file at path: %s" % path)

    parsed_lines = (parse_line(line) for line in yield_lines(path))
    return {pr.filepath: (pr.placeholder, pr.filemode) for pr in parsed_lines}


def read_files(path):
    ParseResult = namedtuple('ParseResult', ('filepath', 'hash', 'bytes', 'type'))

    def parse_line(line):
        # 'filepath', 'hash', 'bytes', 'type'
        parts = line.split(',')
        if len(parts) == 4:
            return ParseResult(*parts)
        elif len(parts) == 1:
            return ParseResult(parts[0], None, None, None)
        else:
            raise RuntimeError("Invalid files at path: %s" % path)

    return tuple(parse_line(line) for line in yield_lines(path))


def read_no_link(info_dir):
    return set(chain(yield_lines(join(info_dir, 'no_link')),
                     yield_lines(join(info_dir, 'no_softlink'))))


def read_soft_links(extracted_package_directory, files):
    return tuple(f for f in files if islink(join(extracted_package_directory, f)))


def get_json_content(path_to_json):
    if isfile(path_to_json):
        try:
            with open(path_to_json, "r") as f:
                json_content = json.load(f)
        except json.decoder.JSONDecodeError:
            json_content = {}
    else:
        json_content = {}
    return json_content
