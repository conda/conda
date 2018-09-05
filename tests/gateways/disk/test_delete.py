
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from errno import ENOENT
import os
from os.path import isdir, isfile, islink, join, lexists, dirname

import pytest

from conda.base.context import reset_context
from conda.common.io import env_var
from conda.compat import TemporaryDirectory, on_win
from conda.exports import move_to_trash
from conda.gateways.disk.create import create_link, mkdir_p
from conda.gateways.disk.delete import rm_rf_wait, _move_path_to_trash, delete_trash
from conda.gateways.disk.link import islink, symlink
from conda.gateways.disk.test import softlink_supported
from conda.gateways.disk.update import touch
from conda.models.enums import LinkType
from .test_permissions import _make_read_only, _try_open, tempdir


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
        rm_rf_wait(test_path)
        assert not isfile(test_path)


def test_remove_file_to_trash():
    with tempdir() as td:
        test_path = join(td, 'test_path')
        touch(test_path)
        assert isfile(test_path)
        _try_open(test_path)
        _make_read_only(test_path)
        pytest.raises((IOError, OSError), _try_open, test_path)
        rm_rf_wait(test_path)
        assert not isfile(test_path)


def test_remove_dir():
    with tempdir() as td:
        test_path = join(td, 'test_path')
        touch(test_path)
        _try_open(test_path)
        assert isfile(test_path)
        assert isdir(td)
        assert not islink(test_path)
        rm_rf_wait(td)
        rm_rf_wait(test_path)
        assert not isdir(td)
        assert not isfile(test_path)
        assert not lexists(test_path)


def test_remove_link_to_file():
    with tempdir() as td:
        dst_link = join(td, "test_link")
        src_file = join(td, "test_file")
        _write_file(src_file, "welcome to the ministry of silly walks")
        if not softlink_supported(src_file, td) and on_win:
            pytest.skip("softlink not supported")

        symlink(src_file, dst_link)
        assert isfile(src_file)
        assert not islink(src_file)
        assert islink(dst_link)
        rm_rf_wait(dst_link)
        assert isfile(src_file)
        rm_rf_wait(src_file)
        assert not isfile(src_file)
        assert not islink(dst_link)
        assert not lexists(dst_link)


def test_remove_link_to_dir():
    with tempdir() as td:
        dst_link = join(td, "test_link")
        src_dir = join(td, "test_dir")
        test_file = join(td, "test_file")
        mkdir_p(src_dir)
        touch(test_file)
        assert isdir(src_dir)
        assert not islink(src_dir)
        assert not islink(dst_link)
        if not softlink_supported(test_file, td) and on_win:
            pytest.skip("softlink not supported")

        symlink(src_dir, dst_link)
        assert islink(dst_link)
        rm_rf_wait(dst_link)
        assert not isdir(dst_link)
        assert not islink(dst_link)
        assert not lexists(dst_link)
        assert isdir(src_dir)
        rm_rf_wait(src_dir)
        assert not isdir(src_dir)
        assert not islink(src_dir)


def test_rm_rf_does_not_follow_symlinks():
    with TemporaryDirectory() as tmp:
        # make a file in some temp folder
        real_file = os.path.join(tmp, 'testfile')
        with open(real_file, 'w') as f:
            f.write('weee')
        # make a subfolder
        subdir = os.path.join(tmp, 'subfolder')
        os.makedirs(subdir)
        # link to the file in the subfolder
        link_path = join(subdir, 'file_link')
        if not softlink_supported(real_file, tmp) and on_win:
            pytest.skip("softlink not supported")

        create_link(real_file, link_path, link_type=LinkType.softlink)
        assert islink(link_path)
        # rm_rf the subfolder
        rm_rf_wait(subdir)
        # assert that the file still exists in the root folder
        assert os.path.isfile(real_file)


def test_move_to_trash():
    with tempdir() as td:
        test_path = join(td, 'test_path')
        touch(test_path)
        _try_open(test_path)
        assert isdir(td)
        assert isfile(test_path)
        delete_me = move_to_trash(td, test_path)
        assert not isfile(test_path)
        rm_rf_wait(delete_me)
        assert not isfile(delete_me)


def test_move_path_to_trash_file():
    with tempdir() as td:
        with env_var('CONDA_PREFIX', td, reset_context):
            test_file = join(td, 'test_file')
            touch(test_file)
            assert isfile(test_file)
            trash_file = _move_path_to_trash(test_file)
            assert not isfile(test_file)
            assert isfile(trash_file)
            delete_trash()
            assert not isfile(trash_file)
            assert not isdir(dirname(trash_file))


def test_move_path_to_trash_dir():
    with tempdir() as td:
        with env_var('CONDA_PREFIX', td, reset_context):
            test_file = join(td, 'test_dir', 'test_file')
            test_dir = dirname(test_file)
            touch(test_file, mkdir=True)
            assert isdir(test_dir)
            assert isfile(test_file)
            trash_dir = _move_path_to_trash(test_dir)
            assert not isdir(test_dir)
            assert isdir(trash_dir)
            assert isfile(join(trash_dir, 'test_file'))
            delete_trash()
            assert not isdir(trash_dir)
            assert not isdir(dirname(trash_dir))


def test_backoff_unlink():
    with tempdir() as td:
        test_path = join(td, 'test_path')
        touch(test_path)
        _try_open(test_path)
        assert isdir(td)
        rm_rf_wait(td)
        assert not isdir(td)


def test_backoff_unlink_doesnt_exist():
    with tempdir() as td:
        test_path = join(td, 'test_path')
        touch(test_path)
        rm_rf_wait(join(test_path, 'some', 'path', 'in', 'utopia'))


def test_try_rmdir_all_empty_doesnt_exist():
    from conda.gateways.disk.delete import try_rmdir_all_empty
    with tempdir() as td:
        assert isdir(td)
        try_rmdir_all_empty(td)
        assert not isdir(td)
