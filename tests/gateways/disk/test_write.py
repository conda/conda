# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

from conda.common.compat import on_win

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


@pytest.mark.parametrize("data", [b"", b"\x00\xff\r\n\n", "Grüße".encode()])
def test_write_file_preserves_bytes(tmp_path: Path, data: bytes) -> None:
    from conda.gateways.disk.write import read_file_snapshot, write_file

    path = tmp_path / "data"
    missing = read_file_snapshot(path)
    assert missing.data is None

    written = write_file(path, data, expected=missing)
    assert path.read_bytes() == data
    assert written.data == data
    write_file(path, b"next", expected=written)
    assert path.read_bytes() == b"next"


@pytest.mark.parametrize("initial", [None, b"original"])
def test_write_file_rejects_stale_snapshot(
    tmp_path: Path, initial: bytes | None
) -> None:
    from conda.gateways.disk.write import (
        FileChangedError,
        read_file_snapshot,
        write_file,
    )

    path = tmp_path / "data"
    if initial is not None:
        path.write_bytes(initial)
    snapshot = read_file_snapshot(path)
    path.write_bytes(b"another writer")

    with pytest.raises(FileChangedError, match="changed after reading"):
        write_file(path, b"mine", expected=snapshot)

    assert path.read_bytes() == b"another writer"


@pytest.mark.parametrize("operation", ["fsync", "replace"])
def test_write_file_failure_preserves_original(
    tmp_path: Path, mocker: MockerFixture, operation: str
) -> None:
    from conda.gateways.disk.write import write_file

    path = tmp_path / "data"
    path.write_bytes(b"original")
    mocker.patch(f"os.{operation}", side_effect=PermissionError("write failed"))

    with pytest.raises(PermissionError, match="write failed"):
        write_file(path, b"replacement")

    assert path.read_bytes() == b"original"
    assert set(tmp_path.iterdir()) == {path, tmp_path / "data.lock"}


@pytest.mark.parametrize("data", [b"", b"unchanged"])
@pytest.mark.parametrize(
    "in_place",
    [
        False,
        pytest.param(
            True,
            marks=pytest.mark.skipif(
                on_win or os.geteuid() == 0, reason="POSIX unprivileged permissions"
            ),
        ),
    ],
)
def test_write_file_refreshes_identical_contents(
    tmp_path: Path, data: bytes, in_place: bool
) -> None:
    from conda.gateways.disk.write import write_file

    path = tmp_path / "data"
    path.write_bytes(data)
    os.utime(path, (1, 1))
    if in_place:
        tmp_path.chmod(0o500)
    try:
        write_file(path, data, allow_in_place=in_place)

        assert path.read_bytes() == data
        assert path.stat().st_mtime_ns > 1_000_000_000
    finally:
        tmp_path.chmod(0o700)


@pytest.mark.skipif(
    on_win or os.geteuid() == 0, reason="POSIX unprivileged permissions"
)
@pytest.mark.parametrize("allow_in_place", [False, True])
def test_write_file_requires_opt_in_for_in_place_write(
    tmp_path: Path, allow_in_place: bool
) -> None:
    from conda.gateways.disk.write import write_file

    path = tmp_path / "data"
    path.write_bytes(b"original")
    inode = path.stat().st_ino
    tmp_path.chmod(0o500)
    try:
        if allow_in_place:
            write_file(path, b"new", allow_in_place=True)
            assert path.read_bytes() == b"new"
        else:
            with pytest.raises(PermissionError):
                write_file(path, b"new")
            assert path.read_bytes() == b"original"
        assert path.stat().st_ino == inode
    finally:
        tmp_path.chmod(0o700)


def test_write_file_rejects_text_before_touching_file(tmp_path: Path) -> None:
    from conda.gateways.disk.write import write_file

    path = tmp_path / "data"
    with pytest.raises(TypeError):
        write_file(path, "not bytes")

    assert not list(tmp_path.iterdir())


@pytest.mark.skipif(
    on_win or os.geteuid() == 0, reason="POSIX unprivileged permissions"
)
def test_write_file_reports_write_and_restore_errors(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    from conda.gateways.disk.write import FileRestoreError, write_file

    path = tmp_path / "data"
    path.write_bytes(b"original")
    write_error = OSError("write failed")
    restore_error = OSError("restore failed")
    mocker.patch("os.write", side_effect=[write_error, restore_error])
    tmp_path.chmod(0o500)
    try:
        with pytest.raises(FileRestoreError) as caught:
            write_file(path, b"replacement", allow_in_place=True)

        assert caught.value.write_error is write_error
        assert caught.value.restore_error is restore_error
        assert caught.value.__cause__ is write_error
    finally:
        tmp_path.chmod(0o700)


def test_snapshot_repr_omits_file_contents(tmp_path: Path) -> None:
    from conda.gateways.disk.write import read_file_snapshot

    path = tmp_path / "data"
    path.write_bytes(b"synthetic-secret")

    assert "synthetic-secret" not in repr(read_file_snapshot(path))
