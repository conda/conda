# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import re
from logging import getLogger
from unittest import TestCase

import pytest

from conda.base.constants import PREFIX_PLACEHOLDER, on_win
from conda.core.portability import SHEBANG_REGEX, replace_long_shebang, update_prefix
from conda.models.enums import FileMode

log = getLogger(__name__)


class ReplaceShebangTests(TestCase):
    content_line = b"content line " * 5

    def test_shebang_regex_matches(self):
        shebang = b"#!/simple/shebang"
        match = re.match(SHEBANG_REGEX, shebang, re.MULTILINE)
        assert match.groups() == (b"#!/simple/shebang", b"/simple/shebang", b"")

        # two lines
        shebang = b"#!/simple/shebang\nsecond line\n"
        match = re.match(SHEBANG_REGEX, shebang, re.MULTILINE)
        assert match.groups() == (b"#!/simple/shebang", b"/simple/shebang", b"")

        # with spaces
        shebang = b"#!/simple/shebang\nsecond line\n"
        match = re.match(SHEBANG_REGEX, shebang, re.MULTILINE)
        assert match.groups() == (b"#!/simple/shebang", b"/simple/shebang", b"")

        # with spaces
        shebang = b"#!    /simple/shebang\nsecond line\n"
        match = re.match(SHEBANG_REGEX, shebang, re.MULTILINE)
        assert match.groups() == (b"#!    /simple/shebang", b"/simple/shebang", b"")

        # with escaped spaces and flags
        shebang = b"#!/simple/shebang/escaped\\ space --and --flags -x\nsecond line\n"
        match = re.match(SHEBANG_REGEX, shebang, re.MULTILINE)
        assert match.groups() == (
            b"#!/simple/shebang/escaped\\ space --and --flags -x",
            b"/simple/shebang/escaped\\ space",
            b" --and --flags -x",
        )

    def test_replace_long_shebang_simple_no_replacement(self):
        # simple shebang no replacement
        shebang = b"#!/simple/shebang/escaped\\ space --and --flags -x"
        data = b"\n".join((shebang, self.content_line, self.content_line, self.content_line))
        new_data = replace_long_shebang(FileMode.text, data)
        assert data == new_data

    def test_replace_long_shebang_with_truncation_python(self):
        # long shebang with truncation
        #   executable name is 'python'
        shebang = b"#!/" + b"shebang/" * 20 + b"python" + b" --and --flags -x"
        assert len(shebang) > 127
        data = b"\n".join((shebang, self.content_line, self.content_line, self.content_line))
        new_data = replace_long_shebang(FileMode.text, data)
        new_shebang = b"#!/usr/bin/env python --and --flags -x"
        new_expected_data = b"\n".join(
            (new_shebang, self.content_line, self.content_line, self.content_line)
        )
        assert new_expected_data == new_data

    def test_replace_long_shebang_with_truncation_escaped_space(self):
        # long shebang with truncation
        #   executable name is 'escaped space'
        shebang = b"#!/" + b"shebang/" * 20 + b"escaped\\ space" + b" --and --flags -x"
        assert len(shebang) > 127
        data = b"\n".join((shebang, self.content_line, self.content_line, self.content_line))
        new_data = replace_long_shebang(FileMode.text, data)
        new_shebang = b"#!/usr/bin/env escaped\\ space --and --flags -x"
        new_expected_data = b"\n".join(
            (new_shebang, self.content_line, self.content_line, self.content_line)
        )
        assert new_expected_data == new_data

    def test_replace_normal_shebang_spaces_in_prefix_python(self):
        # normal shebang with escaped spaces in prefix
        #   executable name is 'python'
        shebang = b"#!/she\\ bang/python --and --flags -x"
        assert len(shebang) < 127
        data = b"\n".join((shebang, self.content_line, self.content_line, self.content_line))
        new_data = replace_long_shebang(FileMode.text, data)
        new_shebang = b"#!/usr/bin/env python --and --flags -x"
        new_expected_data = b"\n".join(
            (new_shebang, self.content_line, self.content_line, self.content_line)
        )
        assert new_expected_data == new_data

    def test_replace_normal_shebang_spaces_in_prefix_escaped_space(self):
        # normal shebang with escaped spaces in prefix
        #   executable name is 'escaped space'
        shebang = b"#!/she\\ bang/escaped\\ space --and --flags -x"
        assert len(shebang) < 127
        data = b"\n".join((shebang, self.content_line, self.content_line, self.content_line))
        new_data = replace_long_shebang(FileMode.text, data)
        new_shebang = b"#!/usr/bin/env escaped\\ space --and --flags -x"
        new_expected_data = b"\n".join(
            (new_shebang, self.content_line, self.content_line, self.content_line)
        )
        assert new_expected_data == new_data

    def test_replace_long_shebang_spaces_in_prefix(self):
        # long shebang with escaped spaces in prefix
        shebang = b"#!/" + b"she\\ bang/" * 20 + b"python --and --flags -x"
        assert len(shebang) > 127
        data = b"\n".join((shebang, self.content_line, self.content_line, self.content_line))
        new_data = replace_long_shebang(FileMode.text, data)
        new_shebang = b"#!/usr/bin/env python --and --flags -x"
        new_expected_data = b"\n".join(
            (new_shebang, self.content_line, self.content_line, self.content_line)
        )
        assert new_expected_data == new_data


@pytest.mark.skipif(on_win, reason="Shebang replacement only needed on Unix systems")
def test_escaped_prefix_replaced_only_shebang(tmp_path):
    """
    In order to deal with spaces and shebangs, we first escape the spaces
    in the shebang and then post-process it with the /usr/bin/env trick.

    However, we must NOT escape other occurrences of the prefix in the file.
    """
    new_prefix = "/a/path/with/s p a c e s"
    contents = f"""#!{PREFIX_PLACEHOLDER}/python
data = "{PREFIX_PLACEHOLDER}"
"""
    script = os.path.join(tmp_path, "executable_script")
    with open(script, "wb") as f:
        f.write(contents.encode("utf-8"))
    update_prefix(path=script, new_prefix=new_prefix, placeholder=PREFIX_PLACEHOLDER)

    with open(script) as f:
        for i, line in enumerate(f):
            if i == 0:
                assert line.startswith("#!/usr/bin/env python")
            elif i == 1:
                assert new_prefix in line
