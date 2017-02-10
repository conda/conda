# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import pytest
from os.path import join
from stat import S_IREAD, S_IRGRP, S_IROTH
from conda.utils import on_win
from conda.common.compat import text_type
from conda.gateways.disk.permissions import make_writable, recursive_make_writable


def _make_file(path):
    with open("test_file", "r") as fh:
        fh.close()
    return fh

def _can_write_file(test, content):
    with open('test', "w") as fh:
        fh.write(content)
        fh.close()
    if os.stat('test').st_size == 0.0:
        return False
    else:
        return True


def test_make_writable(tmpdir):
    test_file = _make_file(tmpdir)
    os.chmod(tmpdir, S_IREAD | S_IRGRP | S_IROTH)
    path = join(text_type(test_file), tmpdir)
    make_writable(path)
    assert _can_write_file(test_file, "welcome to the ministry of silly walks") is True


@pytest.mark.skipif(on_win, reason="Testing case for windows is different then Unix")
def test_recursive_make_writable(tmpdir):
    test_file = _make_file(tmpdir)
    os.chmod(tmpdir, S_IREAD | S_IRGRP | S_IROTH)
    path = join(text_type(tmpdir), tmpdir)
    recursive_make_writable(path, 10)
    assert _can_write_file(test_file, "welcome to the ministry of silly walks") is True

