# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from conda.core.portability import SHEBANG_REGEX
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
        pass
