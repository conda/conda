# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import uuid
import pytest
from shutil import rmtree
from os.path import join, isdir, islink, lexists, isfile
from tempfile import mkdtemp, gettempdir
from conda.base.context import context
from conda.common.compat import text_type
from conda.gateways.disk.delete import rm_rf
from conda.gateways.disk.update import touch
from test_permissions import tempdir, _try_open, _make_read_only
from conda.utils import on_win


def can_not_symlink():
    return on_win and context.default_python[0] == '2'


def _write_file(path, content):
    with open(path, "a") as fh:
        fh.write(content)
        fh.close()


def test_remove_file():
    with tempdir() as td:
        test_path = join(td, 'test_path')
        touch(test_path)
        assert isfile(test_path)
        _try_open(test_path)
        _make_read_only(test_path)
        pytest.raises((IOError, OSError), _try_open, test_path)
        assert rm_rf(test_path)
        assert not isfile(test_path)


def test_remove_file_to_trash():
    with tempdir() as td:
        test_path = join(td, 'test_path')
        touch(test_path)
        assert isfile(test_path)
        _try_open(test_path)
        _make_read_only(test_path)
        pytest.raises((IOError, OSError), _try_open, test_path)
        assert rm_rf(test_path)
        assert not isfile(test_path)


def test_remove_dir():
    with tempdir() as td:
        test_path = join(td, 'test_path')
        touch('test_path')
        _try_open(test_path)
        assert isfile(test_path)
        assert isdir(td)
        assert not islink(test_path)
        assert rm_rf(td)
        assert not isdir(td)
        assert not isfile(test_path)
        assert not lexists(test_path)


@pytest.mark.skipif(can_not_symlink(), reason="symlink function not available")
def test_remove_link_to_file():
    with tempdir() as td:
        dst_link = join(td, "test_link")
        src_file = join(td, "test_file")
        _write_file(src_file, "welcome to the ministry of silly walks")
        os.symlink(src_file, dst_link)
        assert isfile(src_file)
        assert not islink(src_file)
        assert islink(dst_link)
        assert rm_rf(dst_link)
        assert isfile(src_file)
        assert rm_rf(src_file)
        assert not isfile(src_file)
        assert not islink(dst_link)
        assert not lexists(dst_link)


@pytest.mark.skipif(can_not_symlink(), reason="symlink function not available")
def test_remove_link_to_dir():
    with tempdir() as td:
        dst_link = join(td, "test_link")
        src_dir = join(td, "test_dir")
        _write_file(src_dir, "welcome to the ministry of silly walks")
        os.symlink(src_dir, dst_link)
        assert not islink(src_dir)
        assert islink(dst_link)
        assert rm_rf(dst_link)
        assert not isdir(dst_link)
        assert not islink(dst_link)
        assert rm_rf(src_dir)
        assert not isdir(src_dir)
        assert not islink(src_dir)
        assert not lexists(dst_link)