# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from base64 import b64encode
from collections import namedtuple
from conda.common.compat import on_win
from errno import ENOENT
from functools import partial
import hashlib
from itertools import chain
import json
from logging import getLogger
from os import listdir, access, X_OK
from os.path import exists, isdir, isfile, islink, join
import shlex

from ..._vendor.auxlib.ish import dals
from ...base.constants import PREFIX_PLACEHOLDER
from ...exceptions import CondaFileNotFoundError, CondaUpgradeError
from ...models.channel import Channel
from ...models.enums import FileMode
from ...models.package_info import PackageInfo, PathInfo, PathInfoV1
from conda.models.enums import PathType
from ...models.record import Record

log = getLogger(__name__)

listdir = listdir
exists, isdir, isfile, islink = exists, isdir, isfile, islink


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


# # attributes external to the package tarball
# extracted_package_dir = StringField()
# channel = ComposableField(Channel)
# repodata_record = ComposableField(Record)
# url = StringField()
#
# # attributes within the package tarball
# paths_version = IntegerField()
# paths = ListField(PathInfo)
# index_json_record = ComposableField(Record)
# icondata = StringField(required=False, nullable=True)
# noarch = ComposableField(NoarchInfo, required=False,
#                          nullable=True)  # TODO: this isn't noarch anymore; package_metadata.json  # NOQA


def collect_all_info_for_package(record, extracted_package_directory):
    info_dir = join(extracted_package_directory, 'info')

    files_path = join(extracted_package_directory, 'info', 'files')
    file_json_path = join(extracted_package_directory, 'info', 'paths.json')

    if isfile(file_json_path):
        with open(file_json_path) as file_json:
            data = json.load(file_json)
        if data.get('paths_version') != 1:
            raise CondaUpgradeError(dals("""
            The current version of conda is too old to install this package. (This version
            only supports paths.json schema version 1.)  Please update conda to install
            this package."""))

        paths = (PathInfoV1(**f) for f in data['paths'])
        index_json_record = read_index_json(extracted_package_directory)
        noarch = read_noarch(extracted_package_directory)
        icondata = read_icondata(extracted_package_directory)
        return PackageInfo(extracted_package_dir=extracted_package_directory,
                           channel=Channel(record.schannel or record.channel),
                           repodata_record=record,
                           url=record.url,
                           paths_version=1,
                           paths=paths,
                           index_json_record=index_json_record,
                           icondata=icondata,
                           noarch=noarch)
    else:
        files = tuple(ln for ln in (line.strip() for line in yield_lines(files_path)) if ln)

        has_prefix_files = read_has_prefix(join(info_dir, 'has_prefix'))
        no_link = read_no_link(info_dir)

        path_info_files = []
        for f in files:
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
            path_info_files.append(PathInfo(**path_info))

        index_json_record = read_index_json(extracted_package_directory)
        icondata = read_icondata(extracted_package_directory)
        noarch = read_noarch(extracted_package_directory)
        return PackageInfo(extracted_package_dir=extracted_package_directory,
                           channel=Channel(record.schannel or record.channel),
                           repodata_record=record,
                           url=record.url,
                           paths_version=0,
                           paths=path_info_files,
                           index_json_record=index_json_record,
                           icondata=icondata,
                           noarch=noarch)


def read_noarch(extracted_package_directory):
    noarch_path = join(extracted_package_directory, 'info', 'noarch.json')
    if isfile(noarch_path):
        with open(noarch_path, 'r') as f:
            return json.loads(f.read())
    else:
        return None


def read_index_json(extracted_package_directory):
    with open(join(extracted_package_directory, 'info', 'index.json')) as fi:
        record = Record(**json.load(fi))  # TODO: change to LinkedPackageData
    return record


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


def read_icondata(extracted_package_directory):
    icon_file_path = join(extracted_package_directory, 'info', 'icon.png')
    if isfile(icon_file_path):
        with open(icon_file_path, 'rb') as f:
            data = f.read()
        return b64encode(data).decode('utf-8')
    else:
        return None


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
