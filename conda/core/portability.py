# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
from os.path import realpath
import re
import struct

from ..base.constants import PREFIX_PLACEHOLDER, UTF8
from ..exceptions import CondaRuntimeError
from ..gateways.disk.update import CancelOperation, update_file_as_binary
from ..models.enums import FileMode
from ..utils import on_win

log = getLogger(__name__)

SHEBANG_REGEX = re.compile(br'^(#!((?:\\ |[^ \n\r])+)(.*))')


class _PaddingError(Exception):
    pass


def update_prefix(path, new_prefix, placeholder=PREFIX_PLACEHOLDER, mode=FileMode.text):
    if on_win and mode == FileMode.text:
        # force all prefix replacements to forward slashes to simplify need to escape backslashes
        # replace with unix-style path separators
        new_prefix = new_prefix.replace('\\', '/')

    def _update_prefix(original_data):
        data = replace_prefix(mode, original_data, placeholder, new_prefix)
        if not on_win:
            data = replace_long_shebang(mode, data)

        if data == original_data:
            raise CancelOperation()

        if len(data) != len(original_data):
            message = ("Attempt failed to replace data of length '%(new_data_length)d' with "
                       "data of length '%(original_data_length)d'.\n"
                       "  path: %(path)s\n"
                       "  new prefix: %(new_prefix)s\n"
                       "  placeholder: %(placeholder)s\n"
                       "  file mode: %(mode)s\n"
                       % {'new_data_length': len(data),
                          'original_data_length': len(original_data),
                          'path': path,
                          'new_prefix': new_prefix,
                          'placeholder': placeholder,
                          'mode': mode,
                          })
            raise CondaRuntimeError(message)

        return data

    update_file_as_binary(realpath(path), _update_prefix)


def binary_replace(data, a, b):
    """
    Perform a binary replacement of `data`, where the placeholder `a` is
    replaced with `b` and the remaining string is padded with null characters.
    All input arguments are expected to be bytes objects.
    """
    if on_win:
        if has_pyzzer_entry_point(data):
            return replace_pyzzer_entry_point_shebang(data, a, b)
        # currently we should skip replacement on Windows for things we don't understand.
        else:
            return data

    def replace(match):
        occurances = match.group().count(a)
        padding = (len(a) - len(b)) * occurances
        if padding < 0:
            raise _PaddingError
        return match.group().replace(a, b) + b'\0' * padding

    original_data_len = len(data)
    pat = re.compile(re.escape(a) + b'([^\0]*?)\0')
    data = pat.sub(replace, data)
    assert len(data) == original_data_len

    return data


def has_pyzzer_entry_point(data):
    pos = data.rfind(b'PK\x05\x06')
    return pos >= 0


def replace_pyzzer_entry_point_shebang(all_data, placeholder, new_prefix):
    """Code adapted from pyzzer.  This is meant to deal with entry point exe's created by distlib,
    which consist of a launcher, then a shebang, then a zip archive of the entry point code to run.
    We need to change the shebang.
    https://bitbucket.org/vinay.sajip/pyzzer/src/5d5740cb04308f067d5844a56fbe91e7a27efccc/pyzzer/__init__.py?at=default&fileviewer=file-view-default#__init__.py-112  # NOQA
    """
    # Copyright (c) 2013 Vinay Sajip.
    #
    # Permission is hereby granted, free of charge, to any person obtaining a copy
    # of this software and associated documentation files (the "Software"), to deal
    # in the Software without restriction, including without limitation the rights
    # to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    # copies of the Software, and to permit persons to whom the Software is
    # furnished to do so, subject to the following conditions:
    #
    # The above copyright notice and this permission notice shall be included in
    # all copies or substantial portions of the Software.
    #
    # THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    # IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    # FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    # AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    # LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    # OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
    # THE SOFTWARE.
    launcher = shebang = None
    pos = all_data.rfind(b'PK\x05\x06')
    if pos >= 0:
        end_cdr = all_data[pos + 12:pos + 20]
        cdr_size, cdr_offset = struct.unpack('<LL', end_cdr)
        arc_pos = pos - cdr_size - cdr_offset
        data = all_data[arc_pos:]
        if arc_pos > 0:
            pos = all_data.rfind(b'#!', 0, arc_pos)
            if pos >= 0:
                shebang = all_data[pos:arc_pos]
                if pos > 0:
                    launcher = all_data[:pos]

        if data and shebang and launcher:
            if hasattr(placeholder, 'encode'):
                placeholder = placeholder.encode('utf-8')
            if hasattr(new_prefix, 'encode'):
                new_prefix = new_prefix.encode('utf-8')
            shebang = shebang.replace(placeholder, new_prefix)
            all_data = b"".join([launcher, shebang, data])
    return all_data


def replace_prefix(mode, data, placeholder, new_prefix):
    if mode == FileMode.text:
        data = data.replace(placeholder.encode(UTF8), new_prefix.encode(UTF8))
    elif mode == FileMode.binary:
        data = binary_replace(data, placeholder.encode(UTF8), new_prefix.encode(UTF8))
    else:
        raise RuntimeError("Invalid mode: %r" % mode)
    return data


def replace_long_shebang(mode, data):
    if mode == FileMode.text:
        shebang_match = SHEBANG_REGEX.match(data)
        if shebang_match:
            whole_shebang, executable, options = shebang_match.groups()
            if len(whole_shebang) > 127:
                executable_name = executable.decode(UTF8).split('/')[-1]
                new_shebang = '#!/usr/bin/env %s%s' % (executable_name, options.decode(UTF8))
                data = data.replace(whole_shebang, new_shebang.encode(UTF8))
    else:
        # TODO: binary shebangs exist; figure this out in the future if text works well
        log.debug("TODO: binary shebangs exist; figure this out in the future if text works well")
    return data
