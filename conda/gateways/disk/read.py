# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import re
import shlex
from base64 import b64encode
from collections import namedtuple
from errno import ENOENT
from itertools import chain
from logging import getLogger
from os.path import islink, join

from ...base.constants import FileMode, PREFIX_PLACEHOLDER, UTF8

log = getLogger(__name__)


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


def collect_all_info_for_package(extracted_package_directory):
    info_dir = join(extracted_package_directory, 'info')

    # collect information from info directory
    files = tuple(ln for ln in (line.strip() for line in yield_lines(join(extracted_package_directory, 'info', 'files'))) if ln)

    # file system calls
    has_prefix_files = read_has_prefix(join(info_dir, 'has_prefix'))
    no_link = read_no_link(info_dir)
    soft_links = read_soft_links(extracted_package_directory, files)

    # simple processing
    MENU_RE = re.compile(r'^menu/.*\.json$', re.IGNORECASE)
    menu_files = tuple(f for f in files if MENU_RE.match(f))

    return files, has_prefix_files, no_link, soft_links, menu_files


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
    try:
        data = open(join(extracted_package_directory, 'info', 'icon.png'), 'rb').read()
        return b64encode(data).decode(UTF8)
    except IOError:
        pass
    return None
