# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
from errno import ENOENT, ENOSPC
from os.path import isdir, isfile, join, lexists
from pathlib import Path
from subprocess import CalledProcessError
from typing import TYPE_CHECKING

import pytest

from conda.common.compat import on_win
from conda.gateways.disk.create import TemporaryDirectory, create_link, mkdir_p
from conda.gateways.disk.delete import (
    backoff_rmdir,
    rm_rf,
    rmtree,
    unlink_or_rename_to_trash,
)
from conda.gateways.disk.link import islink, symlink
from conda.gateways.disk.permissions import make_read_only
from conda.gateways.disk.test import softlink_supported
from conda.gateways.disk.update import touch
from conda.models.enums import LinkType

from .test_permissions import _try_open, tempdir

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


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
        make_read_only(test_path)
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


def test_unlink_to_rename_to_trash_win_fallback(
    mocker: MockerFixture,
):
    """
    Test fix for bug: https://github.com/conda/conda/issues/15760
    """
    test_path = "idontexist"
    mocker.patch(
        "conda.gateways.disk.delete.os.unlink",
        side_effect=OSError(),
    )
    mocker.patch(
        "conda.gateways.disk.delete.os.rename",
        side_effect=OSError(),
    )
    mocker.patch("conda.gateways.disk.delete.on_win", True)
    mocker.patch("conda.gateways.disk.delete.exists", return_value=True)

    # Return True on the first isfile check so the while-loop body executes,
    # then False to exit the loop.
    mocker.patch(
        "conda.gateways.disk.delete.isfile",
        side_effect=[True, False],
    )
    mock_check_output = mocker.patch(
        "conda.gateways.disk.delete.check_output",
        return_value=b"",
    )

    unlink_or_rename_to_trash(test_path)

    # The counter suffix must have been applied; dest filename should end with .conda_trash_1
    call_args = mock_check_output.call_args[0][0]
    assert call_args[-1].endswith(".conda_trash_1")


def test_rmtree_skips_shutil_when_windows_rd_already_removed(
    mocker: MockerFixture,
):
    """Windows RD /S /Q removes the path; do not call shutil.rmtree on a missing dir (#16539)."""
    mocker.patch("conda.gateways.disk.delete.on_win", True)
    mocker.patch("conda.gateways.disk.delete.normpath", side_effect=lambda p: p)
    mocker.patch(
        "conda.gateways.disk.delete.check_output",
        return_value=b"",
    )
    mocker.patch("conda.gateways.disk.delete.isdir", return_value=False)
    mock_shutil_rmtree = mocker.patch("conda.gateways.disk.delete.shutil.rmtree")

    rmtree(r"C:\temp\already-gone")

    mock_shutil_rmtree.assert_not_called()


def test_rmtree_falls_back_to_shutil_when_windows_path_remains(
    mocker: MockerFixture,
):
    """If the Windows fast path leaves the directory, shutil.rmtree still runs."""
    mocker.patch("conda.gateways.disk.delete.on_win", True)
    mocker.patch("conda.gateways.disk.delete.normpath", side_effect=lambda p: p)
    mocker.patch(
        "conda.gateways.disk.delete.check_output",
        return_value=b"",
    )
    mocker.patch("conda.gateways.disk.delete.isdir", return_value=True)
    mock_shutil_rmtree = mocker.patch("conda.gateways.disk.delete.shutil.rmtree")

    rmtree(r"C:\temp\still-there")

    mock_shutil_rmtree.assert_called_once_with(r"C:\temp\still-there")


@pytest.mark.skipif(on_win, reason="rsync is only used on Unix")
@pytest.mark.parametrize("rsync", ["rsync", None])
def test_rmtree_preserves_existing_empty_directory(
    tmp_path, monkeypatch, mocker, rsync
):
    monkeypatch.chdir(tmp_path)
    existing = tmp_path / ".empty"
    existing.mkdir()
    keep = existing / "keep.txt"
    keep.write_text("keep me")
    target = tmp_path / "target"
    target.mkdir()
    (target / "file.txt").touch()
    mocker.patch("conda.gateways.disk.delete.which", return_value=rsync)
    mocker.patch("conda.gateways.disk.delete.check_output", return_value=b"")

    rmtree(target)

    assert not target.exists()
    assert keep.read_text() == "keep me"


@pytest.mark.skipif(on_win, reason="rsync is only used on Unix")
def test_rmtree_overlapping_deletions(tmp_path, monkeypatch, mocker):
    monkeypatch.chdir(tmp_path)
    targets = [tmp_path / "first", tmp_path / "second"]
    for target in targets:
        (target / "subdir").mkdir(parents=True)
        (target / "subdir" / "file.txt").touch()
    sources = []

    def overlap_deletions(command, **kwargs):
        source = Path(command[-2])
        sources.append(source)
        if len(sources) == 1:
            rmtree(targets[1])
        assert source.is_dir()
        return b""

    mocker.patch("conda.gateways.disk.delete.which", return_value="rsync")
    mocker.patch(
        "conda.gateways.disk.delete.check_output", side_effect=overlap_deletions
    )

    rmtree(targets[0])

    assert len(sources) == 2
    assert sources[0] != sources[1]
    assert all(not target.exists() for target in targets)
    assert all(not source.exists() for source in sources)


@pytest.mark.skipif(on_win, reason="rsync is only used on Unix")
def test_rmtree_falls_back_after_rsync_failure(tmp_path, monkeypatch, mocker):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "target"
    (target / "subdir").mkdir(parents=True)
    (target / "subdir" / "file.txt").touch()
    mocker.patch("conda.gateways.disk.delete.which", return_value="rsync")
    rsync = mocker.patch(
        "conda.gateways.disk.delete.check_output",
        side_effect=CalledProcessError(23, "rsync", output=b"rsync failed"),
    )

    rmtree(target)

    assert not target.exists()
    assert not Path(rsync.call_args.args[0][-2]).exists()


@pytest.mark.skipif(on_win, reason="rsync is only used on Unix")
def test_rmtree_falls_back_when_temporary_directory_cannot_be_created(tmp_path, mocker):
    target = tmp_path / "target"
    (target / "subdir").mkdir(parents=True)
    (target / "subdir" / "file.txt").touch()
    mocker.patch("conda.gateways.disk.delete.which", return_value="rsync")
    mocker.patch(
        "conda.gateways.disk.delete.TemporaryDirectory",
        side_effect=OSError(ENOSPC, "No space left on device"),
    )

    rmtree(target)

    assert not target.exists()
