# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from contextlib import nullcontext
from errno import ENOENT
from os.path import isdir, join, lexists
from typing import TYPE_CHECKING

import pytest

from conda.common.compat import on_win
from conda.gateways.disk import delete
from conda.gateways.disk.create import create_link, mkdir_p
from conda.gateways.disk.delete import backoff_rmdir, rm_rf
from conda.gateways.disk.link import symlink
from conda.gateways.disk.test import softlink_supported
from conda.gateways.disk.update import touch
from conda.models.enums import LinkType

from .test_permissions import _make_read_only, _try_open, tempdir

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any


def _write_file(path, content):
    with open(path, "a") as fh:
        fh.write(content)
        fh.close()


def test_remove_file(tmp_path: Path):
    test_path = tmp_path / "test_path"
    touch(test_path)
    assert test_path.is_file()
    _try_open(test_path)
    _make_read_only(test_path)
    with pytest.raises((IOError, OSError)):
        _try_open(test_path)
    assert rm_rf(test_path)
    assert not test_path.exists()


def test_remove_file_to_trash(tmp_path: Path):
    test_path = tmp_path / "test_path"
    touch(test_path)
    assert test_path.is_file()
    _try_open(test_path)
    _make_read_only(test_path)
    with pytest.raises((IOError, OSError)):
        _try_open(test_path)
    assert rm_rf(test_path)
    assert not test_path.exists()


def test_remove_dir(tmp_path: Path):
    test_path = tmp_path / "test_path"
    touch(test_path)
    _try_open(test_path)
    assert test_path.is_file()
    assert tmp_path.is_dir()
    assert not test_path.is_symlink()
    assert rm_rf(tmp_path)
    assert rm_rf(test_path)
    assert not tmp_path.is_dir()
    assert not test_path.is_file()
    assert not lexists(test_path)


def test_remove_link_to_file(tmp_path: Path):
    dst_link = tmp_path / "test_link"
    src_file = tmp_path / "test_file"
    _write_file(src_file, "welcome to the ministry of silly walks")
    if not softlink_supported(src_file, tmp_path) and on_win:
        pytest.skip("softlink not supported")

    symlink(src_file, dst_link)
    assert src_file.is_file()
    assert not src_file.is_symlink()
    assert dst_link.is_symlink()
    assert rm_rf(dst_link)
    assert src_file.is_file()
    assert rm_rf(src_file)
    assert not src_file.is_file()
    assert not dst_link.is_symlink()
    assert not lexists(dst_link)


@pytest.mark.xfail(on_win, reason="Windows permission errors make a mess here")
def test_remove_link_to_dir(tmp_path: Path):
    dst_link = tmp_path / "test_link"
    src_dir = tmp_path / "test_dir"
    test_file = tmp_path / "test_file"
    mkdir_p(src_dir)
    touch(test_file)
    assert src_dir.is_dir()
    assert not src_dir.is_symlink()
    assert not dst_link.is_symlink()
    if not softlink_supported(test_file, tmp_path) and on_win:
        pytest.skip("softlink not supported")

    symlink(src_dir, dst_link)
    assert dst_link.is_symlink()
    assert rm_rf(dst_link)
    assert not dst_link.is_dir()
    assert not dst_link.is_symlink()
    assert not lexists(dst_link)
    assert src_dir.is_dir()
    assert rm_rf(src_dir)
    assert not src_dir.is_dir()
    assert not src_dir.is_symlink()


def test_rm_rf_does_not_follow_symlinks(tmp_path: Path):
    # make a file in some temp folder
    real_file = tmp_path / "testfile"
    real_file.write_text("weee")
    # make a subfolder
    subdir = tmp_path / "subfolder"
    subdir.mkdir()
    # link to the file in the subfolder
    link_path = subdir / "file_link"
    if not softlink_supported(real_file, tmp_path) and on_win:
        pytest.skip("softlink not supported")

    create_link(real_file, link_path, link_type=LinkType.softlink)
    assert link_path.is_symlink()
    # rm_rf the subfolder
    rm_rf(subdir)
    # assert that the file still exists in the root folder
    assert real_file.is_file()


def test_rm_rf(tmp_path: Path):
    test_path = tmp_path / "test_path"
    touch(test_path)
    _try_open(test_path)
    assert tmp_path.is_dir()
    assert test_path.is_file()
    rm_rf(test_path, True)
    assert not test_path.is_file()
    assert not tmp_path.is_dir()


def test_rm_rf_couldnt(tmp_path: Path):
    test_path = tmp_path / "test_path"
    touch(test_path)
    _try_open(test_path)
    assert tmp_path.is_dir()
    assert test_path.is_file()
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
