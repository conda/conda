# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
from contextlib import nullcontext
from errno import ENOENT
from os.path import isdir, isfile, join, lexists
from typing import TYPE_CHECKING

import pytest

from conda.common.compat import on_win
from conda.gateways.disk import delete
from conda.gateways.disk.create import TemporaryDirectory, create_link, mkdir_p
from conda.gateways.disk.delete import backoff_rmdir, rm_rf
from conda.gateways.disk.link import islink, symlink
from conda.gateways.disk.test import softlink_supported
from conda.gateways.disk.update import touch
from conda.models.enums import LinkType

from .test_permissions import _make_read_only, _try_open, tempdir

if TYPE_CHECKING:
    from typing import Any


def _write_file(path, content):
    with open(path, "a") as fh:
        fh.write(content)
        fh.close()


def test_remove_file():
    with tempdir() as td:
        test_path = join(td, "test_path")
        touch(test_path)
        assert isfile(test_path)
        _try_open(test_path)
        _make_read_only(test_path)
        pytest.raises((IOError, OSError), _try_open, test_path)
        assert rm_rf(test_path)
        assert not isfile(test_path)


def test_remove_file_to_trash():
    with tempdir() as td:
        test_path = join(td, "test_path")
        touch(test_path)
        assert isfile(test_path)
        _try_open(test_path)
        _make_read_only(test_path)
        pytest.raises((IOError, OSError), _try_open, test_path)
        assert rm_rf(test_path)
        assert not isfile(test_path)


def test_remove_dir():
    with tempdir() as td:
        test_path = join(td, "test_path")
        touch(test_path)
        _try_open(test_path)
        assert isfile(test_path)
        assert isdir(td)
        assert not islink(test_path)
        assert rm_rf(td)
        assert rm_rf(test_path)
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
        assert rm_rf(dst_link)
        assert isfile(src_file)
        assert rm_rf(src_file)
        assert not isfile(src_file)
        assert not islink(dst_link)
        assert not lexists(dst_link)


@pytest.mark.xfail(on_win, reason="Windows permission errors make a mess here")
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
        assert rm_rf(dst_link)
        assert not isdir(dst_link)
        assert not islink(dst_link)
        assert not lexists(dst_link)
        assert isdir(src_dir)
        assert rm_rf(src_dir)
        assert not isdir(src_dir)
        assert not islink(src_dir)


def test_rm_rf_does_not_follow_symlinks():
    with TemporaryDirectory() as tmp:
        # make a file in some temp folder
        real_file = os.path.join(tmp, "testfile")
        with open(real_file, "w") as f:
            f.write("weee")
        # make a subfolder
        subdir = os.path.join(tmp, "subfolder")
        os.makedirs(subdir)
        # link to the file in the subfolder
        link_path = join(subdir, "file_link")
        if not softlink_supported(real_file, tmp) and on_win:
            pytest.skip("softlink not supported")

        create_link(real_file, link_path, link_type=LinkType.softlink)
        assert islink(link_path)
        # rm_rf the subfolder
        rm_rf(subdir)
        # assert that the file still exists in the root folder
        assert os.path.isfile(real_file)


def test_rm_rf():
    with tempdir() as td:
        test_path = join(td, "test_path")
        touch(test_path)
        _try_open(test_path)
        assert isdir(td)
        assert isfile(test_path)
        rm_rf(td, test_path)
        assert not isfile(test_path)


def test_rm_rf_couldnt():
    with tempdir() as td:
        test_path = join(td, "test_path")
        touch(test_path)
        _try_open(test_path)
        assert isdir(td)
        assert isfile(test_path)
        assert rm_rf(test_path)


def test_backoff_unlink():
    with tempdir() as td:
        test_path = join(td, "test_path")
        touch(test_path)
        _try_open(test_path)
        assert isdir(td)
        backoff_rmdir(td)
        assert not isdir(td)


def test_backoff_unlink_doesnt_exist():
    with tempdir() as td:
        test_path = join(td, "test_path")
        touch(test_path)
        try:
            backoff_rmdir(join(test_path, "some", "path", "in", "utopia"))
        except Exception as e:
            assert e.value.errno == ENOENT


def test_try_rmdir_all_empty_doesnt_exist():
    with tempdir() as td:
        assert isdir(td)
        rm_rf(td)
        assert not isdir(td)


@pytest.mark.parametrize(
    "function,raises,kwargs",
    [
        ("rm_rf", TypeError, {"max_retries": 5}),
        ("rm_rf", TypeError, {"trash": True}),
        ("try_rmdir_all_empty", TypeError, None),
        ("move_to_trash", TypeError, None),
        ("move_path_to_trash", TypeError, None),
    ],
)
def test_deprecations(
    function: str,
    raises: type[Exception] | None,
    kwargs: dict[str, Any] | None,
) -> None:
    raises_context = pytest.raises(raises) if raises else nullcontext()
    with pytest.deprecated_call(), raises_context:
        getattr(delete, function)(**(kwargs or {}))
