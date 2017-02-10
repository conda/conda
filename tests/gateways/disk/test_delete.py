# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import pytest
from conda.base.context import context
from conda.common.compat import text_type
from conda.gateways.disk.delete import rm_rf
from conda.utils import on_win
from os.path import join, isdir, islink, lexists, isfile


def can_not_symlink():
    return on_win and context.default_python[0] == '2'


def _make_file(path):
    with open("test_file", "r") as fh:
        fh.close()
    return fh


def _write_file(path, content):
    with open("test_file", "w") as fh:
        fh.write(content)
        fh.close()
    return fh


def test_remove_file(tmpdir):
    test_file = _make_file(tmpdir)
    path = join(text_type(test_file), tmpdir)
    try:
        _write_file(test_file, "welcome to the ministry of silly walks")
        assert rm_rf(path) is True
        assert isfile(path) is False
    finally:
        if os.path.exists(path):
            os.remove(path)

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
    try:
        assert not islink(src_file)
        assert islink(dst_link)
        assert rm_rf(dst_link) is True
        assert os.path.exists(src_file) is False
        assert not isfile(dst_link)
        assert not lexists(dst_link)
    finally:
        if os.path.exists(dst_link):
            os.remove(src_file)

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
