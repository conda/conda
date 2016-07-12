# -*- coding: utf-8 -*-
"""``jsonutils`` aims to provide various helpers for working with
JSON. Currently it focuses on providing a reliable and intuitive means
of working with `JSON Lines`_-formatted files.

.. _JSON Lines: http://jsonlines.org/

"""

from __future__ import print_function

import os
import json


DEFAULT_BLOCKSIZE = 4096

# reverse iter lines algorithm:
#
#  - if it ends in a newline, add an empty string to the line list
#  - if there's one item, then prepend it to the buffer, continue
#  - if there's more than one item, pop the last item and prepend it
#    to the buffer, yielding it
#  - yield all remaining items in reverse, except for the first
#  - first item becomes the new buffer
#
#  - when the outer loop completes, yield the buffer


__all__ = ['JSONLIterator', 'reverse_iter_lines']


def reverse_iter_lines(file_obj, blocksize=DEFAULT_BLOCKSIZE, preseek=True):
    """Returns an iterator over the lines from a file object, in
    reverse order, i.e., last line first, first line last. Uses the
    :meth:`file.seek` method of file objects, and is tested compatible with
    :class:`file` objects, as well as :class:`StringIO.StringIO`.

    Args:
        file_obj (file): An open file object. Note that ``reverse_iter_lines``
            mutably reads from the file and other functions should not mutably
            interact with the file object.
        blocksize (int): The block size to pass to :meth:`file.read()`
        preseek (bool): Tells the function whether or not to automatically
            seek to the end of the file. Defaults to ``True``.
            ``preseek=False`` is useful in cases when the
            file cursor is already in position, either at the end of
            the file or in the middle for relative reverse line
            generation.
    """
    if preseek:
        file_obj.seek(0, os.SEEK_END)
    cur_pos = file_obj.tell()
    buff = ''
    while 0 < cur_pos:
        read_size = min(blocksize, cur_pos)
        cur_pos -= read_size
        file_obj.seek(cur_pos, os.SEEK_SET)
        cur = file_obj.read(read_size)
        lines = cur.splitlines()
        if cur[-1] == '\n':
            lines.append('')
        if len(lines) == 1:
            buff = lines[0] + buff
            continue
        last = lines.pop()
        yield last + buff
        for line in lines[:0:-1]:
            yield line
        buff = lines[0]
    if buff:
        # TODO: test this, does an empty buffer always mean don't yield?
        yield buff


"""
TODO: allow passthroughs for:

json.load(fp[, encoding[, cls[, object_hook[, parse_float[, parse_int[, parse_constant[, object_pairs_hook[, **kw]]]]]]]])
"""


class JSONLIterator(object):
    """The ``JSONLIterator`` is used to iterate over JSON-encoded objects
    stored in the `JSON Lines format`_ (one object per line).

    Most notably it has the ability to efficiently read from the
    bottom of files, making it very effective for reading in simple
    append-only JSONL use cases. It also has the ability to start from
    anywhere in the file and ignore corrupted lines.

    Args:
        file_obj (file): An open file object.
        ignore_errors (bool): Whether to skip over lines that raise an error on
            deserialization (:func:`json.loads`).
        reverse (bool): Controls the direction of the iteration.
            Defaults to ``False``. If set to ``True`` and *rel_seek*
            is unset, seeks to the end of the file before iteration
            begins.
        rel_seek (float): Used to preseek the start position of
            iteration. Set to 0.0 for the start of the file, 1.0 for the
            end, and anything in between.

    .. _JSON Lines format: http://jsonlines.org/
    """
    def __init__(self, file_obj,
                 ignore_errors=False, reverse=False, rel_seek=None):
        self._reverse = bool(reverse)
        self._file_obj = file_obj
        self.ignore_errors = ignore_errors

        if rel_seek is None:
            if reverse:
                rel_seek = 1.0
        elif not -1.0 < rel_seek < 1.0:
            raise ValueError("'rel_seek' expected a float between"
                             " -1.0 and 1.0, not %r" % rel_seek)
        elif rel_seek < 0:
            rel_seek = 1.0 - rel_seek
        self._rel_seek = rel_seek
        self._blocksize = 4096
        if rel_seek is not None:
            self._init_rel_seek()
        if self._reverse:
            self._line_iter = reverse_iter_lines(self._file_obj,
                                                 blocksize=self._blocksize,
                                                 preseek=False)
        else:
            self._line_iter = iter(self._file_obj)

    @property
    def cur_byte_pos(self):
        "A property representing where in the file the iterator is reading."
        return self._file_obj.tell()

    def _align_to_newline(self):
        "Aligns the file object's position to the next newline."
        fo, bsize = self._file_obj, self._blocksize
        cur, total_read = '', 0
        cur_pos = fo.tell()
        while '\n' not in cur:
            cur = fo.read(bsize)
            total_read += bsize
        try:
            newline_offset = cur.index('\n') + total_read - bsize
        except ValueError:
            raise  # TODO: seek to end?
        fo.seek(cur_pos + newline_offset)

    def _init_rel_seek(self):
        "Sets the file object's position to the relative location set above."
        rs, fo = self._rel_seek, self._file_obj
        if rs == 0.0:
            fo.seek(0, os.SEEK_SET)
        else:
            fo.seek(0, os.SEEK_END)
            size = fo.tell()
            if rs == 1.0:
                self._cur_pos = size
            else:
                target = int(size * rs)
                fo.seek(target, os.SEEK_SET)
                self._align_to_newline()
                self._cur_pos = fo.tell()

    def __iter__(self):
        return self

    def next(self):
        """Yields one :class:`dict` loaded with :func:`json.loads`, advancing
        the file object by one line. Raises :exc:`StopIteration` upon reaching
        the end of the file (or beginning, if ``reverse`` was set to ``True``.
        """
        while 1:
            line = next(self._line_iter).lstrip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                if not self.ignore_errors:
                    raise
                continue
            return obj

    __next__ = next


if __name__ == '__main__':
    def _main():
        import sys
        if '-h' in sys.argv or '--help' in sys.argv:
            print('loads one or more JSON Line files for basic validation.')
            return
        verbose = False
        if '-v' in sys.argv or '--verbose' in sys.argv:
            verbose = True
        file_count, obj_count = 0, 0
        filenames = sys.argv[1:]
        for filename in filenames:
            if filename in ('-h', '--help', '-v', '--verbose'):
                continue
            file_count += 1
            with open(filename, 'rb') as file_obj:
                iterator = JSONLIterator(file_obj)
                cur_obj_count = 0
                while 1:
                    try:
                        next(iterator)
                    except ValueError:
                        print('error reading object #%s around byte %s in %s'
                              % (cur_obj_count + 1, iterator.cur_byte_pos, filename))
                        return
                    except StopIteration:
                        break
                    obj_count += 1
                    cur_obj_count += 1
                    if verbose and obj_count and obj_count % 100 == 0:
                        sys.stdout.write('.')
                        if obj_count % 10000:
                            sys.stdout.write('%s\n' % obj_count)
        if verbose:
            print('files checked: %s' % file_count)
            print('objects loaded: %s' % obj_count)
        return

    _main()
