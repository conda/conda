# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals
from logging import getLogger

log = getLogger(__name__)


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
