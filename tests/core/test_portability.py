# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from conda.core.portability import SHEBANG_REGEX, replace_long_shebang
from conda.models.enums import FileMode
from logging import getLogger
import re
from unittest import TestCase

log = getLogger(__name__)


class ReplaceShebangTests(TestCase):

    def test_shebang_regex_matches(self):
        shebang = b"#!/simple/shebang"
        match = re.match(SHEBANG_REGEX, shebang, re.MULTILINE)
        assert match.groups() == (b'#!/simple/shebang',
                                  b'/simple/shebang',
                                  b'')

        # two lines
        shebang = b"#!/simple/shebang\nsecond line\n"
        match = re.match(SHEBANG_REGEX, shebang, re.MULTILINE)
        assert match.groups() == (b'#!/simple/shebang',
                                  b'/simple/shebang',
                                  b'')

        # with spaces
        shebang = b"#!/simple/shebang\nsecond line\n"
        match = re.match(SHEBANG_REGEX, shebang, re.MULTILINE)
        assert match.groups() == (b'#!/simple/shebang',
                                  b'/simple/shebang',
                                  b'')

        # with spaces
        shebang = b"#!    /simple/shebang\nsecond line\n"
        match = re.match(SHEBANG_REGEX, shebang, re.MULTILINE)
        assert match.groups() == (b'#!    /simple/shebang',
                                  b'/simple/shebang',
                                  b'')

        # with escaped spaces and flags
        shebang = b"#!/simple/shebang/escaped\\ space --and --flags -x\nsecond line\n"
        match = re.match(SHEBANG_REGEX, shebang, re.MULTILINE)
        assert match.groups() == (b'#!/simple/shebang/escaped\\ space --and --flags -x',
                                  b'/simple/shebang/escaped\\ space',
                                  b' --and --flags -x')


    def test_replace_long_shebang(self):
        content_line = b"content line " * 5

        # simple shebang no replacement
        shebang = b"#!/simple/shebang/escaped\\ space --and --flags -x"
        data = b'\n'.join((shebang, content_line, content_line, content_line))
        new_data = replace_long_shebang(FileMode.text, data)
        assert data == new_data

        # long shebang with truncation
        #   executable name is 'escaped space'
        shebang = b"#!/" + b"shebang/" * 20 + b"python" + b" --and --flags -x"
        assert len(shebang) > 127
        data = b'\n'.join((shebang, content_line, content_line, content_line))
        new_data = replace_long_shebang(FileMode.text, data)
        new_shebang = b"#!/usr/bin/env python --and --flags -x"
        new_expected_data = b'\n'.join((new_shebang, content_line, content_line, content_line))
        assert new_expected_data == new_data

        # long shebang with truncation
        #   executable name is 'escaped space'
        shebang = b"#!/" + b"shebang/" * 20 + b"escaped\\ space" + b" --and --flags -x"
        assert len(shebang) > 127
        data = b'\n'.join((shebang, content_line, content_line, content_line))
        new_data = replace_long_shebang(FileMode.text, data)
        new_shebang = b"#!/usr/bin/env escaped\\ space --and --flags -x"
        new_expected_data = b'\n'.join((new_shebang, content_line, content_line, content_line))
        assert new_expected_data == new_data
