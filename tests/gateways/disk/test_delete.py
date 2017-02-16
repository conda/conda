# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import pytest
from conda.base.context import context
from conda.common.compat import text_type
from conda.gateways.disk.delete import rm_rf
from conda.utils import on_win
from os.path import join, isdir, lexists, isfile
from conda.gateways.disk.link import islink


def can_not_symlink():
    return on_win and context.default_python[0] == '2'


def _write_file(path, content):
    with open(path, "w") as fh:
        fh.write(content)


def test_remove_file(tmpdir):
    test_file = "test.txt"
    path = join(text_type(tmpdir), test_file)
    _write_file(path, "welcome to the ministry of silly walks")
    assert rm_rf(path) is True


@pytest.mark.skipif(not on_win, reason="Testing case for windows is different then Unix")
def test_remove_file_to_trash(tmpdir):
    test_file = "test.txt"
    path = join(text_type(tmpdir), test_file)
    _write_file(path, "welcome to the ministry of silly walks")
    assert rm_rf(path) is True


def test_remove_dir(tmpdir):
    test_dir = "test"
    tmpdir.mkdir(test_dir)
    path = join(text_type(tmpdir), test_dir)
    assert isdir(path)
    assert not islink(path)
    assert rm_rf(path) is True
    assert not isdir(path)
    assert not lexists(path)


@pytest.mark.skipif(can_not_symlink(), reason="symlink function not available")
def test_remove_link_to_file(tmpdir):
    dst_link = join(text_type(tmpdir), "test_link")
    src_file = join(text_type(tmpdir), "test_file")
    _write_file(src_file, "welcome to the ministry of silly walks")
    os.symlink(src_file, dst_link)
    assert isfile(src_file)
    assert not islink(src_file)
    assert islink(dst_link)
    assert rm_rf(dst_link) is True
    assert isfile(src_file)  # make sure the directory is still there
    assert not isfile(dst_link)
    assert not lexists(dst_link)


@pytest.mark.skipif(can_not_symlink(), reason="symlink function not available")
def test_remove_link_to_dir(tmpdir):
    dst_link = join(text_type(tmpdir), "test_link")
    src_dir = join(text_type(tmpdir), "test_dir")
    tmpdir.mkdir("test_dir")
    os.symlink(src_dir, dst_link)
    assert isdir(src_dir)
    assert not islink(src_dir)
    assert islink(dst_link)
    assert rm_rf(dst_link) is True
    assert isdir(src_dir)  # make sure the directory is still there
    assert not isdir(dst_link)
    assert not lexists(dst_link)
