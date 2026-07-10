# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import errno
import os
from contextlib import nullcontext
from shutil import copyfile

import pytest

from conda.gateways.disk import create


@pytest.mark.parametrize(
    "function,raises",
    [
        ("create_application_entry_point", TypeError),
        ("ProgressFileWrapper", TypeError),
        ("create_fake_executable_softlink", TypeError),
        ("extract_tarball", TypeError),
    ],
)
def test_deprecations(function: str, raises: type[Exception] | None) -> None:
    raises_context = pytest.raises(raises) if raises else nullcontext()
    with pytest.deprecated_call(), raises_context:
        getattr(create, function)()


def test_copy_uses_clonefile_on_macos(monkeypatch: pytest.MonkeyPatch, tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.write_text("contents")
    clone_calls = []

    class CloneFile:
        argtypes = None
        restype = None

        def __call__(self, src, dst, flags):
            clone_calls.append((src, dst, flags))
            copyfile(src, dst)
            return 0

    class LibC:
        clonefile = CloneFile()

    monkeypatch.setattr(create, "on_mac", True)
    monkeypatch.setattr(create, "CDLL", lambda *args, **kwargs: LibC())
    monkeypatch.setattr(
        create,
        "_do_copy",
        lambda src, dst: pytest.fail("copy fallback should not be used"),
    )
    monkeypatch.setattr(create, "_CLONEFILE_UNSUPPORTED_DEVICES", set())
    monkeypatch.setattr(create, "_CLONEFILE_SUPPORTED_DEVICES", set())
    monkeypatch.setattr(create, "_CLONEFILE", None)

    create.copy(str(source), str(target))

    assert target.read_text() == "contents"
    assert clone_calls == [(bytes(source), bytes(target), 0)]


def test_copy_caches_unsupported_clonefile_device_pair(
    monkeypatch: pytest.MonkeyPatch, tmp_path
):
    source = tmp_path / "source"
    target_one = tmp_path / "target-one"
    target_two = tmp_path / "target-two"
    source.write_text("contents")
    clone_calls = []
    copy_calls = []

    class CloneFile:
        argtypes = None
        restype = None

        def __call__(self, src, dst, flags):
            clone_calls.append((src, dst, flags))
            return -1

    class LibC:
        clonefile = CloneFile()

    def copy_fallback(src, dst):
        copy_calls.append((src, dst))
        copyfile(src, dst)

    monkeypatch.setattr(create, "on_mac", True)
    monkeypatch.setattr(create, "CDLL", lambda *args, **kwargs: LibC())
    monkeypatch.setattr(create, "get_errno", lambda: errno.ENOTSUP)
    monkeypatch.setattr(create, "_do_copy", copy_fallback)
    monkeypatch.setattr(create, "_CLONEFILE_UNSUPPORTED_DEVICES", set())
    monkeypatch.setattr(create, "_CLONEFILE_SUPPORTED_DEVICES", set())
    monkeypatch.setattr(create, "_CLONEFILE", None)

    create.copy(str(source), str(target_one))
    create.copy(str(source), str(target_two))

    assert target_one.read_text() == "contents"
    assert target_two.read_text() == "contents"
    assert len(clone_calls) == 1
    assert copy_calls == [
        (str(source), str(target_one)),
        (str(source), str(target_two)),
    ]


def test_clone_file_supported_reuses_device_probe(
    monkeypatch: pytest.MonkeyPatch, tmp_path
):
    source = tmp_path / "source"
    source.write_text("contents")
    clone_calls = []

    class CloneFile:
        argtypes = None
        restype = None

        def __call__(self, src, dst, flags):
            clone_calls.append((src, dst, flags))
            copyfile(src, dst)
            return 0

    class LibC:
        clonefile = CloneFile()

    monkeypatch.setattr(create, "on_mac", True)
    monkeypatch.setattr(create, "CDLL", lambda *args, **kwargs: LibC())
    monkeypatch.setattr(create, "_CLONEFILE_UNSUPPORTED_DEVICES", set())
    monkeypatch.setattr(create, "_CLONEFILE_SUPPORTED_DEVICES", set())
    monkeypatch.setattr(create, "_CLONEFILE", None)

    assert create.clone_file_supported(str(source), str(tmp_path))
    assert create.clone_file_supported(str(source), str(tmp_path))
    assert len(clone_calls) == 1


@pytest.mark.skipif(not create.on_mac, reason="clonefile is only available on macOS")
def test_clone_directory_macos(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    (source / "nested").mkdir(parents=True)
    source_file = source / "nested/file"
    source_file.write_text("source")

    if not create.clone_directory(str(source), str(target)):
        pytest.skip("filesystem does not support recursive clonefile")

    target_file = target / "nested/file"
    assert target_file.read_text() == "source"
    assert source_file.stat().st_ino != target_file.stat().st_ino

    target_file.write_text("target")
    assert source_file.read_text() == "source"


def test_copy_over_existing_target_skips_clonefile(
    monkeypatch: pytest.MonkeyPatch, tmp_path
):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.write_text("new")
    target.write_text("old")

    monkeypatch.setattr(create, "on_mac", True)
    monkeypatch.setattr(
        create,
        "CDLL",
        lambda *args, **kwargs: pytest.fail("clonefile should not be loaded"),
    )

    create.copy(str(source), str(target))

    assert target.read_text() == "new"


@pytest.mark.parametrize(
    "ioctl_errno,source_size,target_names,expected_ioctl_calls,expected_copy_calls",
    (
        (None, 64 * 1024, ("target",), 1, 0),
        (None, 1024, ("target",), 0, 1),
        (errno.ENOTTY, 64 * 1024, ("target-one", "target-two"), 1, 2),
    ),
    ids=(
        "linux-ficlone",
        "linux-ficlone-skips-tiny-file",
        "linux-ficlone-unsupported-cache",
    ),
)
def test_copy_linux_ficlone_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    ioctl_errno,
    source_size,
    target_names,
    expected_ioctl_calls,
    expected_copy_calls,
):
    source = tmp_path / "source"
    source.write_bytes(b"x" * source_size)
    ioctl_calls = []
    copy_calls = []

    def ioctl(dst_fd, request, src_fd):
        ioctl_calls.append((dst_fd, request, src_fd))
        if ioctl_errno is not None:
            raise OSError(ioctl_errno, "unsupported")
        os.lseek(src_fd, 0, os.SEEK_SET)
        os.write(dst_fd, os.read(src_fd, source_size))

    def copy_fallback(src, dst):
        copy_calls.append((src, dst))
        if expected_copy_calls == 0:
            pytest.fail("copy fallback should not be used")
        copyfile(src, dst)

    monkeypatch.setattr(create, "on_mac", False)
    monkeypatch.setattr(create, "on_linux", True)
    monkeypatch.setattr(create, "_FICLONE_IOCTL", ioctl)
    monkeypatch.setattr(create, "_do_copy", copy_fallback)
    create._FICLONE_UNSUPPORTED_DEVICES.clear()

    for target_name in target_names:
        create.copy(str(source), str(tmp_path / target_name))

    for target_name in target_names:
        assert (tmp_path / target_name).read_bytes() == source.read_bytes()
    assert len(ioctl_calls) == expected_ioctl_calls
    assert all(call[1] == create._FICLONE for call in ioctl_calls)
    assert len(copy_calls) == expected_copy_calls


def test_copy_link_type_does_not_fall_back_to_hardlink(
    monkeypatch: pytest.MonkeyPatch, tmp_path
):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.write_text("contents")
    link_calls = []

    def copy_fallback(src, dst):
        copyfile(src, dst)
        return create.LinkType.copy

    monkeypatch.setattr(create, "_clone_file", lambda *args: False)
    monkeypatch.setattr(create, "link", lambda *args: link_calls.append(args))
    monkeypatch.setattr(create, "_do_copy", copy_fallback)

    create.create_link(str(source), str(target), create.LinkType.copy)

    assert target.read_text() == "contents"
    assert target.stat().st_nlink == 1
    assert link_calls == []


@pytest.mark.parametrize(
    (
        "on_win",
        "copyfile_result",
        "initial_target",
        "expects_python_copy",
        "expects_removed_target",
    ),
    (
        (True, True, None, False, False),
        (False, True, None, True, False),
        (True, False, "partial", True, True),
    ),
    ids=("windows-copyfile", "non-windows-copy", "windows-copyfile-fallback"),
)
def test_do_copy_windows_copyfile_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    on_win,
    copyfile_result,
    initial_target,
    expects_python_copy,
    expects_removed_target,
):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.write_text("contents")
    if initial_target is not None:
        target.write_text(initial_target)
    copy_calls = []
    python_copy_calls = []
    removed = []
    rm_rf = create.rm_rf
    original_copyfileobj = create.copyfileobj

    def copy_file(src, dst, fail_if_exists):
        copy_calls.append((src, dst, fail_if_exists))
        if copyfile_result:
            copyfile(src, dst)
        return copyfile_result

    def copyfileobj_spy(*args, **kwargs):
        python_copy_calls.append(args[2] if len(args) > 2 else kwargs.get("length"))
        return original_copyfileobj(*args, **kwargs)

    def remove(path):
        removed.append(path)
        rm_rf(path)

    win_copyfile = (
        copy_file
        if on_win
        else lambda *args: pytest.fail("CopyFileW should be Windows-only")
    )

    monkeypatch.setattr(create, "on_win", on_win)
    monkeypatch.setattr(create, "_WIN_COPYFILE", win_copyfile)
    monkeypatch.setattr(create, "copyfileobj", copyfileobj_spy)
    monkeypatch.setattr(create, "rm_rf", remove)

    create._do_copy(source, target)

    assert target.read_text() == "contents"
    assert copy_calls == ([(str(source), str(target), True)] if on_win else [])
    assert bool(python_copy_calls) is expects_python_copy
    assert removed == ([str(target)] if expects_removed_target else [])
